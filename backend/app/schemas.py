"""Esquemas Pydantic v2 de request/response de los endpoints de V1.

Fuente de verdad del contrato: `docs/DECISIONES.md` ADR-004 (campos de dominio en español).
Estos esquemas son la forma canónica que documentan los routers (documents, query, sessions).

Convenciones:
- Campos de dominio/posición en español (`pregunta`, `pagina`, `offset_inicio`, `snippet`, …).
- `modo ∈ {estricto, ampliado}`; en V1 solo se usa `estricto`.
- `status` de documento en minúsculas (ADR-001).
- El campo `modelo` de la respuesta refleja el `model_id` real devuelto por el provider.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Tipos de dominio reutilizables (coinciden con los CHECK de SQL).
Modo = Literal["estricto", "ampliado"]
DocumentStatus = Literal[
    "pending", "parsing", "chunking", "embedding", "indexing", "ready", "failed"
]
Role = Literal["user", "assistant", "system"]


# --------------------------------------------------------------------------------------
# Documentos
# --------------------------------------------------------------------------------------
class DocumentUploadResponse(BaseModel):
    """Respuesta de `POST /documents` (202): se acepta y empieza la ingesta async."""

    doc_id: UUID
    status: DocumentStatus


class DocumentListItem(BaseModel):
    """Ítem de la lista de `GET /documents`."""

    model_config = ConfigDict(from_attributes=True)

    doc_id: UUID = Field(..., validation_alias="id")
    titulo: str | None = None
    filename: str
    status: DocumentStatus
    num_paginas: int | None = None
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    """Respuesta de `GET /documents/{doc_id}`: estado de ingesta."""

    doc_id: UUID
    status: DocumentStatus
    progress: float = Field(
        0.0, ge=0.0, le=1.0, description="Avance de la ingesta en [0,1] (orientativo)"
    )
    num_paginas: int | None = None
    error_msg: str | None = Field(
        None, description="Mensaje de error si status='failed' (p.ej. 'needs_ocr')"
    )


# --------------------------------------------------------------------------------------
# Consulta RAG (/query)
# --------------------------------------------------------------------------------------
class ConsultaRequest(BaseModel):
    """Request de `POST /query`."""

    doc_id: UUID
    pregunta: str = Field(..., min_length=1)
    modo: Modo = "estricto"
    session_id: UUID | None = None
    top_k: int = Field(8, ge=1, le=50)


class Cita(BaseModel):
    """Cita a nivel de afirmación, con snippet y offsets calculados por el backend.

    El LLM nunca inventa offsets: el backend mapea el marcador `[n] → chunk_id` y localiza el
    substring de la afirmación dentro de `chunks.texto` (ver ADR-003).
    """

    marcador: int = Field(..., description="Número [n] de la cita dentro de la respuesta")
    chunk_id: UUID | None = Field(
        None, description="Chunk de origen; null si el documento fue borrado después (SET NULL)"
    )
    doc_id: UUID
    pagina: int
    seccion: str | None = None
    offset_inicio: int
    offset_fin: int
    snippet: str = Field(..., description="Fragmento textual literal del documento")
    texto_afirmacion: str = Field(..., description="Afirmación que esta cita respalda")


class ConsultaResponse(BaseModel):
    """Response de `POST /query` (no-streaming en V1)."""

    message_id: UUID
    session_id: UUID
    respuesta: str = Field(..., description="Texto con marcadores [1] [2] …")
    citas: list[Cita] = Field(default_factory=list)
    informacion_ampliada: str | None = Field(
        None,
        description="En modo ampliado: texto extra etiquetado aparte; nunca mezclado con respuesta",
    )
    groundedness: float = Field(..., description="Score de fidelidad en runtime (≠ RAGAS)")
    modelo: str = Field(..., description="model_id real devuelto por el provider (no hardcodeado)")


# --------------------------------------------------------------------------------------
# Sesiones / historial (/sessions)
# --------------------------------------------------------------------------------------
class SessionListItem(BaseModel):
    """Ítem de `GET /sessions`: resumen de una conversación."""

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID = Field(..., validation_alias="id")
    doc_id: UUID | None = None
    titulo: str | None = None
    modo_default: Modo = "estricto"
    created_at: datetime
    updated_at: datetime


class MessageItem(BaseModel):
    """Mensaje embebido en el detalle de una sesión (`GET /sessions/{id}`)."""

    model_config = ConfigDict(from_attributes=True)

    message_id: UUID = Field(..., validation_alias="id")
    role: Role
    contenido: str
    modo: Modo | None = None
    groundedness: float | None = None
    modelo: str | None = Field(None, validation_alias="llm_model")
    citas: list[Cita] = Field(default_factory=list)
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """Detalle de `GET /sessions/{id}`: la conversación con sus mensajes embebidos."""

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID = Field(..., validation_alias="id")
    doc_id: UUID | None = None
    titulo: str | None = None
    modo_default: Modo = "estricto"
    created_at: datetime
    updated_at: datetime
    mensajes: list[MessageItem] = Field(default_factory=list)
