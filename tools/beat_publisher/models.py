from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class BeatRecord:
    id: str
    title: str
    slug: str
    status: str
    public_order: int
    bpm: str = ""
    key: str = ""
    source_path: str = ""
    source_fingerprint: str = ""
    original_filename: str = ""
    source_duration: float = 0.0
    suggested_start: float = 0.0
    preview_start: float = 0.0
    preview_duration: float = 30.0
    normalize: bool = True
    source_peaks: tuple[int, ...] = ()
    preview_path: str = ""
    preview_peaks: tuple[int, ...] = ()
    preview_fingerprint: str = ""
    published_preview_path: str = ""
    published_fingerprint: str = ""
    published_revision: str = ""
    managed_source: bool = False
    warnings: tuple[str, ...] = ()
    previous_status: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        value = asdict(self)
        value["source_peaks"] = list(self.source_peaks)
        value["preview_peaks"] = list(self.preview_peaks)
        value["warnings"] = list(self.warnings)
        return value


@dataclass(frozen=True, slots=True)
class PublishRevision:
    revision: str
    state: str
    created_at: str
    commit_hash: str = ""
    detail: str = ""
