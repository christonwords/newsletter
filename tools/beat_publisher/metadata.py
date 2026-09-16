from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParsedMetadata:
    title: str
    bpm: str
    key: str
    slug: str
    warnings: tuple[str, ...]


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower().strip())
    return value.strip("-") or "untitled-beat"


def normalize_key(value: str) -> str:
    value = re.sub(r"\s+", " ", value.lower().strip())
    value = value.replace("major", "maj").replace("minor", "min")
    if re.fullmatch(r"[a-g](?:#|b)?m", value):
        value = f"{value[:-1]} min"
    return value


def parse_filename(filename: str) -> ParsedMetadata:
    stem = Path(filename).stem
    spaced = re.sub(r"[_-]+", " ", stem).strip()
    bpm_match = re.search(r"\b(\d{2,3})\s*bpm\b", spaced, re.IGNORECASE)
    if not bpm_match:
        bpm_match = re.search(r"(?:^|\s)(\d{2,3})(?:\s|$)", spaced)
    bpm = bpm_match.group(1) if bpm_match else ""

    key_match = re.search(
        r"\b([a-g](?:#|b)?\s*(?:major|minor|maj|min|m))\b",
        spaced,
        re.IGNORECASE,
    )
    key = normalize_key(key_match.group(1)) if key_match else ""

    title = spaced
    if bpm_match:
        title = f"{title[:bpm_match.start()]} {title[bpm_match.end():]}"
    if key_match:
        title = re.sub(re.escape(key_match.group(0)), " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" -_").lower() or spaced.lower()

    warnings = []
    if not bpm:
        warnings.append("bpm missing")
    if not key:
        warnings.append("key missing")
    return ParsedMetadata(title, bpm, key, slugify(title), tuple(warnings))


def fingerprint_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
