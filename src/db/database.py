"""Database connection and session handling.
Supports PostgreSQL (Vercel Postgres/Supabase/Neon) and SQLite fallback for local development.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _sanitize_postgres_url(raw_url: str) -> str:
    """Normalize postgres:// prefix and strip query parameters unsupported by older libpq/drivers."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url.startswith("postgresql"):
        return url

    parts = urlsplit(url)
    # Keep only standard libpq parameters supported universally; drop channel_binding / pgbouncer / schema
    unsupported_keys = {"channel_binding", "pgbouncer", "schema", "sslaccept"}
    clean_query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k not in unsupported_keys
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(clean_query), parts.fragment))


DATABASE_URL = (
    os.environ.get("DATABASE_URL", "").strip()
    or os.environ.get("POSTGRES_URL", "").strip()
    or os.environ.get("POSTGRES_PRISMA_URL", "").strip()
)

if not DATABASE_URL:
    if os.environ.get("VERCEL"):
        DATABASE_URL = "sqlite:////tmp/jobs.db"
    else:
        local_db_path = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"
        local_db_path.parent.mkdir(parents=True, exist_ok=True)
        DATABASE_URL = f"sqlite:///{local_db_path}"
else:
    DATABASE_URL = _sanitize_postgres_url(DATABASE_URL)

try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    )
except Exception:
    if DATABASE_URL.startswith("postgresql://"):
        # Strip all query params for pg8000 pure-python fallback
        parts = urlsplit(DATABASE_URL)
        pg8000_url = urlunsplit(("postgresql+pg8000", parts.netloc, parts.path, "", ""))
        engine = create_engine(pg8000_url, echo=False, pool_pre_ping=True)
    else:
        raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: init_db failed: {e}")
