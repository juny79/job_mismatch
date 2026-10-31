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
from src.retrieval.search import search, summary


def _posting_result(posting: Any) -> dict[str, Any]:
    return {
        "posting_id": posting.posting_id,
        "title": posting.title,
        "region": posting.region,
        "role_category": posting.role_category,
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
            self._send(405, b'{"error":"method not allowed"}', "application/json; charset=utf-8")

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
