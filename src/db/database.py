"""Database connection and session handling.
Supports PostgreSQL (Vercel Postgres/Supabase/Neon) and SQLite fallback for local development.
"""

from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = (
    os.environ.get("DATABASE_URL", "").strip()
    or os.environ.get("POSTGRES_URL", "").strip()
    or os.environ.get("POSTGRES_PRISMA_URL", "").strip()
)

if not DATABASE_URL:
    # Local fallback to sqlite in /tmp on serverless or local data dir
    if os.environ.get("VERCEL"):
        DATABASE_URL = "sqlite:////tmp/jobs.db"
    else:
        local_db_path = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"
        local_db_path.parent.mkdir(parents=True, exist_ok=True)
        DATABASE_URL = f"sqlite:///{local_db_path}"

# Handle Postgres protocol prefix for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Try psycopg2 first; fallback to pg8000 pure python driver if psycopg2 binary fails in lambda
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    )
except Exception:
    if DATABASE_URL.startswith("postgresql://"):
        pg8000_url = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)
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
