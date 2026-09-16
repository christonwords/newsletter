from __future__ import annotations

import json
import mimetypes
import secrets
from dataclasses import asdict
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .audio import export_preview
from .catalog import CatalogStore
from .jobs import BatchImporter
from .publish import prepare_review, publish, retry_push


class PublisherApplication:
    def __init__(self, repo_root: Path, data_dir: Path, token: str | None = None):
        self.repo_root = Path(repo_root)
        self.data_dir = Path(data_dir)
        self.static_dir = Path(__file__).parent / "static"
        self.token = token or secrets.token_urlsafe(24)
        self.store = CatalogStore(self.data_dir / "catalog.sqlite3")
        self.store.initialize()
        self.importer = BatchImporter(self.store, self.data_dir / "sources")
        self.reviews: dict[str, tuple[tuple[str, str, str], ...]] = {}
        (self.data_dir / "previews").mkdir(parents=True, exist_ok=True)

    def state(self) -> dict:
        return {
            "beats": [record.to_dict() for record in self.store.list()],
            "publish": {
                "state": self.store.get_setting("publish_state", "saved locally"),
                "commit": self.store.get_setting("last_commit"),
            },
        }


def parse_uploads(body: bytes, content_type: str) -> list[tuple[str, bytes]]:
    message = BytesParser(policy=default).parsebytes(f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body)
    uploads = []
    for part in message.iter_parts():
        filename = part.get_filename()
        if filename:
            uploads.append((Path(filename).name, part.get_payload(decode=True)))
    return uploads


def make_handler(application: PublisherApplication):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def send_bytes(self, payload: bytes, content_type: str, status=HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def send_json(self, value: dict, status=HTTPStatus.OK) -> None:
            self.send_bytes(json.dumps(value).encode("utf-8"), "application/json; charset=utf-8", status)

        def read_json(self) -> dict:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8"))

        def authorized(self, state_change: bool = False) -> bool:
            parsed = urlparse(self.path)
            supplied = self.headers.get("X-Beat-Publisher-Token") or parse_qs(parsed.query).get("token", [""])[0]
            if not secrets.compare_digest(supplied, application.token):
                self.send_json({"error": "unauthorized"}, HTTPStatus.FORBIDDEN)
                return False
            if state_change:
                origin = self.headers.get("Origin")
                expected = f"http://{self.headers.get('Host')}"
                if origin and origin != expected:
                    self.send_json({"error": "origin rejected"}, HTTPStatus.FORBIDDEN)
                    return False
            return True

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                html = (application.static_dir / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", application.token)
                self.send_bytes(html.encode(), "text/html; charset=utf-8")
                return
            if parsed.path in {"/styles.css", "/app.js"}:
                path = application.static_dir / parsed.path.removeprefix("/")
                self.send_bytes(path.read_bytes(), mimetypes.guess_type(path)[0] or "text/plain")
                return
            if parsed.path == "/api/state" and self.authorized():
                self.send_json(application.state())
                return
            if parsed.path.startswith("/api/audio/") and self.authorized():
                beat_id = parsed.path.rsplit("/", 1)[-1]
                beat = application.store.get(beat_id)
                kind = parse_qs(parsed.query).get("kind", ["preview"])[0]
                path = Path(beat.source_path if kind == "source" else beat.preview_path) if beat else Path()
                if beat and path.is_file():
                    self.send_bytes(path.read_bytes(), "audio/wav" if kind == "source" else "audio/mpeg")
                    return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_PATCH(self) -> None:
            if not self.authorized(True):
                return
            try:
                beat_id = urlparse(self.path).path.rsplit("/", 1)[-1]
                payload = self.read_json()
                allowed = {"title", "bpm", "key", "slug", "preview_start", "normalize", "status"}
                changes = {key: value for key, value in payload.items() if key in allowed}
                if "title" in changes:
                    changes["title"] = str(changes["title"]).strip().lower()
                if "key" in changes:
                    changes["key"] = str(changes["key"]).strip().lower()
                beat = application.store.update(beat_id, **changes)
                self.send_json({"beat": beat.to_dict()})
            except Exception as error:
                self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def do_POST(self) -> None:
            if not self.authorized(True):
                return
            path = urlparse(self.path).path
            try:
                if path == "/api/import":
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    uploads = parse_uploads(body, self.headers.get("Content-Type", ""))
                    results = [asdict(application.importer.import_upload(name, data)) for name, data in uploads]
                    self.send_json({"results": results, **application.state()})
                    return
                if path == "/api/order":
                    application.store.set_order(self.read_json().get("ids", []))
                    self.send_json(application.state())
                    return
                if path.endswith("/preview"):
                    beat_id = path.split("/")[-2]
                    beat = application.store.get(beat_id)
                    if not beat or not Path(beat.source_path).is_file():
                        raise ValueError("source wav is missing")
                    output = application.data_dir / "previews" / f"{beat.id}.mp3"
                    artifact = export_preview(Path(beat.source_path), output, beat.preview_start, beat.normalize)
                    beat = application.store.update(beat.id, preview_path=str(output), preview_peaks=artifact.peaks, preview_fingerprint=artifact.fingerprint)
                    self.send_json({"beat": beat.to_dict(), "url": f"/api/audio/{beat.id}?kind=preview&token={application.token}"})
                    return
                if path.endswith("/approve"):
                    beat_id = path.split("/")[-2]
                    beat = application.store.get(beat_id)
                    if not beat or not beat.preview_path:
                        raise ValueError("make the encoded preview first")
                    self.send_json({"beat": application.store.update(beat_id, status="ready").to_dict()})
                    return
                if path == "/api/publish/prepare":
                    review = prepare_review(application.store)
                    application.reviews[review.id] = tuple(
                        (record.id, record.updated_at, record.status)
                        for record in application.store.list()
                    )
                    self.send_json({"review": review.to_dict()})
                    return
                if path == "/api/publish/confirm":
                    review_id = self.read_json().get("reviewId", "")
                    reviewed_state = application.reviews.pop(review_id, None)
                    current_state = tuple(
                        (record.id, record.updated_at, record.status)
                        for record in application.store.list()
                    )
                    if reviewed_state is None:
                        raise ValueError("publish review expired; review the batch again")
                    if reviewed_state != current_state:
                        raise ValueError("the batch changed after review; review it again")
                    result = publish(application.store, application.repo_root, review_id, push=True)
                    self.send_json({"result": result, **application.state()})
                    return
                if path == "/api/publish/retry":
                    self.send_json({"result": retry_push(application.store, application.repo_root), **application.state()})
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except Exception as error:
                self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    return Handler


def create_server(application: PublisherApplication, port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(application))
