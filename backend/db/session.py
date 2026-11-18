"""Database session and connection management for PULSE.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env from PULSE root directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=REPO_ROOT / ".env")


def get_database_url() -> str:
    """Safely retrieves and normalizes DATABASE_URL from environment."""
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_URL is not set in environment or .env file.")

    # Normalize PostgreSQL driver to pure-Python psycopg if no driver explicitly specified
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    return raw_url


DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

