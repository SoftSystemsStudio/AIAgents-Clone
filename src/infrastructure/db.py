from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

from src.config.settings import settings

# Fallback to a local sqlite file when DATABASE_URL is not configured to
# allow running lightweight dev workflows without Postgres.
DATABASE_URL = settings.DATABASE_URL or "sqlite:///./dev.db"

engine = create_engine(str(DATABASE_URL), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db() -> Generator:
    """Yield a SQLAlchemy session (blocking). Use within `asyncio.to_thread` or
    background threads when called from async contexts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
