"""CLI demo: python -m src.app.cli --data data/demo_jobs.jsonl"""

import argparse
import json

from src.ingestion.jsonl import load_jsonl
from src.retrieval.search import search, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first local GraphRAG PoC scaffold")
    parser.add_argument("--data", required=True, help="Approved JSONL dataset (demo fixture is synthetic)")
    parser.add_argument("--query", default="", help="Search words")
    parser.add_argument("--region", default=None, help="Optional region filter")
    args = parser.parse_args()

    postings, rejected = load_jsonl(args.data)
    print("DATA QUALITY")
    print(json.dumps({"loaded": len(postings), "rejected": rejected}, ensure_ascii=False, indent=2))
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
            "source": {"id": posting.source_id, "name": posting.source_name, "collected_at": posting.collected_at},
            "evidence": [{"field": e.field, "quote": e.quote, "locator": e.locator} for e in posting.evidence],
            "synthetic": posting.synthetic,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
