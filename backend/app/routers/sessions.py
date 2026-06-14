"""Sesiones / historial (`/sessions`) — V1.

- `GET /sessions`            → lista las conversaciones del usuario (resumen).
- `GET /sessions/{id}`       → detalle de una conversación con sus mensajes embebidos y, en cada
                               mensaje de asistente, sus citas.

La identidad viaja por el header `X-User-Id` (MVP, ver `app.deps.get_current_user_id`). Los
esquemas de respuesta son los canónicos de `app.schemas` (ADR-004): `SessionListItem`,
`SessionDetailResponse` con `MessageItem`/`Cita`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.deps import get_current_user_id
from app.models import Conversation, Message
from app.schemas import (
    Cita,
    MessageItem,
    SessionDetailResponse,
    SessionListItem,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionListItem])
async def listar_sesiones(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[SessionListItem]:
    """Lista las conversaciones del usuario, de la más reciente a la más antigua."""
    user_uuid = UUID(str(user_id))
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_uuid)
        .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
    )
    result = await session.execute(stmt)
    conversaciones = result.scalars().all()
    return [SessionListItem.model_validate(c) for c in conversaciones]


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def detalle_sesion(
    session_id: UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SessionDetailResponse:
    """Detalle de una conversación del usuario con sus mensajes y citas embebidos."""
    user_uuid = UUID(str(user_id))

    stmt = (
        select(Conversation)
        .where(Conversation.id == session_id)
        .options(selectinload(Conversation.messages).selectinload(Message.citations))
    )
    result = await session.execute(stmt)
    conversacion = result.scalar_one_or_none()

    if conversacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada.")
    if conversacion.user_id != user_uuid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La sesión no pertenece al usuario.")

    mensajes = [_a_message_item(m) for m in conversacion.messages]
    return SessionDetailResponse(
        id=conversacion.id,
        doc_id=conversacion.doc_id,
        titulo=conversacion.titulo,
        modo_default=conversacion.modo_default,  # type: ignore[arg-type]
        created_at=conversacion.created_at,
        updated_at=conversacion.updated_at,
        mensajes=mensajes,
    )


def _a_message_item(m: Message) -> MessageItem:
    """Convierte un `Message` ORM (con sus citas) al esquema `MessageItem` (ADR-004)."""
    citas = [
        Cita(
            marcador=c.marcador,
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,  # type: ignore[arg-type]
            pagina=c.pagina if c.pagina is not None else 0,
            seccion=c.seccion,
            offset_inicio=c.offset_inicio if c.offset_inicio is not None else 0,
            offset_fin=c.offset_fin if c.offset_fin is not None else 0,
            snippet=c.snippet or "",
            texto_afirmacion=c.texto_afirmacion or "",
        )
        for c in m.citations
    ]
    return MessageItem(
        id=m.id,
        role=m.role,  # type: ignore[arg-type]
        contenido=m.contenido,
        modo=m.modo,  # type: ignore[arg-type]
        groundedness=m.groundedness,
        llm_model=m.llm_model,
        citas=citas,
        created_at=m.created_at,
    )
