"""Database models and repository helpers for JobPosting."""

from __future__ import annotations

import json
from typing import Any
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from src.db.database import Base
from src.domain.models import JobPosting, Salary, Evidence


class JobPostingRecord(Base):
    __tablename__ = "job_postings"

    posting_id = Column(String(100), primary_key=True, index=True)
    source_id = Column(String(50), index=True)
    source_name = Column(String(100))
    source_record_id = Column(String(100), index=True)
    source_url = Column(Text)
    title = Column(String(300), nullable=False, index=True)
    company_name = Column(String(200), index=True)
    region = Column(String(100), index=True)
    region_raw = Column(String(200))
    role_category = Column(String(100), index=True)
    experience = Column(String(100))
    employment_type = Column(String(50))
    recruitment_status = Column(String(50), default="active")
    
    # Salary fields
    salary_raw = Column(String(200))
    salary_status = Column(String(50))
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_unit = Column(String(50), nullable=True)

    # JSON stored fields
    required_skills_json = Column(Text, default="[]")
    benefits_json = Column(Text, default="[]")
    evidence_json = Column(Text, default="[]")
    raw_text = Column(Text)

    posted_at = Column(String(50))
    expires_at = Column(String(50))
    collected_at = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_domain(self) -> JobPosting:
        skills = tuple(json.loads(self.required_skills_json or "[]"))
        benefits = tuple(json.loads(self.benefits_json or "[]"))
        raw_evidence = json.loads(self.evidence_json or "[]")
        evidence = tuple(Evidence.from_dict(item) for item in raw_evidence)
        salary = Salary(
            raw=self.salary_raw or "",
            status=self.salary_status or "not_stated",
            minimum=self.salary_min,
            maximum=self.salary_max,
            unit=self.salary_unit,
        )
        return JobPosting(
            posting_id=self.posting_id,
            source_id=self.source_id,
            source_name=self.source_name,
            source_record_id=self.source_record_id or "",
            source_url=self.source_url or "",
            title=self.title,
            company_name=self.company_name or "",
            region=self.region,
            region_raw=self.region_raw or "",
            role_category=self.role_category,
            role_raw=self.role_category,
            experience=self.experience or "",
            employment_type=self.employment_type or "",
            recruitment_status=self.recruitment_status or "active",
            raw_text=self.raw_text or "",
            salary=salary,
            required_skills=skills,
            benefits=benefits,
            evidence=evidence,
            posted_at=self.posted_at or "",
            expires_at=self.expires_at or "",
            collected_at=self.collected_at or "",
        )

    @classmethod
    def from_domain(cls, posting: JobPosting) -> "JobPostingRecord":
        return cls(
            posting_id=posting.posting_id,
            source_id=posting.source_id,
            source_name=posting.source_name,
            source_record_id=posting.source_record_id,
            source_url=posting.source_url,
            title=posting.title,
            company_name=posting.company_name,
            region=posting.region,
            region_raw=posting.region_raw,
            role_category=posting.role_category,
            experience=posting.experience,
            employment_type=posting.employment_type,
            recruitment_status=posting.recruitment_status,
            salary_raw=posting.salary.raw,
            salary_status=posting.salary.status,
            salary_min=posting.salary.minimum,
            salary_max=posting.salary.maximum,
            salary_unit=posting.salary.unit,
            required_skills_json=json.dumps(list(posting.required_skills), ensure_ascii=False),
            benefits_json=json.dumps(list(posting.benefits), ensure_ascii=False),
            evidence_json=json.dumps(
                [{"field": e.field, "quote": e.quote, "locator": e.locator} for e in posting.evidence],
                ensure_ascii=False,
            ),
            raw_text=posting.raw_text,
            posted_at=posting.posted_at,
            expires_at=posting.expires_at,
            collected_at=posting.collected_at,
        )
