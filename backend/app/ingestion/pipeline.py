"""Orquestación de la ingesta offline (V1): parser → chunker → embedder → indexer.

Avanza `documents.status` por etapa (parsing → chunking → embedding → indexing → ready). Ante
cualquier fallo deja `status='failed'` y guarda `error_msg`:
- `IngestaError('needs_ocr')` (PDF escaneado sin capa de texto) → `error_msg='needs_ocr'`.
- Cualquier otra excepción → `error_msg` con un resumen acotado (sin volcar el texto del documento,
  por privacidad ADR-007).

Las etapas pesadas (parseo, embeddings) se ejecutan en un hilo aparte vía `asyncio.to_thread`, para
no bloquear el event loop mientras corren en segundo plano.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.config import settings
from app.ingestion import indexer
from app.ingestion.chunker import chunk_document
from app.ingestion.parser import parse_pdf
from app.ingestion.types import IngestaError, ParsedDocument

logger = logging.getLogger("uvicorn.error")

# Tope defensivo del `error_msg` libre (no debe contener texto del documento; ADR-007).
_MAX_ERROR_MSG = 300


async def ingerir_documento(doc_id: uuid.UUID, data: bytes) -> None:
    """Ejecuta la ingesta completa de un documento ya creado en BD (`status='pending'`).

    Args:
        doc_id: id del documento (fila `documents` ya existe, con el PDF ya guardado en disco).
        data: bytes del PDF (se pasan para no releer del disco en el hilo de fondo).
    """
    try:
        # 1) PARSING ---------------------------------------------------------------------
        await indexer.set_status(doc_id, "parsing")
        parsed: ParsedDocument = await asyncio.to_thread(parse_pdf, data)
        await indexer.actualizar_metadatos_documento(
            doc_id,
            num_paginas=parsed.num_paginas,
            parser=parsed.parser,
            idioma=parsed.idioma,
            embedding_model=settings.embedding_model,
        )

        # 2) CHUNKING --------------------------------------------------------------------
        await indexer.set_status(doc_id, "chunking")
        chunks = chunk_document(parsed)
        if not chunks:
            raise IngestaError(
                "empty_document",
                detalle="No se obtuvieron chunks del documento (¿texto vacío tras el parseo?).",
            )

        # 3) EMBEDDING -------------------------------------------------------------------
        await indexer.set_status(doc_id, "embedding")
        # Import perezoso: el embedder carga sentence-transformers (extra `[rag]`) bajo demanda.
        from app.ingestion.embedder import embed_textos

        vectores = await asyncio.to_thread(embed_textos, [c.texto for c in chunks])
        for chunk, vec in zip(chunks, vectores, strict=True):
            chunk.embedding = vec

        # 4) INDEXING --------------------------------------------------------------------
        await indexer.set_status(doc_id, "indexing")
        n = await indexer.insertar_chunks(doc_id, chunks)
        logger.info("Ingesta de %s: %d chunks indexados.", doc_id, n)

        # 5) READY -----------------------------------------------------------------------
        await indexer.set_status(doc_id, "ready")

    except IngestaError as exc:
        logger.warning("Ingesta de %s fallida: %s", doc_id, exc.error_msg)
        await indexer.set_status(doc_id, "failed", error_msg=exc.error_msg[:_MAX_ERROR_MSG])
    except Exception as exc:  # noqa: BLE001 - cualquier fallo deja el documento en 'failed'
        logger.exception("Error inesperado ingiriendo %s", doc_id)
        await indexer.set_status(
            doc_id, "failed", error_msg=f"error_interno: {type(exc).__name__}"[:_MAX_ERROR_MSG]
        )
