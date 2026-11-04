"""CLI script to sync jobs from Work24 API or demo JSONL into the database."""

from __future__ import annotations

import argparse
import sys
from src.db.database import init_db, SessionLocal
from src.db.models import JobPostingRecord
from src.ingestion.jsonl import load_jsonl
from src.ingestion.work24_adapter import work24_to_job_posting
from src.ingestion.work24_client import Work24Client, Work24ApiError


def sync_from_work24(api_key: str, pages: int = 1, display: int = 20, region_filter: str | None = None) -> int:
    client = Work24Client(api_key=api_key)
    session = SessionLocal()
    total_saved = 0

    filters = {}
    if region_filter:
        filters["region"] = region_filter

    print(f"Fetching from Work24 API (pages: {pages}, display: {display})...")
    try:
        for page in range(1, pages + 1):
            res = client.list_jobs(start_page=page, display=display, filters=filters if filters else None)
            for raw_job in res.jobs:
                posting = work24_to_job_posting(raw_job)
                record = JobPostingRecord.from_domain(posting)
                session.merge(record)
                total_saved += 1
            session.commit()
            print(f"  Page {page}/{pages} synced ({len(res.jobs)} jobs).")
    except Work24ApiError as err:
        print(f"Work24 API error: {err}", file=sys.stderr)
    finally:
        session.close()

    print(f"Total Work24 jobs synced to DB: {total_saved}")
    return total_saved


def sync_from_jsonl(jsonl_path: str) -> int:
    session = SessionLocal()
    postings, rejected = load_jsonl(jsonl_path, allow_synthetic=True)
    count = 0
    for p in postings:
        record = JobPostingRecord.from_domain(p)
        session.merge(record)
        count += 1
    session.commit()
    session.close()
    print(f"Synced {count} records from {jsonl_path} into DB (rejected: {len(rejected)}).")
    return count


def main():
    parser = argparse.ArgumentParser(description="Sync job postings to database.")
    parser.add_argument("--jsonl", help="Path to jsonl file to import into DB (e.g. data/demo_jobs.jsonl)")
    parser.add_argument("--work24", action="store_true", help="Fetch from Work24 API using WORK24_API_KEY environment variable")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch from Work24 (default: 1)")
    parser.add_argument("--display", type=int, default=20, help="Items per page (default: 20)")
    parser.add_argument("--region", type=str, default="", help="Work24 region code or keyword")

    args = parser.parse_args()
    init_db()

    if args.jsonl:
        sync_from_jsonl(args.jsonl)
    elif args.work24:
        import os
        api_key = os.environ.get("WORK24_API_KEY", "").strip()
        if not api_key:
            print("Error: WORK24_API_KEY environment variable is not set.", file=sys.stderr)
            sys.exit(1)
        sync_from_work24(api_key, pages=args.pages, display=args.display, region_filter=args.region or None)
    else:
        # Default fallback: import demo data
        sync_from_jsonl("data/demo_jobs.jsonl")


if __name__ == "__main__":
    main()
