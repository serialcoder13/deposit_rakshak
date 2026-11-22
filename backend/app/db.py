"""
db.py — SQLite engine and session factory (SQLModel).
One file is all we need for the hackathon; switch DB_URL to postgresql:// later.
"""
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Ensure the data directory exists
Path("data/photos").mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
    echo=False,
)


def create_db_and_tables() -> None:
    """Create all tables (called once at startup)."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency: yields a database session."""
    with Session(engine) as session:
        yield session
