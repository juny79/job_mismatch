"""Deterministic, evidence-gated recommendation preview (not employment prediction)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from src.domain.models import Evidence, JobPosting
from src.retrieval.search import searchable


@dataclass(frozen=True)
class RecommendationHit:
    posting: JobPosting
    score: float | None
    matched_required_skills: tuple[str, ...]
    matched_preferred_skills: tuple[str, ...]
    unmatched_preferred_skills: tuple[str, ...]
    matched_preferred_benefits: tuple[str, ...]
    unmatched_preferred_benefits: tuple[str, ...]
    conditions: tuple[dict[str, object], ...]
    evidence: tuple[Evidence, ...]
    matched_profile_skills: tuple[str, ...]
    unlisted_job_skills: tuple[str, ...]
    profile_skill_coverage: float | None


def _terms(values: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(values, str):
        values = values.split(",")
    return tuple(dict.fromkeys(value.strip().casefold() for value in values if value.strip()))


def _field_evidence(posting: JobPosting, field: str) -> tuple[Evidence, ...]:
    return tuple(item for item in posting.evidence if item.field == field)


def _has_term_evidence(posting: JobPosting, field: str, term: str) -> bool:
    return any(term in item.quote.casefold() for item in _field_evidence(posting, field))


def recommend(
    postings: list[JobPosting],
    *,
    region: str = "",
    region_mode: str = "required",
    role_category: str = "",
    role_mode: str = "required",
    required_skills: Iterable[str] = (),
    preferred_skills: Iterable[str] = (),
    preferred_benefits: Iterable[str] = (),
    candidate_skills: Iterable[str] = (),
    salary_minimum: int | None = None,
    salary_unit: str = "만원/연",
    salary_required: bool = False,
    employment_type: str = "",
    employment_type_required: bool = False,
    work_mode: str = "",
    work_mode_required: bool = False,
    experience: str = "",
    experience_required: bool = False,
    limit: int = 10,
) -> list[RecommendationHit]:
    """Apply hard requirements first, rank remaining candidates by preferences.

    Only approved, explicitly active and unexpired postings can be recommended.
    Missing evidence never counts as a match. An empty condition set abstains.
    """
    required = _terms(required_skills)
    preferred_skill_terms = _terms(preferred_skills)
    preferred_benefit_terms = _terms(preferred_benefits)
    candidate_skill_terms = _terms(candidate_skills)
    region, role_category = region.strip(), role_category.strip()
    employment_type, work_mode, experience = (
        employment_type.strip(), work_mode.strip(), experience.strip()
    )
    if region_mode not in {"required", "preferred", "ignore"}:
        raise ValueError("region_mode must be required, preferred, or ignore")
    if role_mode not in {"required", "preferred", "ignore"}:
        raise ValueError("role_mode must be required, preferred, or ignore")
    if salary_minimum is not None and (isinstance(salary_minimum, bool) or salary_minimum < 0):
        raise ValueError("salary_minimum must be a non-negative integer")

    has_conditions = bool(
        (region and region_mode != "ignore") or (role_category and role_mode != "ignore")
        or required or preferred_skill_terms or preferred_benefit_terms or candidate_skill_terms
        or salary_minimum is not None or employment_type or work_mode or experience
    )
    if not has_conditions:
        return []

    hits: list[RecommendationHit] = []
    today = date.today()
    for posting in postings:
        if not searchable(posting) or posting.recruitment_status != "active":
            continue
        if not _field_evidence(posting, "recruitment_status"):
            continue
        if posting.expires_at and posting.expires_at[:10] < today.isoformat():
            continue
        if not posting.synthetic:
            # Real-source recommendations require an explicit expiry and a recent
            # ingestion/source-check timestamp; synthetic fixtures are exempt only
            # for regression demos.
            checked_at = posting.collected_at
            try:
                checked_date = datetime.fromisoformat(checked_at.replace("Z", "+00:00")).date()
                expiry_date = date.fromisoformat(posting.expires_at[:10])
            except (ValueError, TypeError):
                continue
            if not posting.expires_at or checked_date > today or (today - checked_date).days > 30 or expiry_date < today:
                continue

        checks: list[dict[str, object]] = []
        used_fields: set[str] = {"recruitment_status"}
        rejected = False

        def assess(label: str, field: str, wanted: str, actual: str, *, hard: bool) -> None:
            nonlocal rejected
            evidence = _field_evidence(posting, field)
            has_evidence = bool(evidence)
            found = wanted.casefold() in actual.casefold() if actual else False
            evidence_ok = has_evidence and _has_term_evidence(posting, field, wanted.casefold())
            status = "unknown" if not has_evidence or not actual else "match" if found and evidence_ok else "mismatch"
            checks.append({"condition": label, "requested": wanted, "status": status,
                           "required": hard, "field": field})
            if status == "match":
                used_fields.add(field)
            if hard and status != "match":
                rejected = True

        if region and region_mode != "ignore":
            assess("지역", "region", region, posting.region, hard=region_mode == "required")
        if role_category and role_mode != "ignore":
            assess("직무", "role_category", role_category, posting.role_category,
                   hard=role_mode == "required")
        supported_skills = tuple(skill for skill in posting.required_skills
                                 if _field_evidence(posting, "required_skills")
                                 and _has_term_evidence(posting, "required_skills", skill.casefold()))
        for term in required:
            assess("필수 기술", "required_skills", term,
                   ", ".join(supported_skills), hard=True)
        for term in preferred_skill_terms:
            assess("선호 기술", "required_skills", term,
                   ", ".join(supported_skills), hard=False)
        for term in preferred_benefit_terms:
            supported_benefits = tuple(benefit for benefit in posting.benefits
                                       if _has_term_evidence(posting, "benefits", benefit.casefold()))
            assess("선호 복지", "benefits", term, ", ".join(supported_benefits), hard=False)

        job_skill_matches: list[tuple[str, str]] = []
        if candidate_skill_terms:
            if supported_skills:
                used_fields.add("required_skills")
            for job_skill in supported_skills:
                candidate_match = next((candidate for candidate in candidate_skill_terms
                                        if candidate == job_skill.casefold()), None)
                if candidate_match:
                    job_skill_matches.append((job_skill, candidate_match))
            coverage = round(100 * len(job_skill_matches) / len(supported_skills), 1) if supported_skills else None
            matched_candidate_skills = tuple(dict.fromkeys(job_skill for job_skill, _ in job_skill_matches))
            matched_job_skills = {job_skill for job_skill, _ in job_skill_matches}
            unlisted_job_skills = tuple(skill for skill in supported_skills if skill not in matched_job_skills)
        else:
            coverage = None
            matched_candidate_skills = ()
            unlisted_job_skills = ()
        if salary_minimum is not None:
            evidence = _field_evidence(posting, "salary")
            known = (posting.salary.status == "reported" and posting.salary.minimum is not None
                     and bool(evidence) and posting.salary.unit == salary_unit)
            if not known:
                status = "unknown"
            elif posting.salary.minimum >= salary_minimum:
                status = "match"
            elif posting.salary.maximum is not None and posting.salary.maximum < salary_minimum:
                status = "mismatch"
            else:
                status = "unknown"
            checks.append({"condition": "급여 하한", "requested": str(salary_minimum),
                           "actual": posting.salary.minimum, "unit": posting.salary.unit,
                           "status": status, "required": salary_required, "field": "salary"})
            if status == "match":
                used_fields.add("salary")
            if salary_required and status != "match":
                rejected = True
        if employment_type:
            assess("고용 형태", "employment_type", employment_type, posting.employment_type,
                   hard=employment_type_required)
        if work_mode:
            assess("근무 방식", "work_mode", work_mode, posting.work_mode, hard=work_mode_required)
        if experience:
            assess("경력 수준", "experience", experience, posting.experience,
                   hard=experience_required)
        if rejected:
            continue

        preferred_checks = [item for item in checks if not item["required"]]
        score = round(100 * sum(item["status"] == "match" for item in preferred_checks)
                      / len(preferred_checks), 1) if preferred_checks else None
        evidence = tuple(item for item in posting.evidence if item.field in used_fields)
        matched_preferred_skills = tuple(term for term in preferred_skill_terms if any(
            item["condition"] == "선호 기술" and item["requested"] == term and item["status"] == "match"
            for item in checks))
        matched_preferred_benefits = tuple(term for term in preferred_benefit_terms if any(
            item["condition"] == "선호 복지" and item["requested"] == term and item["status"] == "match"
            for item in checks))
        matched_pref = set(matched_preferred_skills + matched_preferred_benefits)
        hits.append(RecommendationHit(
            posting=posting, score=score,
            matched_required_skills=required,
            matched_preferred_skills=matched_preferred_skills,
            unmatched_preferred_skills=tuple(t for t in preferred_skill_terms if t not in matched_pref),
            matched_preferred_benefits=matched_preferred_benefits,
            unmatched_preferred_benefits=tuple(t for t in preferred_benefit_terms if t not in matched_pref),
            conditions=tuple(checks), evidence=evidence,
            matched_profile_skills=matched_candidate_skills,
            unlisted_job_skills=unlisted_job_skills,
            profile_skill_coverage=coverage,
        ))

    hits.sort(key=lambda hit: (
        -(hit.profile_skill_coverage if hit.profile_skill_coverage is not None else -1.0),
        -(hit.score if hit.score is not None else -1.0),
        hit.posting.posting_id,
    ))
    return hits[:max(0, min(limit, 50))]
