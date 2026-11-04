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

    # Normalize to 만원/연 when annual or monthly salary is provided
    unit: str | None = None
    if "연봉" in sal_type_nm or "연봉" in raw:
        unit = "만원/연"
        # Work24 minSal for 연봉 is often in 만원 (e.g. 3500) or 원 (35000000)
        if min_val is not None and min_val >= 1000000:
            min_val = min_val // 10000
        if max_val is not None and max_val >= 1000000:
            max_val = max_val // 10000
    elif "월급" in sal_type_nm or "월급" in raw:
        unit = "만원/연"
        # Convert monthly salary to approximate annual 만원/연 (x12) for comparability
        if min_val is not None:
            if min_val >= 100000:
                min_val = (min_val // 10000) * 12
            else:
                min_val = min_val * 12
        if max_val is not None:
            if max_val >= 100000:
                max_val = (max_val // 10000) * 12
            else:
                max_val = max_val * 12
    elif "시급" in sal_type_nm or "시급" in raw:
        unit = "원/시"

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
        "Python", "PyTorch", "TensorFlow", "SQL", "JavaScript", "TypeScript",
        "Java", "C++", "C#", "React", "Vue", "Node.js", "Spring", "Django",
        "FastAPI", "MySQL", "PostgreSQL", "Docker", "Kubernetes", "Linux",
        "AWS", "Azure", "GCP", "ROS2", "Git", "엑셀", "Excel", "데이터 분석",
        "AI", "머신러닝", "딥러닝", "CAD", "AutoCAD", "SolidWorks", "CATIA",
        "PLC", "CNC", "MCT", "품질관리", "생산관리", "안전관리", "용접", "지게차",
        "전기기사", "산업안전기사", "회계", "ERP",
        "생산", "제조", "가공", "조립", "설비", "기계", "전기", "전자", "공무",
        "물류", "자재", "구매", "영업", "사무", "경리", "총무", "인사", "회계",
        "운전", "배송", "납품", "포장", "검사", "품질", "연구", "개발", "설계",
        "간호", "요양", "조리", "상담", "고객", "마케팅", "디자인", "시공", "건축", "토목"
    ]
    found = []
    text_lower = text.lower()
    for skill in common_skills:
        pattern = r"(?i)(?:\b|_)" + re.escape(skill) + r"(?:\b|_)"
        if re.search(pattern, text) or skill.lower() in text_lower:
            if skill not in found:
                found.append(skill)
    return tuple(found)


def _extract_benefits_from_text(text: str) -> tuple[str, ...]:
    common_benefits = [
        "기숙사", "통근버스", "식사제공", "중식제공", "유연근무", "재택근무",
        "자녀학자금", "건강검진", "퇴직연금", "상여금", "인센티브", "차량유지비",
        "교육비지원", "자기계발", "주차가능", "연차수당"
    ]
    found = []
    for benefit in common_benefits:
        if benefit in text:
            found.append(benefit)
    return tuple(found)


def _normalize_date(dt_str: str, default_iso: str = "2099-12-31") -> str:
    cleaned = dt_str.strip()
    if not cleaned or "채용시" in cleaned or "상시" in cleaned:
        return default_iso
    # Handle YYYYMMDD or YY-MM-DD or YYYY-MM-DD
    digits = re.sub(r"[^0-9]", "", cleaned)
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    elif len(digits) == 6:
        return f"20{digits[:2]}-{digits[2:4]}-{digits[4:6]}"
    # Validate ISO
    try:
        datetime.date.fromisoformat(cleaned[:10])
        return cleaned[:10]
    except ValueError:
        return default_iso


def work24_to_job_posting(item: dict[str, str], collected_at: str | None = None) -> JobPosting:
    """Transforms a single raw item from Work24Client into a verified JobPosting."""
    now_iso = collected_at or datetime.date.today().isoformat()
    auth_no = item.get("wantedAuthNo", "").strip()
    title = item.get("title", "").strip()
    company = item.get("company", "").strip()
    region_raw = item.get("region", "").strip()
    basic_addr = item.get("basicAddr", "").strip()
    detail_addr = item.get("detailAddr", "").strip()
    career = item.get("career", "").strip() or "경력무관"
    reg_dt = _normalize_date(item.get("regDt", ""), default_iso=now_iso)
    close_dt_raw = item.get("closeDt", "").strip()
    close_dt = _normalize_date(close_dt_raw, default_iso="2099-12-31")
    url = item.get("wantedInfoUrl", "").strip() or item.get("wantedMobileInfoUrl", "").strip()
    emp_tp = item.get("empTpCd", "").strip() or "정규직"
    holiday_tp = item.get("holidayTpNm", "").strip()
    ind_tp = item.get("indTpNm", "").strip()
    jobs_cd = item.get("jobsCd", "").strip()
    min_edu = item.get("minEdubg", "").strip()

    # Region normalization (Bu-Ul-Gyeong detailed retention)
    region = region_raw or basic_addr
    if "부산" in region_raw or "부산" in basic_addr:
        region = f"부산 ({region_raw})" if region_raw and "부산" not in region_raw else (region_raw or "부산")
    elif "울산" in region_raw or "울산" in basic_addr:
        region = f"울산 ({region_raw})" if region_raw and "울산" not in region_raw else (region_raw or "울산")
    elif "경남" in region_raw or "경상남도" in basic_addr or "창원" in region_raw or "김해" in region_raw or "양산" in region_raw or "거제" in region_raw or "진주" in region_raw:
        region = f"경남 {region_raw}" if region_raw and "경남" not in region_raw and "경상남도" not in region_raw else (region_raw or "경남")

    role_category = f"{ind_tp} ({title})" if ind_tp else (title or jobs_cd or "일반/제조/IT")
    work_mode = holiday_tp or "주5일(상근)"

    salary = _parse_salary(
        sal_type_nm=item.get("salTpNm", ""),
        sal_text=item.get("sal", ""),
        min_sal_text=item.get("minSal", ""),
        max_sal_text=item.get("maxSal", ""),
    )

    full_text = " ".join(filter(None, [title, company, ind_tp, region_raw, basic_addr, detail_addr, career, min_edu, holiday_tp, salary.raw]))
    skills = _extract_skills_from_text(full_text)
    benefits = _extract_benefits_from_text(full_text)

    evidences: list[Evidence] = [
        Evidence(field="recruitment_status", quote=f"모집 중 (마감: {close_dt_raw or '상시'})", locator="Work24:closeDt"),
        Evidence(field="region", quote=f"{region} ({basic_addr or region_raw})", locator="Work24:region"),
        Evidence(field="role_category", quote=f"업종/직무: {role_category} — {title}", locator="Work24:indTpNm"),
    ]
    if career:
        evidences.append(Evidence(field="experience", quote=f"요구 경력: {career} / 학력: {min_edu or '무관'}", locator="Work24:career"))
    if salary.raw:
        evidences.append(Evidence(field="salary", quote=salary.raw, locator="Work24:sal"))
    if emp_tp:
        evidences.append(Evidence(field="employment_type", quote=f"고용형태코드/구분: {emp_tp}", locator="Work24:empTpCd"))
    if work_mode:
        evidences.append(Evidence(field="work_mode", quote=f"근무형태: {work_mode}", locator="Work24:holidayTpNm"))
    if skills:
        evidences.append(Evidence(field="required_skills", quote=f"공고문 기술 키워드 확인: {', '.join(skills)} ({title})", locator="Work24:title"))
    if benefits:
        evidences.append(Evidence(field="benefits", quote=f"복리후생 확인: {', '.join(benefits)}", locator="Work24:title"))

    posting_id = f"WORK24-{auth_no}" if auth_no else f"WORK24-TEMP-{abs(hash(title))}"

    return JobPosting(
        posting_id=posting_id,
        source_id="work24",
        source_name="고용24 (Work24 OpenAPI)",
        source_record_id=auth_no,
        source_url=url,
        collected_at=now_iso,
        posted_at=reg_dt,
        expires_at=close_dt,
        updated_at=reg_dt,
        title=f"[{company}] {title}" if company and company not in title else title,
        company_name=company,
        region=region,
        region_raw=region_raw,
        role_category=role_category,
        role_raw=jobs_cd,
        experience=career,
        employment_type=emp_tp,
        work_mode=work_mode,
        recruitment_status="active",
        raw_text=full_text,
        salary=salary,
        required_skills=skills,
        benefits=benefits,
        evidence=tuple(evidences),
        review_status="approved",
        synthetic=False,
    )
