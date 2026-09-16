from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from .audio import extract_peaks
from .catalog import CatalogStore
from .metadata import fingerprint_file
from .models import BeatRecord


@dataclass(frozen=True, slots=True)
class MigrationResult:
    imported: int
    skipped: int


def migrate_legacy_catalog(store: CatalogStore, legacy_path: Path, preview_dir: Path, analyze_peaks: bool = True) -> MigrationResult:
    if store.get_setting("legacy_migration_v1") == "done" or not legacy_path.exists():
        return MigrationResult(0, 0)
    payload = json.loads(legacy_path.read_text(encoding="utf-8"))
    imported = 0
    skipped = 0
    for order, item in enumerate(payload if isinstance(payload, list) else []):
        slug = str(item.get("slug") or "").strip().lower()
        preview_name = Path(str(item.get("preview") or "")).name
        preview = preview_dir / preview_name
        if not slug or not preview.is_file():
            skipped += 1
            continue
        warnings: tuple[str, ...] = ()
        peaks: tuple[int, ...] = ()
        if analyze_peaks:
            try:
                peaks = extract_peaks(preview)
            except Exception:
                warnings = ("preview unreadable",)
        store.upsert(BeatRecord(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"christon.xyz/beats/{slug}")),
            title=str(item.get("title") or slug).lower(),
            slug=slug,
            status="published",
            public_order=order,
            bpm=str(item.get("bpm") or ""),
            key=str(item.get("key") or "").lower(),
            preview_peaks=peaks,
            preview_fingerprint=fingerprint_file(preview),
            published_preview_path=f"previews/{preview_name}",
            published_fingerprint=fingerprint_file(preview),
            warnings=warnings,
        ))
        imported += 1
    store.set_setting("legacy_migration_v1", "done")
    return MigrationResult(imported, skipped)
