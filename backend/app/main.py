"""Punto de entrada de la API FastAPI del agente RAG.

Registra los routers (health, documents, query, sessions) y, en el arranque, hace un UPSERT
idempotente del usuario de desarrollo (`settings.dev_user_id`) para que las claves foráneas no
fallen en el MVP (identidad por header `X-User-Id`). Ver docs/PLAN.md y docs/DECISIONES.md.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import settings
from app.routers import documents, health, query, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la app: al arrancar, asegura el usuario de desarrollo.

    El seed es idempotente (`ON CONFLICT DO NOTHING`): si la BD aún no tiene la tabla `users`
    (migraciones sin correr), no se bloquea el arranque, solo se registra el aviso.
    """
    try:
        await db.seed_dev_user()
    except Exception as exc:  # noqa: BLE001 - el arranque no debe caer por el seed
        import logging

        logging.getLogger("uvicorn.error").warning(
            "No se pudo sembrar el usuario de desarrollo (¿migraciones pendientes?): %s", exc
        )
    yield


app = FastAPI(
    title="Agente RAG sobre documentos",
    description="Explica un PDF citando el punto exacto. Proyecto antecedente para dominar RAG.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(sessions.router)


@app.get("/")
async def root():
    return {"name": "agente-rag", "version": app.version, "docs": "/docs"}
