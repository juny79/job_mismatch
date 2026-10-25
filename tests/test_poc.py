import json
import tempfile
import unittest
from pathlib import Path

from src.ingestion.jsonl import load_jsonl
from src.retrieval.search import search, summary


class PoCTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parents[1] / "data" / "demo_jobs.jsonl"
        self.postings, self.rejected = load_jsonl(path)

    def test_demo_fixture_is_explicitly_synthetic(self):
        self.assertEqual([], self.rejected)
        self.assertTrue(all(posting.synthetic for posting in self.postings))

    def test_unreviewed_records_are_not_retrieved_or_aggregated(self):
        self.assertEqual(1, len(search(self.postings, "PLC")))
        result = summary(self.postings)
        self.assertEqual(2, result["approved_postings"])
        self.assertEqual(1, result["excluded_unreviewed_count"])

    def test_salary_missing_is_not_imputed(self):
        busan = next(p for p in self.postings if p.region.startswith("부산"))
        self.assertEqual("not_stated", busan.salary.status)
        self.assertIsNone(busan.salary.minimum)

    def test_duplicate_and_invalid_json_are_quarantined(self):
        source = Path(__file__).parents[1] / "data" / "demo_jobs.jsonl"
        lines = source.read_text(encoding="utf-8").splitlines()
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "input.jsonl"
            candidate.write_text("\n".join([lines[0], lines[0], "{bad json", "[]"]) + "\n", encoding="utf-8")
            accepted, rejected = load_jsonl(candidate)
        self.assertEqual(1, len(accepted))
        self.assertEqual(3, len(rejected))
        self.assertIn("duplicate posting_id", rejected[0]["errors"])

    def test_source_evidence_is_returned_for_search_hits(self):
        hits = search(self.postings, "ROS2", region="경남")
        self.assertEqual(1, len(hits))
        self.assertEqual("DEMO-CW-001", hits[0].posting.posting_id)
        self.assertTrue(hits[0].posting.evidence)


if __name__ == "__main__":
    unittest.main()
