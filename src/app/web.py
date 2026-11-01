"""Read-only standard-library web UI for the local GraphRAG PoC."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.ingestion.jsonl import load_jsonl
from src.ingestion.quality import quality_report
from src.ingestion.source_registry import validate_source_registry
from src.retrieval.graphrag import answer_with_graph
from src.retrieval.hybrid import hybrid_search
from src.retrieval.recommend import recommend
from src.retrieval.search import search, summary


def _posting_result(posting: Any) -> dict[str, Any]:
    return {
        "posting_id": posting.posting_id,
        "title": posting.title,
        "region": posting.region,
        "role_category": posting.role_category,
        "recruitment_status": posting.recruitment_status,
        "expires_at": posting.expires_at,
        "updated_at": posting.updated_at,
        "employment_type": posting.employment_type,
        "work_mode": posting.work_mode,
        "experience": posting.experience,
        "skills": list(posting.required_skills),
        "benefits": list(posting.benefits),
        "salary": {
            "raw": posting.salary.raw,
            "status": posting.salary.status,
            "minimum": posting.salary.minimum,
            "maximum": posting.salary.maximum,
            "unit": posting.salary.unit,
        },
        "source": {
            "id": posting.source_id,
            "name": posting.source_name,
            "record_id": posting.source_record_id,
            "url": posting.source_url,
            "posted_at": posting.posted_at,
            "updated_at": posting.updated_at,
            "checked_at": posting.collected_at,
        },
        "evidence": [
            {"field": item.field, "quote": item.quote, "locator": item.locator}
            for item in posting.evidence
        ],
        "synthetic": posting.synthetic,
    }


def build_search_payload(
    postings: list[Any],
    rejected: list[dict[str, Any]],
    query: str = "",
    region: str = "",
    graph: bool | str = False,
) -> dict[str, Any]:
    """Build the JSON contract used by the UI from already gated records."""
    report = quality_report(postings, rejected)
    approved_regions = sorted({
        posting.region for posting in postings
        if posting.review_status == "approved" and posting.region
    })
    mode = "graph" if graph is True else graph if graph in {"keyword", "graph", "hybrid"} else "keyword"
    message = "검수 승인 레코드만 표시합니다."
    if mode == "graph":
        answer = answer_with_graph(postings, query, region or None)
        results = answer["results"]
        message = answer["message"]
    elif mode == "hybrid":
        results = []
        for hit in hybrid_search(postings, query, region or None):
            result = _posting_result(hit.posting)
            result.update({
                "score": round(hit.score, 3),
                "matched_terms": list(hit.matched_terms),
                "matched_fields": list(hit.matched_fields),
                "channels": list(hit.channels),
                "graph_paths": [
                    {
                        "relationship": path["relationship"],
                        "label": path["label"],
                        "matched_terms": list(path["matched_terms"]),
                        "evidence": [
                            {"field": item.field, "quote": item.quote, "locator": item.locator}
                            for item in path["evidence"]
                        ],
                    }
                    for path in hit.graph_paths
                ],
                "evidence": [
                    {"field": item.field, "quote": item.quote, "locator": item.locator}
                    for item in hit.evidence
                ],
            })
            results.append(result)
    else:
        results = [
            _posting_result(hit.posting)
            for hit in search(postings, query, region or None)
        ]
    if not results:
        message = "조건에 맞는 검수 승인 레코드가 없습니다."

    return {
        "mode": mode,
        "query": query,
        "region_filter": region or None,
        "result_count": len(results),
        "results": results,
        "message": message,
        "summary": summary(postings),
        "quality": report,
        "regions": approved_regions,
        "synthetic": any(posting.synthetic for posting in postings),
    }


def _comma_values(value: Any, field: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        values = value
    else:
        raise ValueError(f"{field} must be text or a list of text values")
    cleaned = tuple(dict.fromkeys(item.strip() for item in values if item.strip()))
    if len(cleaned) > 20 or any(len(item) > 80 for item in cleaned):
        raise ValueError(f"{field} 항목은 20개, 각 80자 이하여야 합니다.")
    return cleaned


def build_recommendation_payload(postings: list[Any], preferences: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a transient request; no profile or preference is persisted."""
    allowed = {
        "region", "region_mode", "role_category", "role_mode", "required_skills",
        "preferred_skills", "preferred_benefits", "candidate_skills", "salary_minimum", "salary_unit", "salary_required",
        "employment_type", "employment_type_required", "work_mode", "work_mode_required",
        "experience", "experience_required",
    }
    if set(preferences) - allowed:
        raise ValueError("지원하지 않는 조건 항목이 포함되어 있습니다.")
    for name, max_length in (("region", 100), ("role_category", 100),
                             ("employment_type", 80), ("work_mode", 80), ("experience", 80)):
        value = preferences.get(name, "")
        if not isinstance(value, str) or len(value) > max_length:
            raise ValueError(f"{name} 값이 올바르지 않거나 너무 깁니다.")
    salary_minimum = preferences.get("salary_minimum")
    if salary_minimum in (None, ""):
        salary_minimum = None
    else:
        if isinstance(salary_minimum, bool):
            raise ValueError("salary_minimum must be a non-negative integer")
        try:
            if isinstance(salary_minimum, float) and not salary_minimum.is_integer():
                raise ValueError
            if isinstance(salary_minimum, str) and not salary_minimum.strip().isdigit():
                raise ValueError
            salary_minimum = int(salary_minimum)
        except (TypeError, ValueError) as exc:
            raise ValueError("급여 하한은 정수로 입력해 주세요.") from exc
        if salary_minimum < 0 or salary_minimum > 10000000:
            raise ValueError("급여 하한 값이 허용 범위를 벗어났습니다.")
    for flag in ("salary_required", "employment_type_required", "work_mode_required", "experience_required"):
        if flag in preferences and not isinstance(preferences[flag], bool):
            raise ValueError(f"{flag} must be boolean")
    for name in ("region_mode", "role_mode"):
        mode_value = preferences.get(name, "required")
        if not isinstance(mode_value, str) or mode_value not in {"required", "preferred", "ignore"}:
            raise ValueError(f"{name} must be required, preferred, or ignore")
    salary_unit = preferences.get("salary_unit", "만원/연")
    if not isinstance(salary_unit, str) or salary_unit != "만원/연":
        raise ValueError("현재 데모 급여 비교 단위는 만원/연만 지원합니다.")

    hits = recommend(
        postings,
        region=preferences.get("region", ""),
        region_mode=preferences.get("region_mode", "required"),
        role_category=preferences.get("role_category", ""),
        role_mode=preferences.get("role_mode", "required"),
        required_skills=_comma_values(preferences.get("required_skills"), "required_skills"),
        preferred_skills=_comma_values(preferences.get("preferred_skills"), "preferred_skills"),
        preferred_benefits=_comma_values(preferences.get("preferred_benefits"), "preferred_benefits"),
        candidate_skills=_comma_values(preferences.get("candidate_skills"), "candidate_skills"),
        salary_minimum=salary_minimum,
        salary_unit=salary_unit,
        salary_required=preferences.get("salary_required", False),
        employment_type=preferences.get("employment_type", ""),
        employment_type_required=preferences.get("employment_type_required", False),
        work_mode=preferences.get("work_mode", ""),
        work_mode_required=preferences.get("work_mode_required", False),
        experience=preferences.get("experience", ""),
        experience_required=preferences.get("experience_required", False),
        limit=20,
    )
    has_conditions = bool(
        (preferences.get("region") and preferences.get("region_mode", "required") != "ignore")
        or (preferences.get("role_category") and preferences.get("role_mode", "required") != "ignore")
        or _comma_values(preferences.get("required_skills"), "required_skills")
        or _comma_values(preferences.get("preferred_skills"), "preferred_skills")
        or _comma_values(preferences.get("preferred_benefits"), "preferred_benefits")
        or _comma_values(preferences.get("candidate_skills"), "candidate_skills")
        or salary_minimum is not None
        or preferences.get("employment_type") or preferences.get("work_mode")
        or preferences.get("experience")
    )
    results = []
    for hit in hits:
        row = _posting_result(hit.posting)
        row.update({
            "score": hit.score,
            "score_label": "입력 조건 선호 일치도" if hit.score is not None else None,
            "conditions": list(hit.conditions),
            "matched_required_skills": list(hit.matched_required_skills),
            "matched_preferred_skills": list(hit.matched_preferred_skills),
            "unmatched_preferred_skills": list(hit.unmatched_preferred_skills),
            "matched_preferred_benefits": list(hit.matched_preferred_benefits),
            "unmatched_preferred_benefits": list(hit.unmatched_preferred_benefits),
            "matched_profile_skills": list(hit.matched_profile_skills),
            "unlisted_job_skills": list(hit.unlisted_job_skills),
            "profile_skill_coverage": hit.profile_skill_coverage,
            "evidence": [
                {"field": item.field, "quote": item.quote, "locator": item.locator}
                for item in hit.evidence
            ],
        })
        results.append(row)
    abstained = not results
    message = (
        "조건을 입력하면 추천 후보를 비교할 수 있습니다. 현재 입력 조건이 없어 추천하지 않았습니다."
        if not has_conditions else
        "필수 조건·검수·모집 상태를 확인할 수 있는 공고가 없습니다. 조건을 완화하거나 원문을 확인해 주세요."
        if abstained else
        "프로필 기준으로 확인할 후보입니다. 이력서에 적히지 않은 요건은 실제 역량 부족으로 단정하지 않습니다. 취업·채용 결과를 예측하거나 보장하지 않습니다."
    )
    return {
        "mode": "deterministic_recommendation_preview",
        "result_count": len(results), "abstained": abstained,
        "message": message, "synthetic": any(row["synthetic"] for row in results),
        "results": results,
    }


