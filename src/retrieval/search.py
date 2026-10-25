"""Small, deterministic retrieval and aggregation layer for the PoC scaffold."""

from collections import Counter
from dataclasses import dataclass

from src.domain.models import JobPosting


@dataclass(frozen=True)
class SearchHit:
    posting: JobPosting
    matched_terms: tuple[str, ...]


def searchable(posting: JobPosting) -> bool:
    """Only reviewed records enter user-facing retrieval."""
    return posting.review_status == "approved"


def search(postings: list[JobPosting], query: str, region: str | None = None) -> list[SearchHit]:
    terms = tuple(dict.fromkeys(term.casefold() for term in query.split() if term.strip()))
    hits: list[SearchHit] = []
    for posting in postings:
        if not searchable(posting) or (region and region.casefold() not in posting.region.casefold()):
            continue
        text = " ".join((posting.title, posting.region, posting.role_category, posting.raw_text,
                         *posting.required_skills, *posting.benefits)).casefold()
        matches = tuple(term for term in terms if term in text)
        if not terms or matches:
            hits.append(SearchHit(posting, matches))
    return hits


def summary(postings: list[JobPosting]) -> dict[str, object]:
    records = [posting for posting in postings if searchable(posting)]
    salary_records = [
        p for p in records
        if p.salary.status == "reported" and p.salary.minimum is not None and p.salary.unit
    ]
    salary_units = {p.salary.unit for p in salary_records}
    comparable_salary_records = salary_records if len(salary_units) == 1 else []
    skill_counts = Counter(skill for p in records for skill in p.required_skills)
    benefits_counts = Counter(benefit for p in records for benefit in p.benefits)
    return {
        "approved_postings": len(records),
        "salary_minimum_count": len(salary_records),
        "salary_minimum_mean": round(sum(p.salary.minimum for p in comparable_salary_records) / len(comparable_salary_records), 2)
            if comparable_salary_records else None,
        "salary_unit": next(iter(salary_units)) if len(salary_units) == 1 else None,
        "salary_comparability_warning": "Mixed or missing units: mean suppressed" if salary_records and not comparable_salary_records else None,
        "salary_not_stated_count": sum(p.salary.status == "not_stated" for p in records),
        "salary_negotiable_count": sum(p.salary.status == "negotiable" for p in records),
        "top_skills": skill_counts.most_common(10),
        "top_benefits": benefits_counts.most_common(10),
        "excluded_unreviewed_count": len(postings) - len(records),
    }
