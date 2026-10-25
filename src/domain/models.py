"""Core data contract for source-traceable job postings."""

from dataclasses import dataclass, field
from typing import Any

SALARY_STATUSES = {"reported", "not_stated", "negotiable", "not_applicable", "extraction_failed", "review_pending"}
REVIEW_STATUSES = {"pending", "approved", "rejected"}


@dataclass(frozen=True)
class Salary:
    raw: str
    status: str
    minimum: int | None = None
    maximum: int | None = None
    unit: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Salary":
        return cls(
            raw=str(value.get("raw", "")),
            status=str(value.get("status", "review_pending")),
            minimum=value.get("minimum"),
            maximum=value.get("maximum"),
            unit=value.get("unit"),
        )


@dataclass(frozen=True)
class Evidence:
    field: str
    quote: str
    locator: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Evidence":
        return cls(
            field=str(value.get("field", "")),
            quote=str(value.get("quote", "")),
            locator=str(value.get("locator", "")),
        )


@dataclass(frozen=True)
class JobPosting:
    posting_id: str
    source_id: str
    source_name: str
    collected_at: str
    title: str
    region: str
    role_category: str
    raw_text: str
    salary: Salary
    required_skills: tuple[str, ...] = field(default_factory=tuple)
    benefits: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    review_status: str = "pending"
    synthetic: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "JobPosting":
        return cls(
            posting_id=str(value.get("posting_id", "")),
            source_id=str(value.get("source_id", "")),
            source_name=str(value.get("source_name", "")),
            collected_at=str(value.get("collected_at", "")),
            title=str(value.get("title", "")),
            region=str(value.get("region", "")),
            role_category=str(value.get("role_category", "")),
            raw_text=str(value.get("raw_text", "")),
            salary=Salary.from_dict(value.get("salary", {})),
            required_skills=tuple(value.get("required_skills", [])),
            benefits=tuple(value.get("benefits", [])),
            evidence=tuple(Evidence.from_dict(item) for item in value.get("evidence", [])),
            review_status=str(value.get("review_status", "pending")),
            synthetic=bool(value.get("synthetic", False)),
        )
