import json
import tempfile
import unittest
from pathlib import Path

from tools.beat_publisher.catalog import CatalogStore
from tools.beat_publisher.migration import migrate_legacy_catalog


class MigrationTests(unittest.TestCase):
    def test_migration_is_ordered_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            previews = root / "previews"
            previews.mkdir()
            (previews / "one.mp3").write_bytes(b"one")
            legacy = root / "beats.json"
            legacy.write_text(json.dumps([{"title": "one", "slug": "one", "bpm": "140", "key": "c min", "preview": "previews/one.mp3"}]), encoding="utf-8")
            store = CatalogStore(root / "catalog.sqlite3")
            store.initialize()
            first = migrate_legacy_catalog(store, legacy, previews, analyze_peaks=False)
            second = migrate_legacy_catalog(store, legacy, previews, analyze_peaks=False)
            self.assertEqual((first.imported, second.imported), (1, 0))
            self.assertEqual(store.list()[0].status, "published")
            self.assertEqual(store.list()[0].published_preview_path, "previews/one.mp3")


if __name__ == "__main__":
    unittest.main()
