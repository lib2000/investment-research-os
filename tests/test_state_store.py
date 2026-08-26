import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.state_store import read_json_store, write_json_store  # noqa: E402


class StateStoreTests(unittest.TestCase):
    def test_write_json_store_replaces_a_complete_document_without_temp_residue(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "_system" / "state.json"
            payload = {"updated_at": "2026-08-26T23:00:00+09:00", "items": ["005930"]}

            write_json_store(path, payload)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            self.assertEqual(read_json_store(path, {}), payload)
            self.assertEqual(list(path.parent.glob(".state.json.*.tmp")), [])
