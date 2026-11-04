"""Vercel Serverless entrypoint powered by FastAPI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Vercel sends requests to /api/index.py or strips prefix; docs_url enabled for inspection
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
        from src.db.models import JobPostingRecord
        records = db.query(JobPostingRecord).all()
        if records:
            return [r.to_domain() for r in records]
    except Exception as err:
        print(f"DB query error: {err}")

    # Fallback to demo JSONL
    try:
        from src.ingestion.jsonl import load_jsonl
        demo_path = Path(__file__).resolve().parent.parent / "data" / "demo_jobs.jsonl"
        if demo_path.exists():
            postings, _ = load_jsonl(demo_path, allow_synthetic=True)
            return postings
    except Exception as err:
        print(f"JSONL fallback error: {err}")

    return []


# Bind both root and sub-paths to guarantee matching regardless of Vercel path rewrites
@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
def index_page():
    return HTMLResponse(content=_read_index_html())


@app.get("/health")
@app.get("/api/health")
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


@app.get("/search")
@app.get("/api/search")
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
        return payload
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
        return payload
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    finally:
        db.close()


@app.post("/sync")
@app.post("/api/sync")
def trigger_sync(secret: str = Query("", description="Sync protection secret")):
    expected_secret = os.environ.get("SYNC_SECRET", "")
    if expected_secret and secret != expected_secret:
        return JSONResponse(status_code=403, content={"error": "Unauthorized sync secret"})

    api_key = os.environ.get("WORK24_API_KEY", "").strip()
    if not api_key:
        return JSONResponse(status_code=400, content={"error": "WORK24_API_KEY not configured"})

    from src.ingestion.sync_work24 import sync_from_work24
    synced = sync_from_work24(api_key=api_key, pages=1, display=20)
    return {"status": "success", "synced_count": synced}
