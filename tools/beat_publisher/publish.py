from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .catalog import CatalogStore
from .models import BeatRecord
from .public_catalog import build_public_catalog, hashed_preview_name


@dataclass(frozen=True, slots=True)
class PublishReview:
    id: str
    ready: int
    visible: int
    removals: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"id": self.id, "ready": self.ready, "visible": self.visible, "removals": self.removals, "warnings": list(self.warnings)}


def prepare_review(store: CatalogStore) -> PublishReview:
    records = store.list()
    visible = [record for record in records if record.status in {"ready", "published"}]
    ready = [record for record in visible if record.status == "ready"]
    if not ready and not any(record.status in {"hidden", "removed"} for record in records):
        raise ValueError("nothing is ready to publish")
    problems = []
    for record in ready:
        if not record.preview_path or not Path(record.preview_path).is_file():
            problems.append(f"{record.title}: make and approve a preview")
        if len(record.preview_peaks) != 240:
            problems.append(f"{record.title}: waveform data is incomplete")
    if problems:
        raise ValueError("\n".join(problems))
    return PublishReview(uuid.uuid4().hex, len(ready), len(visible), sum(record.status in {"hidden", "removed"} for record in records), ())


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)


def publish(store: CatalogStore, repo_root: Path, review_id: str, push: bool = True) -> dict:
    review = prepare_review(store)
    if not review_id:
        raise ValueError("publish review is required")
    records = store.list()
    beats_dir = repo_root / "beats"
    previews_dir = beats_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    revision = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    published_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    catalog = build_public_catalog(records, revision, published_at)
    visible = {record.id: record for record in records if record.status in {"ready", "published"}}

    with tempfile.TemporaryDirectory(dir=repo_root / ".beat_publisher_data") as temp:
        staging = Path(temp)
        staged_previews = staging / "previews"
        staged_previews.mkdir()
        for item in catalog["beats"]:
            record = visible[item["id"]]
            source = Path(record.preview_path) if record.status == "ready" else beats_dir / record.published_preview_path
            if not source.is_file():
                raise ValueError(f"missing preview for {record.title}")
            shutil.copy2(source, staged_previews / Path(item["preview"]).name)
        (staging / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

        previous = set()
        current_catalog = beats_dir / "catalog.json"
        if current_catalog.exists():
            old = json.loads(current_catalog.read_text(encoding="utf-8"))
            previous = {Path(item.get("preview", "")).name for item in old.get("beats", [])}
        generated = {path.name for path in staged_previews.iterdir()}
        hidden = {
            Path(record.published_preview_path).name
            for record in records
            if record.status == "hidden" and record.published_preview_path
        }
        removals = [previews_dir / name for name in previous - generated - hidden if name]

        changed = []
        for source in staged_previews.iterdir():
            destination = previews_dir / source.name
            shutil.copy2(source, destination)
            changed.append(destination)
        shutil.copy2(staging / "catalog.json", current_catalog)
        changed.append(current_catalog)
        legacy = beats_dir / "beats.json"
        if legacy.exists():
            legacy.unlink()
            removals.append(legacy)
        for path in removals:
            path.unlink(missing_ok=True)

    relative_changed = [str(path.relative_to(repo_root)).replace("\\", "/") for path in changed]
    relative_removed = [str(path.relative_to(repo_root)).replace("\\", "/") for path in removals]
    if relative_changed:
        _run(["git", "add", "--", *relative_changed], repo_root)
    for path in relative_removed:
        _run(["git", "add", "--", path], repo_root)
    staged = _run(["git", "diff", "--cached", "--name-only"], repo_root).stdout.splitlines()
    allowed = set(relative_changed + relative_removed)
    if set(staged) - allowed:
        raise RuntimeError("unrelated files were already staged; publish cancelled")
    _run(["git", "commit", "-m", f"publish {len(catalog['beats'])} beat previews"], repo_root)
    commit_hash = _run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()
    push_error = ""
    if push:
        try:
            _run(["git", "push"], repo_root)
        except subprocess.CalledProcessError as error:
            push_error = (error.stderr or error.stdout or str(error)).strip()

    for item in catalog["beats"]:
        record = visible[item["id"]]
        store.update(
            record.id,
            status="published",
            published_preview_path=item["preview"],
            published_fingerprint=record.preview_fingerprint or record.published_fingerprint,
            published_revision=revision,
            previous_status="",
        )
    store.set_setting("publish_state", "push_required" if push_error else "pushed")
    store.set_setting("last_commit", commit_hash)
    return {"state": "push_required" if push_error else "pushed", "commit": commit_hash, "revision": revision, "error": push_error}


def retry_push(store: CatalogStore, repo_root: Path) -> dict:
    _run(["git", "push"], repo_root)
    store.set_setting("publish_state", "pushed")
    return {"state": "pushed", "commit": store.get_setting("last_commit")}
