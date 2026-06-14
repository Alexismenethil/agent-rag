"""Conexión async a PostgreSQL (asyncpg) vía SQLAlchemy 2.0.

Expone:
- `engine` / `SessionLocal`: motor y fábrica de sesiones async.
- `get_session`: dependencia FastAPI (una sesión por request).
- `Base`: clase declarativa base de la que heredan todos los modelos ORM (ver `app.models`).
- `ping`: chequeo de conexión usado por `/health`.
- `seed_dev_user`: UPSERT idempotente del usuario de desarrollo (para que las FK no fallen en MVP).
"""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Clase declarativa base de SQLAlchemy 2.0 para todos los modelos ORM."""


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: una sesión async por request."""
    async with SessionLocal() as session:
        yield session


async def ping() -> bool:
    """Verifica la conexión a la BD (usado por /health)."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def seed_dev_user() -> None:
    """UPSERT idempotente del usuario de desarrollo (`settings.dev_user_id`).

    En el MVP (V1-V3) la identidad viaja por el header `X-User-Id` y por defecto se usa este
    usuario fijo. Lo insertamos al arrancar para que las claves foráneas (documents.owner_id,
    conversations.user_id, …) no fallen. Es idempotente: `ON CONFLICT DO NOTHING`.
    """
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO users (id, email, nombre)
                VALUES (:id, :email, :nombre)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": settings.dev_user_id,
                "email": "dev@local",
                "nombre": "Usuario de desarrollo",
            },
        )
