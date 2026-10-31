import csv
from dataclasses import replace
from datetime import date, timedelta
import tempfile
import unittest
from pathlib import Path

from src.app.evaluate import _evaluate_mode, _evaluate_recommendations
from src.app.web import build_recommendation_payload, build_search_payload
from src.ingestion.jsonl import load_jsonl
from src.ingestion.quality import quality_report
from src.ingestion.source_registry import REQUIRED_COLUMNS, validate_source_registry
from src.retrieval.graphrag import answer_with_graph, build_job_graph
from src.retrieval.hybrid import hybrid_search
from src.retrieval.recommend import recommend
from src.retrieval.search import search, summary


class PoCTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).parents[1] / "data" / "demo_jobs.jsonl"
        self.postings, self.rejected = load_jsonl(path, allow_synthetic=True)

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
            accepted, rejected = load_jsonl(candidate, allow_synthetic=True)
        self.assertEqual(1, len(accepted))
        self.assertEqual(3, len(rejected))
        self.assertIn("duplicate posting_id", rejected[0]["errors"])

    def test_synthetic_records_are_rejected_without_explicit_opt_in(self):
        path = Path(__file__).parents[1] / "data" / "demo_jobs.jsonl"
        postings, rejected = load_jsonl(path)
        self.assertEqual([], postings)
        self.assertEqual(3, len(rejected))
        self.assertTrue(all("synthetic record requires" in error for row in rejected for error in row["errors"]))

    def test_source_registry_fails_closed_and_accepts_explicit_approval(self):
        approved_row = {
            "source_id": "SRC-1",
            "source_name": "Test source",
            "source_url": "https://example.invalid/jobs",
            "data_owner": "Data owner",
            "permission_reference": "approval-123",
            "collection_allowed": "yes",
            "redistribution_allowed": "no",
            "external_processing_allowed": "no",
            "retention_days": "30",
            "approved_by": "Approver",
            "approved_at": "2025-01-01",
            "status": "approved",
            "notes": "test only",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "registry.csv"
            with registry.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=sorted(REQUIRED_COLUMNS | {"notes"}))
                writer.writeheader()
                writer.writerow(approved_row)
            approved, errors = validate_source_registry(registry)
        self.assertEqual({"SRC-1"}, approved)
        self.assertEqual([], errors)

        approved_row["collection_allowed"] = "unknown"
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "registry.csv"
            with registry.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=sorted(REQUIRED_COLUMNS | {"notes"}))
                writer.writeheader()
                writer.writerow(approved_row)
            approved, errors = validate_source_registry(registry)
        self.assertEqual(set(), approved)
        self.assertTrue(errors)

    def test_quality_report_keeps_denominators_and_rejection_reasons(self):
        report = quality_report(self.postings, self.rejected)
        self.assertEqual(3, report["valid_records"])
        self.assertEqual(2, report["approved_records"])
        self.assertEqual(3, report["approved_record_denominator"])
        self.assertEqual(1, report["pending_records"])
        self.assertEqual(3, report["processed_records"])
        self.assertEqual(
            {"present": 3, "missing": 0, "denominator": 3},
            report["field_completeness"]["title"],
        )
        self.assertEqual(0, report["evidence_coverage_record_denominator"])
        self.assertEqual({}, report["evidence_coverage"])

    def test_source_evidence_is_returned_for_search_hits(self):
        hits = search(self.postings, "ROS2", region="경남")
        self.assertEqual(1, len(hits))
        self.assertEqual("DEMO-CW-001", hits[0].posting.posting_id)
        self.assertTrue(hits[0].posting.evidence)

    def test_graph_contains_approved_relationships_and_excludes_pending_records(self):
        graph = build_job_graph(self.postings)
        self.assertEqual(2, len(graph.postings))
        self.assertNotIn("DEMO-UL-001", graph.postings)
        self.assertTrue(any(edge.relationship == "REQUIRES_SKILL" for edge in graph.edges))
        skill_edges = [edge for edge in graph.edges if edge.relationship == "REQUIRES_SKILL"]
        self.assertTrue(all(edge.evidence for edge in skill_edges))

    def test_graph_answer_returns_citations_and_abstains_when_empty(self):
        answer = answer_with_graph(self.postings, "Python", region="부산")
        self.assertEqual(1, answer["result_count"])
        self.assertEqual("DEMO-BS-001", answer["results"][0]["posting_id"])
        self.assertTrue(answer["results"][0]["synthetic"])
        self.assertTrue(answer["results"][0]["evidence"])
        self.assertIn("실제 시장 근거가 아닙니다", answer["message"])

        empty = answer_with_graph(self.postings, "quantum", region="부산")
        self.assertTrue(empty["abstained"])
        self.assertEqual(0, empty["result_count"])

    def test_web_search_payload_returns_cited_approved_records(self):
        payload = build_search_payload(self.postings, self.rejected, "Python", "부산")
        self.assertEqual("keyword", payload["mode"])
        self.assertEqual(1, payload["result_count"])
        result = payload["results"][0]
        self.assertEqual("DEMO-BS-001", result["posting_id"])
        self.assertTrue(result["synthetic"])
        self.assertTrue(result["evidence"])
        self.assertEqual(["경남 창원", "부산 센텀"], payload["regions"])

    def test_web_graph_payload_abstains_when_no_approved_match(self):
        payload = build_search_payload(self.postings, self.rejected, "quantum", "부산", graph=True)
        self.assertEqual("graph", payload["mode"])
        self.assertEqual(0, payload["result_count"])
        self.assertEqual([], payload["results"])

    def test_recommendation_applies_required_filters_and_evidence_supported_preferences(self):
        hits = recommend(
            self.postings,
            region="부산",
            role_category="AI/SW",
            required_skills=["Python"],
            preferred_skills=["PyTorch"],
            preferred_benefits=["유연근무"],
        )
        self.assertEqual(1, len(hits))
        hit = hits[0]
        self.assertEqual("DEMO-BS-001", hit.posting.posting_id)
        self.assertEqual(100.0, hit.score)
        self.assertEqual(("python",), hit.matched_required_skills)
        self.assertTrue(all(item["status"] == "match" for item in hit.conditions))
        self.assertEqual(
            {"recruitment_status", "region", "role_category", "required_skills", "benefits"},
            {item.field for item in hit.evidence},
        )

    def test_recommendation_excludes_closed_and_expired_records(self):
        busan = next(p for p in self.postings if p.region.startswith("부산"))
        closed = replace(busan, recruitment_status="closed")
        expired = replace(busan, expires_at=(date.today() - timedelta(days=1)).isoformat())
        self.assertEqual([], recommend([closed], region="부산"))
        self.assertEqual([], recommend([expired], region="부산"))

    def test_recommendation_abstains_for_missing_required_salary_or_no_conditions(self):
        self.assertEqual([], recommend(self.postings))
        hits = recommend(self.postings, region="부산", salary_minimum=4000, salary_required=True)
        self.assertEqual([], hits)
        optional = recommend(self.postings, region="부산", salary_minimum=4000)
        self.assertEqual(1, len(optional))
        self.assertEqual("unknown", optional[0].conditions[-1]["status"])

    def test_web_recommendation_contract_is_transient_explainable_and_fails_closed(self):
        payload = build_recommendation_payload(self.postings, {
            "region": "부산", "role_category": "AI/SW", "required_skills": "Python",
            "preferred_benefits": "유연근무",
        })
        self.assertEqual("deterministic_recommendation_preview", payload["mode"])
        self.assertFalse(payload["abstained"])
        self.assertEqual("DEMO-BS-001", payload["results"][0]["posting_id"])
        self.assertTrue(payload["results"][0]["evidence"])
        self.assertIn("보장하지 않습니다", payload["message"])

        empty = build_recommendation_payload(self.postings, {})
        self.assertTrue(empty["abstained"])
        with self.assertRaises(ValueError):
            build_recommendation_payload(self.postings, {"age": 20})

    def test_recommendation_evaluator_covers_relevance_and_abstention_cases(self):
        cases_path = Path(__file__).parents[1] / "data" / "recommendation_eval_synthetic.json"
        import json
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
        result = _evaluate_recommendations(self.postings, cases, 5)
        self.assertEqual(4, result["case_count"])
        self.assertEqual(1.0, result["abstention_accuracy"])
        self.assertEqual(0.0, result["required_condition_violation_rate"])
        self.assertEqual(["DEMO-BS-001"], result["cases"][0]["ranked_ids"])

    def test_evaluator_does_not_count_irrelevant_hits_as_answerable(self):
        cases = [
            {"id": "wrong-hit", "query": "Python", "relevant_ids": ["NOT-IN-DATASET"]},
            {"id": "correct-abstain", "query": "quantum", "relevant_ids": []},
        ]
        result = _evaluate_mode(self.postings, cases, "keyword", 5)
        self.assertEqual(0.5, result["abstention_accuracy"])
        self.assertFalse(result["cases"][0]["answerability_correct"])
        self.assertTrue(result["cases"][1]["answerability_correct"])

    def test_hybrid_retrieval_explains_lexical_and_graph_matches(self):
        hits = hybrid_search(self.postings, "Python", region="부산")
        self.assertEqual(1, len(hits))
        self.assertEqual("DEMO-BS-001", hits[0].posting.posting_id)
        self.assertIn("lexical", hits[0].channels)
        self.assertIn("graph", hits[0].channels)
        self.assertIn("required_skills", hits[0].matched_fields)
        self.assertTrue(hits[0].evidence)

        payload = build_search_payload(self.postings, self.rejected, "Python", "부산", "hybrid")
        self.assertEqual("hybrid", payload["mode"])
        self.assertEqual(1, payload["result_count"])
        self.assertIn("score", payload["results"][0])
        self.assertTrue(payload["results"][0]["graph_paths"])


if __name__ == "__main__":
    unittest.main()
