"""Shared SQLAlchemy wiring for API and admin scripts."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from urban_lens.core.settings import AppConfig


def _to_sqlalchemy_dsn(raw_dsn: str) -> str:
    return raw_dsn.replace("postgresql://", "postgresql+psycopg://", 1)


_config = AppConfig.from_env()
engine = create_engine(_to_sqlalchemy_dsn(_config.postgres_dsn))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
