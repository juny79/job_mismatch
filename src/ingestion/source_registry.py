"""Permission gate for registered data sources; performs no network collection."""

import csv
from datetime import date
from pathlib import Path

REQUIRED_COLUMNS = {
    "source_id",
    "source_name",
    "source_url",
    "data_owner",
    "permission_reference",
    "collection_allowed",
    "redistribution_allowed",
    "external_processing_allowed",
    "retention_days",
    "approved_by",
    "approved_at",
    "status",
}


def validate_source_registry(path: str | Path) -> tuple[set[str], list[dict[str, object]]]:
    """Return source IDs explicitly approved for collection and row-level errors.

    A source is usable only when status is approved, collection is explicitly
    allowed, and the permission evidence and accountable owner are recorded.
    Unknown values fail closed. This validates the register, not legal rights.
    """
    approved: set[str] = set()
    errors: list[dict[str, object]] = []
    seen: set[str] = set()

    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_COLUMNS - columns)
        if missing_columns:
            return set(), [{"row": 1, "errors": [f"missing columns: {', '.join(missing_columns)}"]}]

        for row_number, row in enumerate(reader, start=2):
            source_id = (row.get("source_id") or "").strip()
            row_errors: list[str] = []
            if not source_id:
                row_errors.append("source_id is required")
            elif source_id in seen:
                row_errors.append("duplicate source_id")
            else:
                seen.add(source_id)

            if (row.get("status") or "").strip().casefold() != "approved":
                row_errors.append("source status is not approved")
            if (row.get("collection_allowed") or "").strip().casefold() != "yes":
                row_errors.append("collection permission is not explicitly yes")
            for field in ("redistribution_allowed", "external_processing_allowed"):
                if (row.get(field) or "").strip().casefold() not in {"yes", "no", "unknown"}:
                    row_errors.append(f"{field} must be yes, no, or unknown")
            for field in ("source_name", "source_url", "data_owner", "permission_reference", "approved_by", "approved_at"):
                if not (row.get(field) or "").strip():
                    row_errors.append(f"{field} is required")
            try:
                date.fromisoformat((row.get("approved_at") or "").strip()[:10])
            except ValueError:
                row_errors.append("approved_at must contain an ISO-8601 date")
            try:
                retention = int((row.get("retention_days") or "").strip())
                if retention < 0:
                    row_errors.append("retention_days must be non-negative")
            except ValueError:
                row_errors.append("retention_days must be an integer")

            if row_errors:
                errors.append({"row": row_number, "source_id": source_id, "errors": row_errors})
            elif source_id:
                approved.add(source_id)

    return approved, errors
