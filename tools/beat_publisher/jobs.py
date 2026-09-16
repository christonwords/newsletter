from __future__ import annotations

import os
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

from .audio import analyze_source
from .catalog import CatalogStore
from .metadata import fingerprint_file, parse_filename
from .models import BeatRecord


@dataclass(frozen=True, slots=True)
class ImportResult:
    beat_id: str
    state: str
    warnings: tuple[str, ...] = ()
    error: str = ""


class BatchImporter:
    def __init__(self, store: CatalogStore, managed_source_dir: Path, workers: int | None = None):
        self.store = store
        self.managed_source_dir = Path(managed_source_dir)
        self.workers = workers or min(4, max(1, (os.cpu_count() or 2) // 2))
        self.managed_source_dir.mkdir(parents=True, exist_ok=True)

    def _unique_slug(self, wanted: str, existing: set[str]) -> str:
        if wanted not in existing:
            return wanted
        suffix = 2
        while f"{wanted}-{suffix}" in existing:
            suffix += 1
        return f"{wanted}-{suffix}"

    def _analyze(self, path: Path):
        if path.suffix.lower() != ".wav":
            raise ValueError("only wav files are supported")
        fingerprint = fingerprint_file(path)
        duplicate = self.store.find_by_fingerprint(fingerprint)
        if duplicate:
            return ImportResult(duplicate.id, "duplicate", duplicate.warnings), None
        return None, (path, fingerprint, parse_filename(path.name), analyze_source(path))

    def import_paths(self, paths: list[Path]) -> list[ImportResult]:
        clean_paths = [Path(path).resolve() for path in paths]
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [executor.submit(self._analyze, path) for path in clean_paths]
            analyzed = []
            for path, future in zip(clean_paths, futures):
                try:
                    analyzed.append(future.result())
                except Exception as error:
                    analyzed.append((ImportResult("", "error", error=str(error)), None))

        existing_slugs = {record.slug for record in self.store.list()}
        next_order = len(self.store.list())
        results = []
        for prebuilt, detail in analyzed:
            if prebuilt:
                results.append(prebuilt)
                continue
            path, fingerprint, parsed, analysis = detail
            beat_id = uuid.uuid4().hex
            slug = self._unique_slug(parsed.slug, existing_slugs)
            existing_slugs.add(slug)
            destination = self.managed_source_dir / f"{beat_id}.wav"
            shutil.copy2(path, destination)
            warnings = parsed.warnings + (("slug adjusted",) if slug != parsed.slug else ())
            record = BeatRecord(
                id=beat_id,
                title=parsed.title,
                slug=slug,
                status="draft",
                public_order=next_order,
                bpm=parsed.bpm,
                key=parsed.key,
                source_path=str(destination),
                source_fingerprint=fingerprint,
                original_filename=path.name,
                source_duration=analysis.duration,
                suggested_start=analysis.suggested_start,
                preview_start=analysis.suggested_start,
                source_peaks=analysis.peaks,
                managed_source=True,
                warnings=warnings,
            )
            self.store.upsert(record)
            next_order += 1
            results.append(ImportResult(beat_id, "imported", warnings))
        return results

    def import_upload(self, filename: str, data: bytes) -> ImportResult:
        incoming = self.managed_source_dir / f"incoming-{uuid.uuid4().hex}.wav"
        incoming.write_bytes(data)
        try:
            result = self.import_paths([incoming])[0]
        finally:
            incoming.unlink(missing_ok=True)
        if result.beat_id and result.state == "imported":
            current = self.store.get(result.beat_id)
            if current:
                self.store.upsert(replace(current, original_filename=Path(filename).name))
        return result
