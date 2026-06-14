"""Consulta RAG: pregunta sobre un documento y responde con citas exactas.

STUB (V0): define el contrato canónico (docs/DECISIONES.md ADR-004) con los modelos Pydantic
para que el OpenAPI ya documente la forma de la respuesta (citas con offsets/snippet). La
implementación (recuperación → grounding → localización del span de cita) llega en V1.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import get_current_user_id

router = APIRouter(tags=["query"])

Modo = Literal["estricto", "ampliado"]


class ConsultaRequest(BaseModel):
    doc_id: str
    pregunta: str
    modo: Modo = "estricto"
    session_id: str | None = None
    top_k: int = 8


class Cita(BaseModel):
    marcador: int = Field(..., description="Número [n] de la cita en la respuesta")
    chunk_id: str
    doc_id: str
    pagina: int
    seccion: str | None = None
    offset_inicio: int
    offset_fin: int
    snippet: str = Field(..., description="Fragmento textual literal del documento")
    texto_afirmacion: str = Field(..., description="Afirmación que esta cita respalda")


class ConsultaResponse(BaseModel):
    message_id: str
    session_id: str
    respuesta: str
    citas: list[Cita]
    informacion_ampliada: str | None = None
    groundedness: float
    modelo: str


@router.post("/query", response_model=ConsultaResponse)
async def consultar(req: ConsultaRequest, user_id: str = Depends(get_current_user_id)):
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "Disponible en V1 (respuesta con cita exacta). Streaming /query/stream en V2.",
    )
