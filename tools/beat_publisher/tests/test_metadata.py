import tempfile
import unittest
from pathlib import Path

from tools.beat_publisher.metadata import fingerprint_file, parse_filename, slugify


class MetadataTests(unittest.TestCase):
    def test_parses_title_key_and_bpm(self):
        parsed = parse_filename("holdher15 d# min 153bpm.wav")
        self.assertEqual((parsed.title, parsed.bpm, parsed.key, parsed.slug), ("holdher15", "153", "d# min", "holdher15"))

    def test_reports_missing_fields(self):
        parsed = parse_filename("untitled beat.wav")
        self.assertIn("bpm missing", parsed.warnings)
        self.assertIn("key missing", parsed.warnings)

    def test_slug_and_fingerprint_are_stable(self):
        self.assertEqual(slugify("A Strange Beat!"), "a-strange-beat")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "beat.wav"
            path.write_bytes(b"one")
            first = fingerprint_file(path)
            path.write_bytes(b"two")
            self.assertNotEqual(first, fingerprint_file(path))


if __name__ == "__main__":
    unittest.main()
