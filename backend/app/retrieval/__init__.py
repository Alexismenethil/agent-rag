"""Recuperación (retrieval) del RAG.

V1 = SOLO búsqueda vectorial (kNN sobre pgvector). La recuperación híbrida (BM25 + RRF) y el
reranker llegan en V2 (ver docs/PLAN.md y docs/DECISIONES.md).

Reexporta el punto de entrada de la recuperación vectorial para importar desde `app.retrieval`:

    from app.retrieval import buscar_chunks, ChunkRecuperado
"""

from app.retrieval.vector import (
    ChunkRecuperado,
    buscar_chunks,
    buscar_chunks_con_embedding,
    embed_pregunta,
)

__all__ = [
    "ChunkRecuperado",
    "buscar_chunks",
    "buscar_chunks_con_embedding",
    "embed_pregunta",
]
