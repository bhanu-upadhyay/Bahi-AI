from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_name(target=None) -> str:
    """Extracts the resolved database name from a Session, Engine, or the default engine."""
    if target is not None:
        if hasattr(target, "get_bind"):
            bind = target.get_bind()
        else:
            bind = target
        if bind is not None and hasattr(bind, "url") and bind.url:
            return (bind.url.database or "").strip()
    if engine is not None and hasattr(engine, "url") and engine.url:
        return (engine.url.database or "").strip()
    return ""
