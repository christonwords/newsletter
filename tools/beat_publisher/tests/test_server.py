import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from tools.beat_publisher.server import PublisherApplication, create_server


class ServerTests(unittest.TestCase):
    def test_root_and_token_protected_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = PublisherApplication(root, root / "data", token="test-token")
            server = create_server(app, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(base + "/", timeout=3) as response:
                    self.assertIn("beat publisher", response.read().decode())
                with urllib.request.urlopen(base + "/api/state?token=test-token", timeout=3) as response:
                    self.assertEqual(json.load(response)["beats"], [])
                with self.assertRaises(urllib.error.HTTPError) as blocked:
                    urllib.request.urlopen(base + "/api/state", timeout=3)
                self.assertEqual(blocked.exception.code, 403)
                blocked.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
