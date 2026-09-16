import unittest

from tools.beat_publisher.models import BeatRecord
from tools.beat_publisher.public_catalog import build_public_catalog, hashed_preview_name


class PublicCatalogTests(unittest.TestCase):
    def test_catalog_filters_and_orders(self):
        peaks = tuple([64] * 240)
        records = [
            BeatRecord(id="two", title="two", slug="two", status="published", public_order=1, preview_peaks=peaks, preview_fingerprint="22222222", published_preview_path="previews/two.mp3"),
            BeatRecord(id="hidden", title="hidden", slug="hidden", status="hidden", public_order=0, preview_peaks=peaks),
            BeatRecord(id="one", title="one", slug="one", status="ready", public_order=0, preview_peaks=peaks, preview_fingerprint="11111111", preview_path="private/one.mp3"),
        ]
        catalog = build_public_catalog(records, "rev1", "2026-09-16T00:00:00Z")
        self.assertEqual(catalog["schemaVersion"], 1)
        self.assertEqual([beat["id"] for beat in catalog["beats"]], ["one", "two"])
        self.assertEqual(len(catalog["beats"][0]["peaks"]), 240)

    def test_hashed_filename(self):
        self.assertEqual(hashed_preview_name("holdher15", "abcdef123456"), "holdher15-abcdef12.mp3")


if __name__ == "__main__":
    unittest.main()
