"""Load and quality-gate JSONL without scraping or external service calls."""

import json
from pathlib import Path
from typing import Any

from src.domain.models import JobPosting
from src.domain.validation import validate_posting


def load_jsonl(
    path: str | Path,
    *,
    approved_source_ids: set[str] | None = None,
    allow_synthetic: bool = False,
) -> tuple[list[JobPosting], list[dict[str, Any]]]:
    """Load records only when their source is approved; synthetic input is opt-in."""
    accepted: list[JobPosting] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    approved_source_ids = approved_source_ids or set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("each JSONL line must be a JSON object")
                posting = JobPosting.from_dict(payload)
                errors = validate_posting(posting)
                if posting.posting_id in seen:
                    errors.append("duplicate posting_id")
                elif posting.posting_id:
                    seen.add(posting.posting_id)
                if posting.synthetic and not allow_synthetic:
                    errors.append("synthetic record requires explicit allow_synthetic=True")
                if not posting.synthetic and posting.source_id not in approved_source_ids:
                    errors.append("source_id is not in the approved source registry")
                if errors:
                    rejected.append({"line": line_number, "posting_id": posting.posting_id, "errors": errors})
                else:
                    accepted.append(posting)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                rejected.append({"line": line_number, "errors": [str(exc)]})
    return accepted, rejected