def make_handler(postings: list[Any], rejected: list[dict[str, Any]]) -> type[BaseHTTPRequestHandler]:
    class WebHandler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args: Any) -> None:
            # Queries and record identifiers are not written to access logs.
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/" or parsed.path == "/index.html":
                page = Path(__file__).with_name("templates").joinpath("index.html").read_bytes()
                self._send(200, page, "text/html; charset=utf-8")
                return
            if parsed.path != "/api/search":
                self._send(404, b'{"error":"not found"}', "application/json; charset=utf-8")
                return

            params = parse_qs(parsed.query, keep_blank_values=True)
            query = params.get("q", [""])[0]
            region = params.get("region", [""])[0]
            mode = params.get("mode", [""])[0]
            if not mode:
                mode = "graph" if params.get("graph", ["0"])[0] == "1" else "keyword"
            if len(query) > 200 or len(region) > 100:
                error_body = '{"error":"검색어 또는 지역 필터가 너무 깁니다."}'.encode("utf-8")
                self._send(400, error_body, "application/json; charset=utf-8")
                return
            payload = build_search_payload(postings, rejected, query, region, mode)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/recommend":
                self._send(404, b'{"error":"not found"}', "application/json; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 16384:
                    raise ValueError("요청 본문은 1~16384바이트여야 합니다.")
                if "application/json" not in self.headers.get("Content-Type", ""):
                    raise ValueError("Content-Type: application/json 요청만 지원합니다.")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("조건은 JSON 객체로 전달해야 합니다.")
                result = build_recommendation_payload(postings, payload)
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
                self._send(400, body, "application/json; charset=utf-8")

    return WebHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only local job evidence web demo")
    parser.add_argument("--data", default="data/demo_jobs.jsonl", help="JSONL dataset")
    parser.add_argument("--source-registry", help="Approved source registry CSV")
    parser.add_argument("--allow-synthetic", action="store_true", help="Explicitly allow synthetic demo records")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; use 0.0.0.0 only on a trusted network")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    args = parser.parse_args()

    approved_source_ids: set[str] = set()
    if args.source_registry:
        approved_source_ids, errors = validate_source_registry(args.source_registry)
        if errors:
            raise SystemExit(json.dumps({"source_registry_errors": errors}, ensure_ascii=False))
    postings, rejected = load_jsonl(
        args.data,
        approved_source_ids=approved_source_ids,
        allow_synthetic=args.allow_synthetic,
    )

    server = ThreadingHTTPServer((args.host, args.port), make_handler(postings, rejected))
    print(f"Web UI: http://{args.host}:{args.port}")
    print(f"Loaded records: {len(postings)} accepted, {len(rejected)} rejected")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
