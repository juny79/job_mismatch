"""Quality-gated local ingestion and retrieval CLI."""

import argparse
import json

from src.ingestion.jsonl import load_jsonl
from src.ingestion.quality import quality_report
from src.ingestion.source_registry import validate_source_registry
from src.retrieval.graphrag import answer_with_graph
from src.retrieval.search import search, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first local GraphRAG PoC scaffold")
    parser.add_argument("--data", required=True, help="Approved JSONL dataset (demo fixture is synthetic)")
    parser.add_argument("--source-registry", help="Approved source registry CSV")
    parser.add_argument("--allow-synthetic", action="store_true", help="Explicitly allow synthetic demo records")
    parser.add_argument("--query", default="", help="Search words or graph entity")
    parser.add_argument("--region", default=None, help="Optional region filter")
    parser.add_argument("--graph", action="store_true", help="Use the deterministic in-memory graph retrieval flow")
    args = parser.parse_args()

    approved_source_ids: set[str] = set()
    registry_errors = []
    if args.source_registry:
        approved_source_ids, registry_errors = validate_source_registry(args.source_registry)
        if registry_errors:
            print(json.dumps({"source_registry_errors": registry_errors}, ensure_ascii=False, indent=2))
            raise SystemExit(2)
    postings, rejected = load_jsonl(
        args.data,
        approved_source_ids=approved_source_ids,
        allow_synthetic=args.allow_synthetic,
    )
    print("DATA QUALITY")
    print(json.dumps(quality_report(postings, rejected), ensure_ascii=False, indent=2))
    if args.graph:
        print("GRAPHRAG EVIDENCE PACKAGE")
        print(json.dumps(answer_with_graph(postings, args.query, args.region), ensure_ascii=False, indent=2))
        return

    print("SUMMARY")
    print(json.dumps(summary(postings), ensure_ascii=False, indent=2))
    print("RESULTS")
    for hit in search(postings, args.query, args.region):
        posting = hit.posting
        print(json.dumps({
            "posting_id": posting.posting_id,
            "title": posting.title,
            "region": posting.region,
            "role_category": posting.role_category,
            "skills": posting.required_skills,
            "benefits": posting.benefits,
            "salary": {
                "raw": posting.salary.raw,
                "status": posting.salary.status,
                "minimum": posting.salary.minimum,
                "maximum": posting.salary.maximum,
                "unit": posting.salary.unit,
            },
            "source": {
                "id": posting.source_id,
                "name": posting.source_name,
                "record_id": posting.source_record_id,
                "url": posting.source_url,
                "collected_at": posting.collected_at,
                "posted_at": posting.posted_at,
            },
            "evidence": [{"field": e.field, "quote": e.quote, "locator": e.locator} for e in posting.evidence],
            "synthetic": posting.synthetic,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
