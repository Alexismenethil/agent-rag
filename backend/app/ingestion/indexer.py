"""Indexer: persiste documentos y chunks en Postgres (async SQLAlchemy ORM).

Usa los modelos ORM de fundamentos (`app.models`) y abre su propia sesión async (`SessionLocal`),
porque la ingesta corre en segundo plano fuera del ciclo request/response (no hay `Depends`).

Responsabilidades:
- Actualizar `documents.status` por etapa y `error_msg`/`updated_at` en fallo (`set_status`).
- Volcar metadatos del documento tras el parseo (`actualizar_metadatos_documento`): `num_paginas`,
  `parser`, `idioma`, `embedding_model`.
- Insertar los chunks ya con embedding (`insertar_chunks`), borrando los previos del documento para
  hacer la re-ingesta idempotente (mismo `doc_id` → se reemplazan sus chunks).

Idempotencia por contenido: la UNICIDAD `(owner_id, content_sha256)` la resuelve el router antes de
crear el documento (si ya existe uno con el mismo sha para ese dueño, reutiliza esa fila). Aquí la
idempotencia es a nivel de chunks: re-ingerir un `doc_id` reemplaza sus chunks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, update

from app.db import SessionLocal
from app.ingestion.types import ChunkData
from app.models import Chunk, Document


async def set_status(doc_id: uuid.UUID, status: str, *, error_msg: str | None = None) -> None:
    """Actualiza `documents.status` (y `error_msg`/`updated_at`) en su propia transacción."""
    async with SessionLocal() as session:
        await session.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(
                status=status,
                error_msg=error_msg,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


async def actualizar_metadatos_documento(
    doc_id: uuid.UUID,
    *,
    num_paginas: int | None,
    parser: str | None,
    idioma: str | None,
    embedding_model: str | None,
) -> None:
    """Guarda en `documents` los metadatos derivados del parseo (no toca el status)."""
    async with SessionLocal() as session:
        await session.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(
                num_paginas=num_paginas,
                parser=parser,
                idioma=idioma,
                embedding_model=embedding_model,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


async def insertar_chunks(doc_id: uuid.UUID, chunks: list[ChunkData]) -> int:
    """Inserta los chunks del documento (reemplazando los previos). Devuelve cuántos insertó.

    Re-ingesta idempotente: primero borra los chunks existentes de `doc_id` (la columna `tsv` es
    GENERATED y la gestiona la BD; `embedding` ya viene calculado en cada `ChunkData`).
    """
    async with SessionLocal() as session:
        # Limpia chunks previos del documento (re-ingesta).
        await session.execute(delete(Chunk).where(Chunk.doc_id == doc_id))

        session.add_all(
            [
                Chunk(
                    doc_id=doc_id,
                    chunk_index=c.chunk_index,
                    texto=c.texto,
                    embedding=c.embedding,
                    pagina=c.pagina,
                    pagina_fin=c.pagina_fin,
                    seccion=c.seccion,
                    seccion_path=c.seccion_path,
                    offset_inicio=c.offset_inicio,
                    offset_fin=c.offset_fin,
                    bbox=c.bbox,
                    token_count=c.token_count,
                )
                for c in chunks
            ]
        )
        await session.commit()
    return len(chunks)
