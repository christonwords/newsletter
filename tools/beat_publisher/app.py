from __future__ import annotations

import json
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
BEATS_DIR = REPO_ROOT / "beats"
PREVIEWS_DIR = BEATS_DIR / "previews"
CATALOG_PATH = BEATS_DIR / "beats.json"
TMP_DIR = REPO_ROOT / ".beat_publisher_tmp"
PREVIEW_SECONDS = 30
MP3_BITRATE = "192k"

SESSIONS: dict[str, dict] = {}


HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>beat publisher</title>
    <style>
      :root { --red:#ff1c1c; --line:rgba(255,28,28,.34); --bg:#050000; --glass:rgba(20,0,0,.72); }
      * { box-sizing:border-box; }
      body { margin:0; min-height:100vh; color:var(--red); background:radial-gradient(circle at 50% 0, rgba(255,0,0,.22), transparent 34rem), var(--bg); font-family:Georgia,serif; text-transform:lowercase; }
      main { width:min(980px, calc(100% - 28px)); margin:0 auto; padding:38px 0 70px; }
      h1 { margin:0 0 10px; font-size:clamp(3rem, 10vw, 7rem); line-height:.8; }
      p { line-height:1.5; }
      .panel { border:1px solid var(--line); border-radius:28px; padding:18px; margin-top:16px; background:var(--glass); box-shadow:0 24px 70px rgba(0,0,0,.55), inset 0 0 24px rgba(255,28,28,.08); }
      label { display:block; margin:14px 0 6px; font-weight:bold; }
      input, button { width:100%; border:1px solid var(--line); border-radius:999px; padding:12px 14px; color:var(--red); background:rgba(0,0,0,.45); font:inherit; text-transform:lowercase; }
      input[type=file] { border-radius:18px; }
      button { cursor:pointer; font-weight:bold; }
      button.primary { background:rgba(255,28,28,.14); }
      button:disabled { opacity:.45; cursor:not-allowed; }
      .grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; }
      .actions { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-top:16px; }
      audio { width:100%; margin-top:14px; }
      .status { white-space:pre-wrap; border:1px solid var(--line); border-radius:18px; padding:12px; min-height:54px; background:rgba(0,0,0,.34); }
      @media (max-width:760px) { .grid, .actions { grid-template-columns:1fr; } }
    </style>
  </head>
  <body>
    <main>
      <h1>beat publisher</h1>
      <p>import a full wav, generate a 30 second mp3 preview, listen before export, then publish it to christon.xyz/beats.</p>

      <section class="panel">
        <label for="file">full wav beat</label>
        <input id="file" type="file" accept=".wav,audio/wav,audio/x-wav">
        <button id="upload" class="primary" type="button">import wav</button>
      </section>

      <section class="panel">
        <div class="grid">
          <div><label for="title">title</label><input id="title"></div>
          <div><label for="bpm">bpm</label><input id="bpm"></div>
          <div><label for="key">key</label><input id="key"></div>
        </div>
        <div class="grid">
          <div><label for="start">preview start seconds</label><input id="start" type="number" min="0" step="0.1"></div>
          <div><label for="duration">source duration</label><input id="duration" disabled></div>
          <div><label for="slug">slug</label><input id="slug"></div>
        </div>
        <div class="actions">
          <button id="suggest" type="button" disabled>use smart start</button>
          <button id="preview" type="button" disabled>make preview</button>
          <button id="export" class="primary" type="button" disabled>export to site</button>
        </div>
        <audio id="player" controls></audio>
      </section>

      <section class="panel">
        <label><input id="push" type="checkbox" style="width:auto; margin-right:8px;"> commit and push after export</label>
        <div id="status" class="status">ready.</div>
      </section>
    </main>

    <script>
      let sessionId = null;
      let smartStart = 0;
      const $ = (id) => document.querySelector(id);
      const status = (msg) => { $("#status").textContent = msg; };
      const setDisabled = (disabled) => {
        $("#suggest").disabled = disabled;
        $("#preview").disabled = disabled;
      };

      const postJson = async (url, payload) => {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "request failed");
        return data;
      };

      $("#upload").addEventListener("click", async () => {
        const file = $("#file").files[0];
        if (!file) { status("choose a wav first."); return; }
        status("importing and analyzing...");
        const form = new FormData();
        form.append("file", file);
        const response = await fetch("/upload", { method: "POST", body: form });
        const data = await response.json();
        if (!response.ok) { status(data.error || "upload failed."); return; }
        sessionId = data.id;
        smartStart = data.suggested_start;
        $("#title").value = data.title;
        $("#bpm").value = data.bpm || "";
        $("#key").value = data.key || "";
        $("#start").value = data.suggested_start;
        $("#duration").value = `${data.duration.toFixed(1)} sec`;
        $("#slug").value = data.slug;
        $("#export").disabled = true;
        setDisabled(false);
        status(`imported ${data.original_name}\\nsmart start: ${data.suggested_start}s`);
      });

      $("#suggest").addEventListener("click", () => {
        $("#start").value = smartStart;
        status(`smart start restored to ${smartStart}s.`);
      });

      $("#preview").addEventListener("click", async () => {
        if (!sessionId) return;
        status("making preview mp3...");
        const data = await postJson("/preview", {
          id: sessionId,
          title: $("#title").value,
          bpm: $("#bpm").value,
          key: $("#key").value,
          slug: $("#slug").value,
          start: $("#start").value
        });
        $("#player").src = `${data.preview_url}?t=${Date.now()}`;
        $("#export").disabled = false;
        status("preview ready. play it before export.");
      });

      $("#export").addEventListener("click", async () => {
        if (!sessionId) return;
        status("exporting to site...");
        try {
          const data = await postJson("/export", {
            id: sessionId,
            title: $("#title").value,
            bpm: $("#bpm").value,
            key: $("#key").value,
            slug: $("#slug").value,
            start: $("#start").value,
            push: $("#push").checked
          });
          status(data.message);
        } catch (error) {
          status(error.message);
        }
      });
    </script>
  </body>
