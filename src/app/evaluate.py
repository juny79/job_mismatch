"""Offline, deterministic retrieval evaluation (synthetic fixture by default)."""

import argparse
import json
import math
from pathlib import Path
from typing import Any

from src.ingestion.jsonl import load_jsonl
from src.retrieval.graphrag import build_job_graph, retrieve_graph
from src.retrieval.hybrid import hybrid_search
from src.retrieval.recommend import recommend
from src.retrieval.search import search


def _evaluate_mode(postings: list[Any], cases: list[dict[str, Any]], mode: str, k: int) -> dict[str, Any]:
    case_rows = []
    precisions = []
    recalls = []
    reciprocal_ranks = []
    evidence_rates = []
    abstention_correct = []

    for case in cases:
        query = str(case.get("query", ""))
        region = str(case.get("region", "")) or None
        relevant = set(case.get("relevant_ids", []))
        if mode == "keyword":
            hits = [hit.posting for hit in search(postings, query, region)]
        elif mode == "graph":
            graph = build_job_graph(postings)
            hits = [hit.posting for hit in retrieve_graph(graph, query, region)]
        else:
            hits = [hit.posting for hit in hybrid_search(postings, query, region, limit=k)]

        ranked_ids = [posting.posting_id for posting in hits[:k]]
        relevant_positions = [index + 1 for index, posting_id in enumerate(ranked_ids) if posting_id in relevant]
        matched = len(set(ranked_ids) & relevant)
        precisions.append(matched / k if k else 0.0)
        if relevant:
            recalls.append(matched / len(relevant))
            reciprocal_ranks.append(1 / relevant_positions[0] if relevant_positions else 0.0)
        relevant_retrieved = [posting for posting in hits[:k] if posting.posting_id in relevant]
        # A non-empty but irrelevant result is still a false answer, not a
        # successful non-abstention. Compare the retrieval decision to qrels.
        abstention_correct.append(not ranked_ids if not relevant else bool(relevant_retrieved))

        if relevant_retrieved:
            evidence_rates.extend(bool(posting.evidence) for posting in relevant_retrieved)

        case_rows.append({
            "id": case.get("id", ""),
            "query": query,
            "expected_ids": sorted(relevant),
            "ranked_ids": ranked_ids,
            "relevant_hits": matched,
            "abstained": not ranked_ids,
            "answerability_correct": abstention_correct[-1],
        })

    mean = lambda values: round(sum(values) / len(values), 4) if values else None
    return {
        "mode": mode,
        "k": k,
        "case_count": len(cases),
        "precision_at_k": mean(precisions),
        "recall_at_k": mean(recalls),
        "mrr": mean(reciprocal_ranks),
        "relevant_result_evidence_coverage": mean(evidence_rates),
        "abstention_accuracy": mean(abstention_correct),
        "cases": case_rows,
    }


def _evaluate_recommendations(
    postings: list[Any], cases: list[dict[str, Any]], k: int,
) -> dict[str, Any]:
    rows = []
    precisions, recalls, reciprocal_ranks, ndcgs, evidence_coverage, abstention = [], [], [], [], [], []
    required_checks, required_violations = 0, 0
    for case in cases:
        hits = recommend(postings, **case.get("preferences", {}), limit=k)
        ids = [hit.posting.posting_id for hit in hits]
        relevant = set(case.get("relevant_ids", []))
        matched = len(set(ids) & relevant)
        precisions.append(matched / k if k else 0.0)
        if relevant:
            recalls.append(matched / len(relevant))
            ranks = [index + 1 for index, posting_id in enumerate(ids) if posting_id in relevant]
            reciprocal_ranks.append(1 / ranks[0] if ranks else 0.0)
            dcg = sum(1 / math.log2(rank + 1) for rank in ranks)
            ideal = sum(1 / math.log2(rank + 1)
                        for rank in range(1, min(len(relevant), k) + 1))
            ndcgs.append(dcg / ideal if ideal else 0.0)
        abstention.append((not ids) == (not relevant))
        for hit in hits:
            evidence_coverage.append(bool(hit.evidence))
            for condition in hit.conditions:
                if condition["required"]:
                    required_checks += 1
                    required_violations += condition["status"] != "match"
        rows.append({
            "id": case.get("id", ""), "expected_ids": sorted(relevant),
            "ranked_ids": ids, "abstained": not ids,
            "answerability_correct": abstention[-1],
        })

    mean = lambda values: round(sum(values) / len(values), 4) if values else None
    return {
        "mode": "deterministic_recommendation", "k": k, "case_count": len(cases),
        "precision_at_k": mean(precisions), "recall_at_k": mean(recalls),
        "mrr": mean(reciprocal_ranks), "ndcg_at_k": mean(ndcgs),
        "required_condition_violation_rate": required_violations / required_checks if required_checks else 0.0,
        "evidence_coverage": mean(evidence_coverage),
        "abstention_accuracy": mean(abstention), "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic retrieval against a fixed relevance set")
    parser.add_argument("--data", required=True, help="JSONL dataset; non-synthetic sources are rejected without registry approval")
    parser.add_argument("--cases", required=True, help="JSON file containing fixed queries and relevant posting IDs")
    parser.add_argument("--allow-synthetic", action="store_true", required=True, help="Explicitly opt in to synthetic evaluation records")
    parser.add_argument("--recommendation-cases", help="Optional fixed condition-based recommendation evaluation JSON")
    parser.add_argument("--k", type=int, default=5, help="Cutoff for precision/recall ranking metrics")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k must be positive")

    postings, rejected = load_jsonl(args.data, allow_synthetic=args.allow_synthetic)
    cases_payload = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    cases = cases_payload.get("cases", [])
    if not isinstance(cases, list) or not cases:
        parser.error("evaluation file must contain a non-empty 'cases' list")
    if any(not isinstance(case.get("relevant_ids", []), list) for case in cases):
        parser.error("each case relevant_ids must be a list")

    result = {
        "notice": "Synthetic-fixture metrics are regression checks, not estimates of real-world retrieval quality.",
        "dataset": cases_payload.get("dataset", args.data),
        "accepted_records": len(postings),
        "rejected_records": len(rejected),
        "rejection_reasons": sorted({reason for row in rejected for reason in row.get("errors", [])}),
        "modes": [
            _evaluate_mode(postings, cases, mode, args.k)
            for mode in ("keyword", "graph", "hybrid")
        ],
    }
    if args.recommendation_cases:
        recommendation_payload = json.loads(Path(args.recommendation_cases).read_text(encoding="utf-8"))
        recommendation_cases = recommendation_payload.get("cases", [])
        if not isinstance(recommendation_cases, list) or not recommendation_cases:
            parser.error("recommendation evaluation file must contain non-empty 'cases'")
        result["recommendation_evaluation"] = _evaluate_recommendations(
            postings, recommendation_cases, args.k,
        )
        result["recommendation_evaluation"]["dataset"] = recommendation_payload.get(
            "dataset", args.data,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
