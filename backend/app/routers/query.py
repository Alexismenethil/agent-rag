"""Consulta RAG (`POST /query`): pregunta sobre un documento y responde con citas exactas.

V1 = SOLO modo estricto, SOLO recuperación vectorial, SIN streaming (docs/PLAN.md).

Flujo (online):
  1. Valida que el documento sea del usuario y esté en `ready`.
  2. Recupera los `top_k` chunks más similares a la pregunta (kNN vectorial, `app.retrieval`).
  3. Arma el prompt de grounding estricto y llama al LLM (`ClaudeProvider`).
  4. Resuelve los marcadores `[n]` → citas con snippet + offsets (`app.grounding.citations`).
  5. Persiste conversación/mensajes/citas y devuelve el `ConsultaResponse` canónico (ADR-004).

El contrato (request/response/Cita) se importa de `app.schemas` (forma canónica, ADR-004); este
router ya no define modelos Pydantic inline.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import get_current_user_id
from app.grounding import (
    RESPUESTA_NO_ENCONTRADO,
    calcular_groundedness,
    construir_mensaje_usuario,
    construir_system_prompt,
    resolver_citas,
)
from app.grounding.citations import CitaResuelta
from app.llm import LLMMessage, LLMProvider
from app.llm.factory import get_provider
from app.models import Conversation, Document, Message, MessageCitation
from app.retrieval import buscar_chunks
from app.retrieval.vector import ChunkRecuperado
from app.schemas import Cita, ConsultaRequest, ConsultaResponse

router = APIRouter(tags=["query"])


def get_llm_provider() -> LLMProvider:
    """Dependencia del proveedor de LLM (según settings.llm_provider). Sustituible en tests."""
    return get_provider()


@router.post("/query", response_model=ConsultaResponse)
async def consultar(
    req: ConsultaRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    llm: LLMProvider = Depends(get_llm_provider),
) -> ConsultaResponse:
    """Responde una pregunta sobre un documento citando el punto exacto (modo estricto)."""
    t0 = time.perf_counter()
    user_uuid = UUID(str(user_id))

    # V1 = SOLO modo estricto (docs/PLAN.md). El modo ampliado llega en V2.
    if req.modo != "estricto":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "En V1 solo está disponible el modo 'estricto'. El modo 'ampliado' llega en V2.",
        )

    # 1) Documento del usuario y en estado 'ready' (valida propiedad/estado, lanza HTTP si no).
    await _cargar_documento_listo(session, req.doc_id, user_uuid)

    # 2) Recuperación vectorial (kNN) acotada al documento.
    try:
        chunks = await buscar_chunks(session, req.doc_id, req.pregunta, req.top_k)
    except RuntimeError as exc:
        # Embedder de ingesta no disponible o error de dimensión: error claro al cliente.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"No se pudo embeber/recuperar para la consulta: {exc}",
        ) from exc

    # 3) Sesión (conversación): se crea si no llega `session_id`.
    conversacion = await _obtener_o_crear_conversacion(
        session, req.session_id, user_uuid, req.doc_id, req.pregunta, req.modo
    )

    # 4) Prompt de grounding estricto + llamada al LLM.
    if not chunks:
        # Sin contexto recuperable, no se llama al LLM: se responde "no encontrado".
        respuesta_texto = RESPUESTA_NO_ENCONTRADO
        modelo_real = settings.llm_model
        prompt_tokens = completion_tokens = 0
    else:
        system_prompt = construir_system_prompt(req.modo)
        contenido_usuario = construir_mensaje_usuario(req.pregunta, chunks)
        try:
            resultado = await llm.complete(
                system=system_prompt,
                messages=[LLMMessage(role="user", content=contenido_usuario)],
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature,
            )
        except Exception as exc:  # noqa: BLE001 - error del proveedor de LLM → 502 limpio
            # Causa típica según LLM_PROVIDER: servidor Ollama caído / modelo inexistente (local),
            # o ANTHROPIC_API_KEY inválida (anthropic).
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"El proveedor de LLM ({settings.llm_provider}) falló: {type(exc).__name__}. "
                "Revisa el servidor de Ollama o la API key en el .env.",
            ) from exc
        respuesta_texto = resultado.text or RESPUESTA_NO_ENCONTRADO
        modelo_real = resultado.model
        prompt_tokens = resultado.usage.prompt_tokens
        completion_tokens = resultado.usage.completion_tokens

    # 5) Resolución de citas (marcador [n] → chunk → snippet + offsets) y groundedness.
    citas_resueltas = resolver_citas(respuesta_texto, chunks)
    # Algunos modelos añaden marcadores de más a la respuesta "no encontrado"
    # (p.ej. "No encontrado en el documento. [1][2]"); en ese caso se normaliza sin citas.
    if RESPUESTA_NO_ENCONTRADO.rstrip(".").lower() in respuesta_texto.lower():
        respuesta_texto = RESPUESTA_NO_ENCONTRADO
        citas_resueltas = []
    groundedness = calcular_groundedness(respuesta_texto, citas_resueltas)
    if respuesta_texto != RESPUESTA_NO_ENCONTRADO and (
        groundedness < 1.0 or any(not c.localizado for c in citas_resueltas)
    ):
        # V1 promete citas exactas. Si el modelo omitió marcadores o el backend no pudo localizar
        # literalmente el span citado, es más seguro degradar que exponer una cita imprecisa.
        respuesta_texto = RESPUESTA_NO_ENCONTRADO
        citas_resueltas = []
        groundedness = calcular_groundedness(respuesta_texto, citas_resueltas)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    # 6) Persistencia: mensaje del usuario, mensaje del asistente y sus citas.
    msg_asistente = await _persistir_turno(
        session,
        conversacion=conversacion,
        pregunta=req.pregunta,
        modo=req.modo,
        respuesta_texto=respuesta_texto,
        modelo_real=modelo_real,
        groundedness=groundedness,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        chunks=chunks,
        citas_resueltas=citas_resueltas,
    )
    await session.commit()

    # 7) Respuesta canónica (informacion_ampliada = null en modo estricto).
    return ConsultaResponse(
        message_id=msg_asistente.id,
        session_id=conversacion.id,
        respuesta=respuesta_texto,
        citas=[_a_cita_schema(c) for c in citas_resueltas],
        informacion_ampliada=None,
        groundedness=groundedness,
        modelo=modelo_real,
    )


# --------------------------------------------------------------------------------------
# Helpers de persistencia y carga
# --------------------------------------------------------------------------------------
async def _cargar_documento_listo(
    session: AsyncSession, doc_id: UUID, user_uuid: UUID
) -> Document:
    """Carga el documento validando propiedad y estado `ready`. Lanza HTTP 404/409/403."""
    documento = await session.get(Document, doc_id)
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    if documento.owner_id is not None and documento.owner_id != user_uuid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El documento no pertenece al usuario.")
    if documento.status != "ready":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El documento aún no está listo (status='{documento.status}'). "
            "Espera a que la ingesta termine en 'ready'.",
        )
    return documento


async def _obtener_o_crear_conversacion(
    session: AsyncSession,
    session_id: UUID | None,
    user_uuid: UUID,
    doc_id: UUID,
    pregunta: str,
    modo: str,
) -> Conversation:
    """Devuelve la conversación indicada (validando propiedad) o crea una nueva.

    El título de una conversación nueva es un recorte de la primera pregunta (orientativo).
    """
    if session_id is not None:
        conversacion = await session.get(Conversation, session_id)
        if conversacion is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada.")
        if conversacion.user_id != user_uuid:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "La sesión no pertenece al usuario.")
        if conversacion.doc_id != doc_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La sesión pertenece a otro documento. Inicia una sesión nueva para este PDF.",
            )
        return conversacion

    titulo = pregunta.strip()
    if len(titulo) > 80:
        titulo = titulo[:77].rstrip() + "…"
    conversacion = Conversation(
        user_id=user_uuid,
        doc_id=doc_id,
        titulo=titulo or None,
        modo_default=modo,
    )
    session.add(conversacion)
    await session.flush()  # asigna id sin cerrar la transacción
    return conversacion


async def _persistir_turno(
    session: AsyncSession,
    *,
    conversacion: Conversation,
    pregunta: str,
    modo: str,
    respuesta_texto: str,
    modelo_real: str,
    groundedness: float,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    chunks: list[ChunkRecuperado],
    citas_resueltas: list[CitaResuelta],
) -> Message:
    """Inserta el mensaje del usuario, el del asistente y las citas denormalizadas.

    Guarda en `messages.retrieval_debug` un resumen mínimo de la recuperación (chunk_ids y score)
    para trazabilidad en V1. Devuelve el mensaje del asistente creado (con su `id` ya asignado)
    para que el endpoint construya la respuesta.
    """
    # Mensaje del usuario (la pregunta).
    conversacion.updated_at = datetime.now(timezone.utc)

    msg_user = Message(
        conversation_id=conversacion.id,
        role="user",
        contenido=pregunta,
        modo=modo,
    )
    session.add(msg_user)

    # Mensaje del asistente (la respuesta).
    retrieval_debug = {
        "modo": modo,
        "top_k": len(chunks),
        "chunks": [
            {"chunk_id": str(ch.chunk_id), "chunk_index": ch.chunk_index, "score": ch.score}
            for ch in chunks
        ],
        "groundedness_nota": "heurística provisional V1: proporción de citas localizadas",
    }
    msg_asistente = Message(
        conversation_id=conversacion.id,
        role="assistant",
        contenido=respuesta_texto,
        modo=modo,
        llm_model=modelo_real,
        groundedness=groundedness,
        retrieval_debug=retrieval_debug,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )
    session.add(msg_asistente)
    await session.flush()  # asigna id del mensaje del asistente

    # Citas relacionales (denormalizadas) ligadas al mensaje del asistente.
    for c in citas_resueltas:
        session.add(
            MessageCitation(
                message_id=msg_asistente.id,
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                marcador=c.marcador,
                texto_afirmacion=c.texto_afirmacion,
                pagina=c.pagina,
                seccion=c.seccion,
                offset_inicio=c.offset_inicio,
                offset_fin=c.offset_fin,
                snippet=c.snippet,
            )
        )

    return msg_asistente


def _a_cita_schema(c: CitaResuelta) -> Cita:
    """Convierte una `CitaResuelta` interna al esquema `Cita` de la respuesta (ADR-004).

    El esquema `Cita` exige `pagina`/`offset_*` no nulos: cuando el localizador no pudo fijar
    valores (caso límite), se rellenan con 0 como respaldo seguro para no romper el contrato.
    """
    return Cita(
        marcador=c.marcador,
        chunk_id=c.chunk_id,
        doc_id=c.doc_id,  # type: ignore[arg-type]  # en V1 siempre proviene de un chunk con doc_id
        pagina=c.pagina if c.pagina is not None else 0,
        seccion=c.seccion,
        offset_inicio=c.offset_inicio if c.offset_inicio is not None else 0,
        offset_fin=c.offset_fin if c.offset_fin is not None else 0,
        snippet=c.snippet,
        texto_afirmacion=c.texto_afirmacion,
    )
