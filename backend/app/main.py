"""Punto de entrada de la API FastAPI del agente RAG.

V0: solo /health (verifica la BD). Los routers de documentos y consulta están como stubs
y se implementan en V1. Ver docs/PLAN.md.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import documents, health, query

app = FastAPI(
    title="Agente RAG sobre documentos",
    description="Explica un PDF citando el punto exacto. Proyecto antecedente para dominar RAG.",
    version="0.1.0",
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


@app.get("/")
async def root():
    return {"name": "agente-rag", "version": app.version, "docs": "/docs"}
