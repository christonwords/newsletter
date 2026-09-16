import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from tools.beat_publisher.catalog import CatalogStore
from tools.beat_publisher.jobs import BatchImporter


class JobsTests(unittest.TestCase):
    @staticmethod
    def make_wav(path: Path, seconds: int = 31) -> None:
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, 8000, seconds * 8000, "NONE", "not compressed"))
            output.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(i * 0.05))) for i in range(seconds * 8000)))

    def test_batch_import_is_persistent_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "memory c min 150bpm.wav"
            self.make_wav(source)
            store = CatalogStore(root / "catalog.sqlite3")
            store.initialize()
            importer = BatchImporter(store, root / "sources", workers=1)
            first = importer.import_paths([source])[0]
            second = importer.import_paths([source])[0]
            self.assertEqual(first.state, "imported")
            self.assertEqual(second.state, "duplicate")
            self.assertEqual(len(store.list()), 1)
            self.assertEqual(len(store.list()[0].source_peaks), 240)


if __name__ == "__main__":
    unittest.main()
