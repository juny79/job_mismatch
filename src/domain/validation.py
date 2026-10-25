"""Validation rules shared by ingestion and the prototype search path."""

from .models import JobPosting, REVIEW_STATUSES, SALARY_STATUSES


def validate_posting(posting: JobPosting) -> list[str]:
    errors: list[str] = []
    for field_name in ("posting_id", "source_id", "source_name", "title", "raw_text"):
        if not getattr(posting, field_name).strip():
            errors.append(f"{field_name} is required")
    if posting.salary.status not in SALARY_STATUSES:
        errors.append(f"unsupported salary status: {posting.salary.status}")
    if posting.salary.status == "reported":
        if posting.salary.minimum is None and posting.salary.maximum is None:
            errors.append("reported salary requires at least one numeric bound")
        if posting.salary.minimum is not None and posting.salary.maximum is not None:
            if posting.salary.minimum > posting.salary.maximum:
                errors.append("salary minimum must not exceed maximum")
        if not posting.salary.unit:
            errors.append("reported salary requires a unit")
    elif posting.salary.minimum is not None or posting.salary.maximum is not None:
        errors.append("non-reported salary must not contain numeric bounds")
    if posting.review_status not in REVIEW_STATUSES:
        errors.append(f"unsupported review status: {posting.review_status}")
    if posting.review_status == "approved" and not posting.synthetic:
        if not posting.source_id or not posting.evidence:
            errors.append("approved source posting requires source ID and evidence")
    return errors
