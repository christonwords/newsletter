import tempfile
import unittest
from pathlib import Path

from tools.beat_publisher.catalog import CatalogStore
from tools.beat_publisher.models import BeatRecord


class CatalogStoreTests(unittest.TestCase):
    def test_round_trip_and_order_survive_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.sqlite3"
            store = CatalogStore(path)
            store.initialize()
            store.upsert(BeatRecord(id="one", title="one", slug="one", status="ready", public_order=0))
            store.upsert(BeatRecord(id="two", title="two", slug="two", status="draft", public_order=1))
            store.set_order(["two", "one"])

            reopened = CatalogStore(path)
            reopened.initialize()
            self.assertEqual([beat.id for beat in reopened.list()], ["two", "one"])

    def test_update_is_persistent(self):
        with tempfile.TemporaryDirectory() as temp:
            store = CatalogStore(Path(temp) / "catalog.sqlite3")
            store.initialize()
            store.upsert(BeatRecord(id="one", title="one", slug="one", status="draft", public_order=0))
            updated = store.update("one", title="edited", preview_start=4.5, status="ready")
            self.assertEqual((updated.title, updated.preview_start, updated.status), ("edited", 4.5, "ready"))

    def test_rejects_invalid_status_and_partial_order(self):
        with tempfile.TemporaryDirectory() as temp:
            store = CatalogStore(Path(temp) / "catalog.sqlite3")
            store.initialize()
            with self.assertRaisesRegex(ValueError, "invalid status"):
                store.upsert(BeatRecord(id="one", title="one", slug="one", status="lost", public_order=0))
            store.upsert(BeatRecord(id="one", title="one", slug="one", status="draft", public_order=0))
            store.upsert(BeatRecord(id="two", title="two", slug="two", status="draft", public_order=1))
            with self.assertRaisesRegex(ValueError, "complete"):
                store.set_order(["one"])


if __name__ == "__main__":
    unittest.main()
