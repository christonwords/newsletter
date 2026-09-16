import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from tools.beat_publisher.audio import analyze_source, export_preview, probe_duration


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg tools required")
class AudioTests(unittest.TestCase):
    @staticmethod
    def make_wav(path: Path, seconds: int = 32, rate: int = 8000) -> None:
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, rate, seconds * rate, "NONE", "not compressed"))
            frames = bytearray()
            for index in range(seconds * rate):
                amplitude = 3000 if index < 5 * rate else 12000
                frames.extend(struct.pack("<h", int(amplitude * math.sin(index * 0.07))))
            output.writeframes(frames)

    def test_analysis_produces_fixed_bounded_peaks(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "beat.wav"
            self.make_wav(source)
            result = analyze_source(source)
            self.assertEqual(len(result.peaks), 240)
            self.assertTrue(all(0 <= value <= 255 for value in result.peaks))
            self.assertGreaterEqual(result.suggested_start, 0)
            self.assertLessEqual(result.suggested_start, 2.1)

    def test_export_is_thirty_seconds(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "beat.wav"
            preview = Path(temp) / "preview.mp3"
            self.make_wav(source)
            artifact = export_preview(source, preview, 1.0, normalize=False)
            self.assertAlmostEqual(probe_duration(preview), 30.0, delta=0.05)
            self.assertGreater(artifact.size, 1000)


if __name__ == "__main__":
    unittest.main()
