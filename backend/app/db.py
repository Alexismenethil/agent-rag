"""Conexión async a PostgreSQL (asyncpg) vía SQLAlchemy 2.0."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: una sesión async por request."""
    async with SessionLocal() as session:
        yield session


async def ping() -> bool:
    """Verifica la conexión a la BD (usado por /health)."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
