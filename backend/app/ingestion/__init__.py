"""Pipeline de ingesta offline de V1.

Orquesta: parser (PDF → bloques con posición) → chunker (bloques → chunks sin cruzar página) →
embedder (BGE-m3, 1024 dims) → indexer (inserta `documents`/`chunks` en Postgres). El estado de
`documents.status` avanza por etapa: parsing → chunking → embedding → indexing → ready (o failed).

Fuente de verdad: docs/DECISIONES.md (ADR-003 offsets/citas, ADR-002 naming) y docs/PLAN.md (V1).

Tipos compartidos:
- `Bloque`: una unidad de texto extraída del PDF con su posición (página, sección, bbox).
- `ParsedDocument`: el resultado del parser (texto completo + bloques + metadatos del documento).
- `ChunkData`: un chunk listo para indexar (texto + metadatos de posición + offsets de documento).
- `IngestaError`: error de ingesta con `error_msg` canónico (p.ej. `needs_ocr`).
"""

from app.ingestion.types import Bloque, ChunkData, IngestaError, ParsedDocument

__all__ = ["Bloque", "ParsedDocument", "ChunkData", "IngestaError"]
