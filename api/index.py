"""Vercel Serverless entrypoint powered by FastAPI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.db.database import get_db, init_db
from src.db.models import JobPostingRecord
from src.retrieval.recommend import recommend
from src.retrieval.search import search, summary
from src.retrieval.hybrid import hybrid_search

# Initialize database tables
init_db()

app = FastAPI(title="Job Mismatch Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "src" / "app" / "templates"


def _to_posting_result(posting: Any) -> dict[str, Any]:
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
    }


def _get_active_postings_from_db(db: Session):
    records = db.query(JobPostingRecord).all()
    return [r.to_domain() for r in records]


@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Job Mismatch Analyzer API</h1>")


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    count = db.query(JobPostingRecord).count()
    return {
        "status": "ok",
        "database": "connected",
        "job_count": count,
    }


@app.get("/api/search")
def search_jobs(
    q: str = Query("", description="Search keyword"),
    mode: str = Query("hybrid", description="lexical, graph, or hybrid"),
    db: Session = Depends(get_db),
):
    postings = _get_active_postings_from_db(db)
    if not postings:
        return {"query": q, "mode": mode, "total": 0, "results": []}

    if mode == "hybrid":
        results = hybrid_search(q, postings)
    else:
        results = search(q, postings)

    formatted = [_to_posting_result(p) for p in results]
    return {
        "query": q,
        "mode": mode,
        "total": len(formatted),
        "results": formatted,
    }


@app.post("/api/recommend")
async def recommend_jobs(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    postings = _get_active_postings_from_db(db)

    results = recommend(payload, postings)
    return results


@app.post("/api/sync")
def trigger_sync(
    secret: str = Query("", description="Sync protection secret"),
    db: Session = Depends(get_db),
):
    expected_secret = os.environ.get("SYNC_SECRET", "")
    if expected_secret and secret != expected_secret:
        return JSONResponse(status_code=403, content={"error": "Unauthorized sync secret"})

    api_key = os.environ.get("WORK24_API_KEY", "").strip()
    if not api_key:
        return JSONResponse(status_code=400, content={"error": "WORK24_API_KEY not configured"})

    from src.ingestion.sync_work24 import sync_from_work24
    synced = sync_from_work24(api_key=api_key, pages=1, display=20)
    return {"status": "success", "synced_count": synced}
