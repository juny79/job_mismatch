"""Deterministic quality summary for a loaded JSONL batch."""

from collections import Counter

from src.domain.models import JobPosting


def quality_report(
    postings: list[JobPosting],
    rejected: list[dict[str, object]],
) -> dict[str, object]:
    review_counts = Counter(posting.review_status for posting in postings)
    salary_counts = Counter(posting.salary.status for posting in postings)
    rejection_reasons = Counter(
        reason
        for record in rejected
        for reason in record.get("errors", [])
    )
    evidence_counts = Counter(item.field for posting in postings for item in posting.evidence)
    total = len(postings)
    completeness_fields = {
        "title": lambda p: p.title,
        "raw_text": lambda p: p.raw_text,
        "collected_at": lambda p: p.collected_at,
        "posted_at": lambda p: p.posted_at,
        "region": lambda p: p.region,
        "role_category": lambda p: p.role_category,
        "company_name": lambda p: p.company_name,
        "required_skills": lambda p: p.required_skills,
        "benefits": lambda p: p.benefits,
    }
    field_completeness = {
        name: {
            "present": sum(bool(getter(posting)) for posting in postings),
            "missing": total - sum(bool(getter(posting)) for posting in postings),
            "denominator": total,
        }
        for name, getter in completeness_fields.items()
    }

    source_approved = [
        posting for posting in postings
        if posting.review_status == "approved" and not posting.synthetic
    ]
    evidence_applicability: Counter[str] = Counter()
    evidence_coverage: Counter[str] = Counter()
    for posting in source_approved:
        present_evidence = {item.field for item in posting.evidence}
        applicable_fields = {"title", "region", "role_category"}
        if posting.salary.status == "reported":
            applicable_fields.add("salary")
        if posting.required_skills:
            applicable_fields.add("required_skills")
        if posting.benefits:
            applicable_fields.add("benefits")
        evidence_applicability.update(applicable_fields)
        evidence_coverage.update(applicable_fields & present_evidence)

    return {
        "valid_records": total,
        "processed_records": total + len(rejected),
        "rejected_records": len(rejected),
        "approved_records": review_counts.get("approved", 0),
        "pending_records": review_counts.get("pending", 0),
        "rejected_review_records": review_counts.get("rejected", 0),
        "synthetic_records": sum(posting.synthetic for posting in postings),
        "salary_status_counts": dict(sorted(salary_counts.items())),
        "field_completeness": field_completeness,
        "evidence_field_counts": dict(sorted(evidence_counts.items())),
        "evidence_coverage": {
            field: {
                "with_evidence": evidence_coverage[field],
                "denominator": denominator,
                "rate": round(evidence_coverage[field] / denominator, 4) if denominator else None,
            }
            for field, denominator in sorted(evidence_applicability.items())
        },
        "evidence_coverage_record_denominator": len(source_approved),
        "rejection_reason_counts": dict(sorted(rejection_reasons.items())),
        "approved_record_denominator": total,
    }
