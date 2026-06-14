"""Endpoint de salud: verifica que la API y la base de datos respondan."""

from fastapi import APIRouter

from app import db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    try:
        await db.ping()
        db_status = "ok"
    except Exception:  # noqa: BLE001 - queremos reportar cualquier fallo de conexión
        db_status = "down"
    status = "ok" if db_status == "ok" else "degraded"
    return {"status": status, "db": db_status}
