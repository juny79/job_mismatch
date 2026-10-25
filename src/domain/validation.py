"""Validation rules shared by ingestion and the prototype search path."""

from datetime import date, datetime

from .models import JobPosting, REVIEW_STATUSES, SALARY_STATUSES


def _valid_date(value: str) -> bool:
    try:
        if "T" in value or " " in value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_posting(posting: JobPosting) -> list[str]:
    errors: list[str] = []
    for field_name in ("posting_id", "source_id", "source_name", "collected_at", "title", "raw_text"):
        if not getattr(posting, field_name).strip():
            errors.append(f"{field_name} is required")
    for field_name in ("collected_at", "posted_at", "expires_at", "reviewed_at"):
        value = getattr(posting, field_name)
        if value and not _valid_date(value):
            errors.append(f"{field_name} must be an ISO-8601 date or datetime")
    if posting.posted_at and posting.expires_at and _valid_date(posting.posted_at) and _valid_date(posting.expires_at):
        posted = date.fromisoformat(posting.posted_at[:10])
        expires = date.fromisoformat(posting.expires_at[:10])
        if expires < posted:
            errors.append("expires_at must not precede posted_at")

    if posting.salary.status not in SALARY_STATUSES:
        errors.append(f"unsupported salary status: {posting.salary.status}")
    bounds = (posting.salary.minimum, posting.salary.maximum)
    for bound_name, bound in zip(("minimum", "maximum"), bounds):
        if bound is not None and (isinstance(bound, bool) or not isinstance(bound, int) or bound < 0):
            errors.append(f"salary {bound_name} must be a non-negative integer")
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
    for evidence in posting.evidence:
        if not evidence.field.strip() or not evidence.quote.strip() or not evidence.locator.strip():
            errors.append("each evidence item requires field, quote, and locator")
            break
    if posting.review_status == "approved" and not posting.synthetic:
        if not posting.source_id or not posting.evidence:
            errors.append("approved source posting requires source ID and evidence")
        evidence_fields = {item.field for item in posting.evidence}
        extracted_fields = {"title", "region", "role_category"}
        if posting.salary.status == "reported":
            extracted_fields.add("salary")
        if posting.required_skills:
            extracted_fields.add("required_skills")
        if posting.benefits:
            extracted_fields.add("benefits")
        missing_evidence = sorted(extracted_fields - evidence_fields)
        if missing_evidence:
            errors.append(f"approved source posting lacks field evidence: {', '.join(missing_evidence)}")
        for field_name in ("reviewer", "reviewed_at", "data_version", "transform_version"):
            if not getattr(posting, field_name).strip():
                errors.append(f"approved source posting requires {field_name}")
    return errors
