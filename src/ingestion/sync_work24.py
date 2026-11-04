"""CLI script and service function to sync jobs from Work24 API or demo JSONL into the database."""

from __future__ import annotations

import argparse
import sys
from src.db.database import init_db, SessionLocal
from src.db.models import JobPostingRecord
from src.ingestion.jsonl import load_jsonl
from src.ingestion.work24_adapter import work24_to_job_posting
from src.ingestion.work24_client import Work24Client, Work24ApiError

# Work24 Standard Administrative Region Codes for Bu-Ul-Gyeong (부산, 울산, 경남)
BU_UL_GYEONG_REGIONS = {
    "부산": "26000",
    "울산": "31000",
    "경남": "48000",
}


def sync_from_work24(
    api_key: str,
    start_page: int = 1,
    pages: int = 1,
    display: int = 100,
    region_filter: str | None = None,
    use_fallback_on_error: bool = True,
) -> dict[str, int | list[str] | bool]:
    """Fetch jobs from Work24 API (defaults to Busan, Ulsan, Gyeongnam, 100 per region) and save to DB."""
    init_db()
    session = SessionLocal()
    total_saved = 0
    errors: list[str] = []
    used_fallback = False

    if region_filter:
        region_targets = [(region_filter, region_filter)]
    else:
        region_targets = list(BU_UL_GYEONG_REGIONS.items())

    total_in_db = 0
    try:
        if api_key and api_key.strip():
            client = Work24Client(api_key=api_key, timeout=12.0)
            for label, code in region_targets:
                filters = {"region": code} if code else None
                for page in range(start_page, start_page + pages):
                    try:
                        res = client.list_jobs(start_page=page, display=display, filters=filters)
                        for raw_job in res.jobs:
                            posting = work24_to_job_posting(raw_job)
                            record = JobPostingRecord.from_domain(posting)
                            session.merge(record)
                            total_saved += 1
                        session.commit()
                    except Exception as err:
                        errors.append(f"{label}(p{page}): {err}")
        else:
            errors.append("WORK24_API_KEY가 비어 있습니다.")

        # If Work24 OpenAPI returned an XML error or blocked overseas Vercel IPs (0 saved),
        # automatically populate Bu-Ul-Gyeong postings for the requested pages so the DB & GraphRAG work seamlessly.
        if total_saved == 0 and use_fallback_on_error:
            from src.ingestion.buulgyeong_seed import build_buulgyeong_seed_postings
            batch_size = display * len(region_targets) * max(1, pages)
            offset = max(0, (start_page - 1) * (display * len(region_targets)))
            seed_postings = build_buulgyeong_seed_postings(target_count=batch_size, start_index=offset)
            for posting in seed_postings:
                record = JobPostingRecord.from_domain(posting)
                session.merge(record)
                total_saved += 1
            session.commit()
            used_fallback = True
    finally:
        try:
            total_in_db = session.query(JobPostingRecord).count()
        except Exception as db_err:
            errors.append(f"DB count error: {db_err}")
        session.close()

    return {
        "saved": total_saved,
        "total_in_db": total_in_db,
        "errors": errors,
        "used_fallback": used_fallback,
    }


def sync_from_jsonl(jsonl_path: str) -> int:
    init_db()
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
    parser.add_argument("--start-page", type=int, default=1, help="Start page number (default: 1)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to fetch per region from Work24 (default: 1)")
    parser.add_argument("--display", type=int, default=100, help="Items per page (default: 100)")
    parser.add_argument("--region", type=str, default="", help="Work24 region code (e.g. 26000 for Busan, 31000 for Ulsan, 48000 for Gyeongnam)")

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
        result = sync_from_work24(
            api_key,
            start_page=args.start_page,
            pages=args.pages,
            display=args.display,
            region_filter=args.region or None,
        )
        print(f"Sync result: {result}")
    else:
        sync_from_jsonl("data/demo_jobs.jsonl")


if __name__ == "__main__":
    main()
