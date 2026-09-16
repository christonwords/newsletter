from __future__ import annotations

import math
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .metadata import fingerprint_file


PREVIEW_SECONDS = 30.0
ANALYSIS_RATE = 8000


@dataclass(frozen=True, slots=True)
class AudioAnalysis:
    duration: float
    sample_rate: int
    peaks: tuple[int, ...]
    suggested_start: float


@dataclass(frozen=True, slots=True)
class PreviewArtifact:
    path: Path
    duration: float
    size: int
    fingerprint: str
    peaks: tuple[int, ...]


def _run(command: list[str], binary: bool = False):
    return subprocess.run(command, check=True, capture_output=True, text=not binary)


def probe_duration(path: Path) -> float:
    result = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(result.stdout.strip())


def _decode_mono(path: Path, rate: int = ANALYSIS_RATE) -> tuple[int, ...]:
    result = _run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"], binary=True)
    return tuple(value[0] for value in struct.iter_unpack("<h", result.stdout))


def _peaks(samples: tuple[int, ...], peak_count: int) -> tuple[int, ...]:
    if not samples:
        return tuple([0] * peak_count)
    result = []
    for index in range(peak_count):
        start = index * len(samples) // peak_count
        end = max(start + 1, (index + 1) * len(samples) // peak_count)
        result.append(min(255, round(max(abs(value) for value in samples[start:end]) * 255 / 32767)))
    return tuple(result)


def extract_peaks(path: Path, peak_count: int = 240) -> tuple[int, ...]:
    return _peaks(_decode_mono(path), peak_count)


def analyze_source(path: Path, peak_count: int = 240) -> AudioAnalysis:
    duration = probe_duration(path)
    samples = _decode_mono(path)
    second_count = max(1, math.ceil(len(samples) / ANALYSIS_RATE))
    rms = []
    for index in range(second_count):
        window = samples[index * ANALYSIS_RATE : (index + 1) * ANALYSIS_RATE]
        rms.append(math.sqrt(sum(value * value for value in window) / max(1, len(window))))
    max_start = max(0, int(duration - PREVIEW_SECONDS))
    best_start = 0
    best_score = -1.0
    for start in range(max_start + 1):
        window = rms[start : start + int(PREVIEW_SECONDS)]
        score = sum(window) / max(1, len(window))
        if score > best_score:
            best_start, best_score = start, score
    return AudioAnalysis(duration, ANALYSIS_RATE, _peaks(samples, peak_count), float(best_start))


def export_preview(source: Path, output: Path, start: float, normalize: bool = True) -> PreviewArtifact:
    source_duration = probe_duration(source)
    if source_duration < PREVIEW_SECONDS - 0.05:
        raise ValueError("source must be at least 30 seconds")
    start = min(max(0.0, float(start)), max(0.0, source_duration - PREVIEW_SECONDS))
    output.parent.mkdir(parents=True, exist_ok=True)
    filters = ["afade=t=in:st=0:d=0.06", "afade=t=out:st=29.65:d=0.35"]
    if normalize:
        filters.insert(0, "loudnorm=I=-14:TP=-1.5:LRA=11")
    try:
        render_duration = PREVIEW_SECONDS
        for _ in range(2):
            _run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{render_duration:.3f}", "-vn", "-codec:a", "libmp3lame", "-b:a", "160k", "-af", ",".join(filters), str(output)])
            duration = probe_duration(output)
            if abs(duration - PREVIEW_SECONDS) <= 0.05:
                break
            render_duration = max(0.1, render_duration - (duration - PREVIEW_SECONDS))
        if abs(duration - PREVIEW_SECONDS) > 0.05:
            raise ValueError(f"preview duration is {duration:.3f}, expected 30 seconds")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return PreviewArtifact(output, duration, output.stat().st_size, fingerprint_file(output), extract_peaks(output))
