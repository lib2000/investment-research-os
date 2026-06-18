import unittest
from pathlib import Path

from tools.check_rag_synthesis_store import RagSynthesisEntry


class RagSynthesisStoreCheckTests(unittest.TestCase):
    def test_noop_synthesis_is_marked_for_source_count_skip(self):
        entry = RagSynthesisEntry(
            entry={"source_count": 0, "candidate_count": 0},
            markdown_path=Path("noop.md"),
            json_path=Path("noop.json"),
            payload={},
            rag_connected=True,
        )

        self.assertTrue(entry.is_noop)
        self.assertEqual(entry.source_count, 0)
        self.assertEqual(entry.candidate_count, 0)

    def test_zero_source_with_candidates_is_not_noop(self):
        entry = RagSynthesisEntry(
            entry={},
            markdown_path=Path("weak.md"),
            json_path=Path("weak.json"),
            payload={"source_count": 0, "candidate_count": 3},
            rag_connected=True,
        )

        self.assertFalse(entry.is_noop)
        self.assertEqual(entry.source_count, 0)
        self.assertEqual(entry.candidate_count, 3)


if __name__ == "__main__":
    unittest.main()
