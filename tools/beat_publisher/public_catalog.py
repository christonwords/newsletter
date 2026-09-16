from __future__ import annotations

import re

from .models import BeatRecord


def hashed_preview_name(slug: str, fingerprint: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("unsafe slug")
    if not re.fullmatch(r"[a-f0-9]{8,}", fingerprint.lower()):
        raise ValueError("invalid preview fingerprint")
    return f"{slug}-{fingerprint[:8].lower()}.mp3"


def build_public_catalog(records: list[BeatRecord], revision: str, published_at: str) -> dict:
    visible = sorted((record for record in records if record.status in {"ready", "published"}), key=lambda record: record.public_order)
    ids = [record.id for record in visible]
    slugs = [record.slug for record in visible]
    if len(ids) != len(set(ids)) or len(slugs) != len(set(slugs)):
        raise ValueError("duplicate beat id or slug")
    beats = []
    for order, record in enumerate(visible):
        if len(record.preview_peaks) != 240 or any(not isinstance(value, int) or value < 0 or value > 255 for value in record.preview_peaks):
            raise ValueError(f"{record.slug} needs 240 normalized peaks")
        fingerprint = record.preview_fingerprint or record.published_fingerprint
        preview = f"previews/{hashed_preview_name(record.slug, fingerprint)}"
        beats.append({
            "id": record.id,
            "slug": record.slug,
            "title": record.title.lower(),
            "bpm": record.bpm,
            "key": record.key.lower(),
            "preview": preview,
            "duration": 30,
            "order": order,
            "peaks": list(record.preview_peaks),
        })
    return {"schemaVersion": 1, "revision": revision, "publishedAt": published_at, "beats": beats}
