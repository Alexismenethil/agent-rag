"""Dependencias compartidas de FastAPI."""

from fastapi import Header

from app.config import settings


async def get_current_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Identidad del usuario en el MVP (V1-V3).

    No hay login real todavía: la identidad viaja en el header `X-User-Id`. Si no se envía,
    se usa el usuario de desarrollo (`DEV_USER_ID`). El login real llega en V4 y reemplaza esto.
    """
    return x_user_id or settings.dev_user_id
