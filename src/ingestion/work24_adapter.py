"""Adapter to convert Work24 XML dictionary items into standard JobPosting models."""

from __future__ import annotations

import datetime
import re
from typing import Any

from src.domain.models import Evidence, JobPosting, Salary


def _parse_salary(sal_type_nm: str, sal_text: str, min_sal_text: str, max_sal_text: str) -> Salary:
    raw = f"{sal_type_nm} {sal_text}".strip()
    if not raw:
        return Salary(raw="", status="not_stated")

    min_val: int | None = None
    max_val: int | None = None

    if min_sal_text and min_sal_text.isdigit():
        min_val = int(min_sal_text)
    if max_sal_text and max_sal_text.isdigit():
        max_val = int(max_sal_text)

    # Unit determination
    unit = "KRW"
    if "연봉" in sal_type_nm:
        unit = "KRW_YEAR"
    elif "월급" in sal_type_nm:
        unit = "KRW_MONTH"
    elif "시급" in sal_type_nm:
        unit = "KRW_HOUR"

    status = "reported" if (min_val is not None or max_val is not None) else "not_stated"
    return Salary(
        raw=raw,
        status=status,
        minimum=min_val,
        maximum=max_val,
        unit=unit,
    )


def _extract_skills_from_text(text: str) -> tuple[str, ...]:
    common_skills = [
        "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "React", "Vue",
        "Node.js", "Spring", "Django", "FastAPI", "SQL", "MySQL", "PostgreSQL",
        "Docker", "Kubernetes", "AWS", "Git", "Linux", "AI", "머신러닝", "딥러닝",
        "CAD", "PLC", "CNC", "품질관리", "생산관리", "용접", "지게차", "전기기사"
    ]
    found = []
    text_lower = text.lower()
    for skill in common_skills:
        # Match word boundaries or simple search for Korean
        pattern = r"(?i)(?:\b|_)" + re.escape(skill) + r"(?:\b|_)"
        if re.search(pattern, text) or skill.lower() in text_lower:
            if skill not in found:
                found.append(skill)
    return tuple(found)


def work24_to_job_posting(item: dict[str, str], collected_at: str | None = None) -> JobPosting:
    """Transforms a single raw item from Work24Client into a JobPosting."""
    now_iso = collected_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    auth_no = item.get("wantedAuthNo", "").strip()
    title = item.get("title", "").strip()
    company = item.get("company", "").strip()
    region_raw = item.get("region", "").strip()
    basic_addr = item.get("basicAddr", "").strip()
    career = item.get("career", "").strip()
    reg_dt = item.get("regDt", "").strip()
    close_dt = item.get("closeDt", "").strip()
    url = item.get("wantedInfoUrl", "").strip()
    emp_tp = item.get("empTpCd", "").strip()
    jobs_cd = item.get("jobsCd", "").strip()

    # Region normalization (Focusing on Bu-Ul-Gyeong & general)
    region = region_raw
    if "부산" in region_raw or "부산" in basic_addr:
        region = "부산"
    elif "울산" in region_raw or "울산" in basic_addr:
        region = "울산"
    elif "경남" in region_raw or "경상남도" in basic_addr:
        region = "경남"

    salary = _parse_salary(
        sal_type_nm=item.get("salTpNm", ""),
        sal_text=item.get("sal", ""),
        min_sal_text=item.get("minSal", ""),
        max_sal_text=item.get("maxSal", ""),
    )

    full_text = f"{title} {company} {region_raw} {basic_addr} {career}"
    skills = _extract_skills_from_text(full_text)

    evidences: list[Evidence] = []
    if career:
        evidences.append(Evidence(field="experience", quote=career, locator="career"))
    if salary.raw:
        evidences.append(Evidence(field="salary", quote=salary.raw, locator="sal"))
    if region_raw:
        evidences.append(Evidence(field="region", quote=region_raw, locator="region"))

    posting_id = f"work24_{auth_no}" if auth_no else f"work24_temp_{hash(title)}"

    return JobPosting(
        posting_id=posting_id,
        source_id="work24",
        source_name="고용24",
        source_record_id=auth_no,
        source_url=url,
        collected_at=now_iso,
        posted_at=reg_dt,
        expires_at=close_dt,
        updated_at=item.get("smodifyDtm", reg_dt),
        title=title,
        company_name=company,
        region=region,
        region_raw=region_raw,
        role_category=jobs_cd or "기타",
        role_raw=jobs_cd,
        experience=career,
        employment_type=emp_tp,
        recruitment_status="active",
        raw_text=full_text,
        salary=salary,
        required_skills=skills,
        evidence=tuple(evidences),
    )
