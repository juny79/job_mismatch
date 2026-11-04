"""Vercel Serverless entrypoint powered by FastAPI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

app = FastAPI(title="Job Mismatch Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "src" / "app" / "templates"


def _read_index_html() -> str:
    html_file = TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    pub_file = Path(__file__).resolve().parent.parent / "public" / "index.html"
    if pub_file.exists():
        return pub_file.read_text(encoding="utf-8")
    return "<h1>Job Mismatch Analyzer API</h1>"


def _get_active_postings_from_db(db: Session):
    try:
        from src.db.database import init_db
        from src.db.models import JobPostingRecord
        init_db()

        # Remove any legacy synthetic demo records if present
        db.query(JobPostingRecord).filter(JobPostingRecord.source_id == "DEMO-SYNTHETIC").delete()
        db.commit()

        # DB has < 100 real jobs: Automatically fetch 300 Bu-Ul-Gyeong postings from Work24 API
        if len(records) < 100:
            api_key = os.environ.get("WORK24_API_KEY", "").strip()
            if api_key:
                from src.ingestion.sync_work24 import sync_from_work24
                sync_from_work24(api_key=api_key, start_page=1, pages=1, display=100)
                records = db.query(JobPostingRecord).all()

        if records:
            return [r.to_domain() for r in records]
    except Exception as err:
        print(f"DB/Work24 auto-sync error: {err}")

    return []


def _enrich_with_graph_stats(payload: dict[str, Any], postings: list[Any]) -> dict[str, Any]:
    from src.retrieval.graphrag import build_job_graph, graph_summary
    graph = build_job_graph(postings)
    g_sum = graph_summary(graph)
    kind_counts: dict[str, int] = {}
    for node in graph.nodes.values():
        kind_counts[node.kind] = kind_counts.get(node.kind, 0) + 1
    rel_counts: dict[str, int] = {}
    for edge in graph.edges:
        rel_counts[edge.relationship] = rel_counts.get(edge.relationship, 0) + 1

    # Sample top graph edges for visual inspection
    sample_triples = []
    for edge in graph.edges[:24]:
        s_node = graph.nodes.get(edge.source_id)
        t_node = graph.nodes.get(edge.target_id)
        if s_node and t_node and edge.relationship != "FROM_SOURCE":
            sample_triples.append({
                "source": s_node.label,
                "source_kind": s_node.kind,
                "relationship": edge.relationship,
                "target": t_node.label,
                "target_kind": t_node.kind,
            })

    payload["graph_stats"] = {
        "node_count": g_sum["node_count"],
        "edge_count": g_sum["relationship_count"],
        "node_kinds": kind_counts,
        "relationship_kinds": rel_counts,
        "sample_triples": sample_triples[:12],
    }
    return payload


@app.api_route("/health", methods=["GET", "POST"])
@app.api_route("/api/health", methods=["GET", "POST"])
def health_check():
    db_status = "unknown"
    job_count = 0
    err_msg = None
    try:
        from src.db.database import SessionLocal
        from src.db.models import JobPostingRecord
        db = SessionLocal()
        job_count = db.query(JobPostingRecord).count()
        db_status = "connected"
        db.close()
    except Exception as e:
        db_status = "error"
        err_msg = str(e)

    return {
        "status": "ok",
        "database": db_status,
        "job_count": job_count,
        "db_error": err_msg,
    }


@app.api_route("/search", methods=["GET", "POST"])
@app.api_route("/api/search", methods=["GET", "POST"])
def search_jobs(
    q: str = Query("", description="Search keyword"),
    region: str = Query("", description="Region filter"),
    mode: str = Query("hybrid", description="lexical, graph, or hybrid"),
):
    from src.db.database import SessionLocal
    from src.app.web import build_search_payload

    db = SessionLocal()
    try:
        postings = _get_active_postings_from_db(db)
        payload = build_search_payload(
            postings=postings,
            rejected=[],
            query=q,
            region=region,
            graph=mode,
        )
        return _enrich_with_graph_stats(payload, postings)
    finally:
        db.close()


@app.post("/recommend")
@app.post("/api/recommend")
async def recommend_jobs(request: Request):
    from src.db.database import SessionLocal
    from src.app.web import build_recommendation_payload

    preferences = await request.json()
    db = SessionLocal()
    try:
        postings = _get_active_postings_from_db(db)
        payload = build_recommendation_payload(postings, preferences)
        return _enrich_with_graph_stats(payload, postings)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    finally:
        db.close()


@app.api_route("/sync", methods=["GET", "POST"])
@app.api_route("/api/sync", methods=["GET", "POST"])
def trigger_sync(
    page: int = Query(0, description="Page to fetch (0 = auto next page)"),
    secret: str = Query("", description="Sync protection secret"),
):
    expected_secret = os.environ.get("SYNC_SECRET", "")
    if expected_secret and secret != expected_secret:
        return JSONResponse(status_code=403, content={"error": "Unauthorized sync secret"})

    api_key = os.environ.get("WORK24_API_KEY", "").strip()
    if not api_key:
        return JSONResponse(status_code=400, content={"error": "WORK24_API_KEY 환경 변수가 설정되지 않았습니다."})

    # Determine next page automatically based on current DB count (each page across 3 regions = ~300 jobs)
    target_page = page
    if target_page <= 0:
        try:
            from src.db.database import SessionLocal
            from src.db.models import JobPostingRecord
            db = SessionLocal()
            current_count = db.query(JobPostingRecord).count()
            db.close()
            target_page = (current_count // 250) + 1
        except Exception:
            target_page = 1

    from src.ingestion.sync_work24 import sync_from_work24
    result = sync_from_work24(api_key=api_key, start_page=target_page, pages=1, display=100)
    return {
        "status": "success",
        "page_fetched": target_page,
        "synced_count": result.get("saved", 0),
        "total_in_db": result.get("total_in_db", 0),
        "errors": result.get("errors", []),
    }


@app.api_route("/{full_path:path}", methods=["GET", "POST"])
def catch_all(request: Request, full_path: str):
    if "api" in full_path or "health" in full_path:
        return {"path_received": full_path, "url": str(request.url), "message": "API endpoint reached via catch_all"}
    return HTMLResponse(content=_read_index_html())
