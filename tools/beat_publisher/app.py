from __future__ import annotations

import argparse
import shutil
import threading
import webbrowser
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.beat_publisher.migration import migrate_legacy_catalog
    from tools.beat_publisher.server import PublisherApplication, create_server
else:
    from .migration import migrate_legacy_catalog
    from .server import PublisherApplication, create_server


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
DATA_DIR = REPO_ROOT / ".beat_publisher_data"


def check_prerequisites() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe", "git") if not shutil.which(name)]
    if missing:
        raise RuntimeError(f"missing required command: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="local batch beat publisher")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    check_prerequisites()
    application = PublisherApplication(REPO_ROOT, DATA_DIR)
    migration = migrate_legacy_catalog(application.store, REPO_ROOT / "beats" / "beats.json", REPO_ROOT / "beats" / "previews")
    server = create_server(application, args.port)
    url = f"http://127.0.0.1:{args.port}/?token={application.token}"
    print(f"beat publisher running at {url}")
    if migration.imported:
        print(f"imported {migration.imported} existing preview(s) into the local catalog")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