</html>"""


def ensure_dirs() -> None:
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    if not CATALOG_PATH.exists():
        CATALOG_PATH.write_text("[]\n", encoding="utf-8")


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd or REPO_ROOT, text=True, capture_output=True, check=True)


def ffprobe_duration(path: Path) -> float:
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    return float(result.stdout.strip())


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or f"beat-{int(time.time())}"


def parse_filename(filename: str) -> dict:
    stem = Path(filename).stem
    spaced = re.sub(r"[_-]+", " ", stem).strip()
    bpm = ""
    key = ""

    bpm_match = re.search(r"\b(\d{2,3})\s*bpm\b", spaced, re.IGNORECASE)
    if not bpm_match:
      bpm_match = re.search(r"(?:^|\s)(\d{2,3})(?:\s|$)", spaced)
    if bpm_match:
        bpm = bpm_match.group(1)

    key_pattern = r"\b([a-g](?:#|b)?\s*(?:maj(?:or)?|min(?:or)?|m)?|[a-g](?:#|b)?)\b"
    candidates = list(re.finditer(key_pattern, spaced, re.IGNORECASE))
    for candidate in reversed(candidates):
        token = candidate.group(1).strip()
        if re.fullmatch(r"[a-g]", token, re.IGNORECASE) and len(candidates) > 1:
            continue
        key = normalize_key(token)
        break

    title = spaced
    if bpm:
        title = re.sub(rf"\b{re.escape(bpm)}\s*bpm\b", " ", title, flags=re.IGNORECASE)
        title = re.sub(rf"(?:^|\s){re.escape(bpm)}(?:\s|$)", " ", title)
    if key:
        title = remove_key_from_title(title, key)
    title = re.sub(r"\s+", " ", title).strip(" -_")

    return {
        "title": title or spaced,
        "bpm": bpm,
        "key": key,
        "slug": slugify(title or spaced),
    }


def normalize_key(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip().lower())
    value = value.replace("major", "maj").replace("minor", "min")
    if value.endswith(" m") and not value.endswith(" maj"):
        value = value[:-2] + " min"
    if re.fullmatch(r"[a-g](#|b)?m", value):
        value = value[:-1] + " min"
    return value


def remove_key_from_title(title: str, key: str) -> str:
    root = key.split()[0]
    forms = {key, root}
    if "min" in key:
        forms.add(root + "m")
        forms.add(root + " minor")
    if "maj" in key:
        forms.add(root + " major")
    for form in sorted(forms, key=len, reverse=True):
        title = re.sub(rf"\b{re.escape(form)}\b", " ", title, flags=re.IGNORECASE)
    return title


def suggest_start(path: Path, duration: float) -> float:
    if duration <= PREVIEW_SECONDS:
        return 0

    sample_rate = 8000
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    samples = struct.iter_unpack("<h", result.stdout)
    frame = sample_rate
    rms_values = []
    acc = 0
    count = 0
    for (sample,) in samples:
        acc += sample * sample
        count += 1
        if count == frame:
            rms_values.append(math.sqrt(acc / count))
            acc = 0
            count = 0

    if len(rms_values) <= PREVIEW_SECONDS:
        return round(max(0, duration - PREVIEW_SECONDS) / 2, 1)

    start_min = min(8, max(0, int(duration - PREVIEW_SECONDS)))
    start_max = max(start_min, len(rms_values) - PREVIEW_SECONDS - 4)
    best_start = start_min
    best_score = -1.0
    for start in range(start_min, start_max + 1):
        window = rms_values[start : start + PREVIEW_SECONDS]
        if not window:
            continue
        score = sum(window) / len(window)
        if score > best_score:
            best_score = score
            best_start = start
    return float(best_start)


def make_preview(source: Path, output: Path, start: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg",
        "-y",
        "-ss",
        f"{max(0, start):.3f}",
        "-i",
        str(source),
        "-t",
        str(PREVIEW_SECONDS),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        MP3_BITRATE,
        "-af",
        "afade=t=in:st=0:d=0.08,afade=t=out:st=29.25:d=0.75,loudnorm=I=-14:TP=-1.5:LRA=11",
        str(output),
    ])


def load_catalog() -> list[dict]:
    ensure_dirs()
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_catalog(beats: list[dict]) -> None:
    CATALOG_PATH.write_text(json.dumps(beats, indent=2) + "\n", encoding="utf-8")


def upsert_beat(entry: dict) -> None:
    beats = load_catalog()
    beats = [beat for beat in beats if beat.get("slug") != entry["slug"]]
    beats.append(entry)
    beats.sort(key=lambda beat: beat.get("title", ""))
    save_catalog(beats)


def commit_and_push(slug: str) -> str:
    run(["git", "add", "beats"])
    status = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, text=True, capture_output=True, check=True)
    if not status.stdout.strip():
        return "nothing changed."
    run(["git", "commit", "-m", f"add beat preview {slug}"])
    run(["git", "push"])
    return "committed and pushed."


def parse_multipart(body: bytes, content_type: str) -> tuple[str, bytes]:
    boundary_match = re.search(r"boundary=(.+)", content_type)
    if not boundary_match:
        raise ValueError("missing multipart boundary")
    boundary = boundary_match.group(1).strip('"').encode()
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"\r\n\r\n" not in part:
            continue
        headers, data = part.split(b"\r\n\r\n", 1)
        if b'name="file"' not in headers:
            continue
        filename_match = re.search(rb'filename="([^"]+)"', headers)
        filename = filename_match.group(1).decode("utf-8", errors="ignore") if filename_match else "beat.wav"
        return Path(filename).name, data.rstrip(b"\r\n-")
    raise ValueError("file not found")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            payload = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if parsed.path.startswith("/tmp/"):
            path = TMP_DIR / parsed.path.removeprefix("/tmp/")
            if path.exists() and path.is_file():
                payload = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            if self.path == "/upload":
                self.handle_upload()
            elif self.path == "/preview":
                self.handle_preview()
            elif self.path == "/export":
                self.handle_export()
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def handle_upload(self) -> None:
        ensure_dirs()
        length = int(self.headers.get("Content-Length", "0"))
        filename, data = parse_multipart(self.rfile.read(length), self.headers.get("Content-Type", ""))
        if not filename.lower().endswith(".wav"):
            raise ValueError("please import a wav file")

        session_id = uuid.uuid4().hex
        session_dir = TMP_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        source_path = session_dir / filename
        source_path.write_bytes(data)

        parsed = parse_filename(filename)
        duration = ffprobe_duration(source_path)
        start = suggest_start(source_path, duration)
        SESSIONS[session_id] = {
            "source": str(source_path),
            "preview": str(session_dir / "preview.mp3"),
            "original_name": filename,
            "duration": duration,
        }

        self.send_json({
            "id": session_id,
            "original_name": filename,
            "duration": duration,
            "suggested_start": start,
            **parsed,
        })

    def handle_preview(self) -> None:
        payload = self.read_json()
        session = SESSIONS[payload["id"]]
        source = Path(session["source"])
        preview = Path(session["preview"])
        start = float(payload.get("start") or 0)
        make_preview(source, preview, start)
        self.send_json({"preview_url": f"/tmp/{payload['id']}/preview.mp3"})

    def handle_export(self) -> None:
        payload = self.read_json()
        session = SESSIONS[payload["id"]]
        source = Path(session["source"])
        slug = slugify(payload.get("slug") or payload.get("title") or "beat")
        final_preview = PREVIEWS_DIR / f"{slug}.mp3"
        start = float(payload.get("start") or 0)
        make_preview(source, final_preview, start)

        entry = {
            "title": (payload.get("title") or slug).strip().lower(),
            "bpm": str(payload.get("bpm") or "").strip(),
            "key": str(payload.get("key") or "").strip().lower(),
            "slug": slug,
            "preview": f"previews/{slug}.mp3",
        }
        upsert_beat(entry)

        message = f"exported {entry['title']} to beats/previews/{slug}.mp3"
        if payload.get("push"):
            message += "\n" + commit_and_push(slug)
        self.send_json({"message": message})


def main() -> None:
    ensure_dirs()
    with tempfile.TemporaryDirectory():
        server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
        url = "http://127.0.0.1:8765"
        print(f"beat publisher running at {url}")
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        server.serve_forever()


if __name__ == "__main__":
    main()
