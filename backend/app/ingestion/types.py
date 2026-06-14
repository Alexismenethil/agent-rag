"""Tipos compartidos del pipeline de ingesta (sin dependencias pesadas).

Se aíslan aquí para que `app.ingestion` (y `compileall`) no requieran docling/pymupdf/torch:
los módulos que sí los usan (`parser`, `embedder`) importan sus dependencias de forma perezosa.

Naming canónico (ADR-002): metadatos de posición en español (`pagina`, `seccion`, `seccion_path`,
`offset_inicio`, `offset_fin`, `bbox`). Los offsets son de carácter sobre el texto del documento.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class IngestaError(Exception):
    """Error de ingesta con un `error_msg` canónico para `documents.error_msg`.

    El caso clave de V1 es `needs_ocr` (PDF escaneado sin capa de texto). El pipeline captura
    esta excepción, marca `documents.status='failed'` y guarda `error_msg`.
    """

    def __init__(self, error_msg: str, *, detalle: str | None = None) -> None:
        self.error_msg = error_msg
        self.detalle = detalle
        super().__init__(detalle or error_msg)


@dataclass(slots=True)
class Bloque:
    """Un bloque de texto extraído del PDF con su posición.

    - `texto`: texto del bloque (ya normalizado, sin saltos de línea redundantes en exceso).
    - `pagina`: número de página 1-based donde aparece el bloque.
    - `seccion`: encabezado/sección más cercana por encima del bloque (o None).
    - `seccion_path`: jerarquía de secciones hasta este bloque (p.ej. ["3 Métodos", "3.2 Datos"]).
    - `bbox`: caja envolvente en coordenadas del PDF ({x0,y0,x1,y1,page}) o None.
    - `es_encabezado`: True si el bloque es un título/encabezado de sección.
    """

    texto: str
    pagina: int
    seccion: str | None = None
    seccion_path: list[str] = field(default_factory=list)
    bbox: dict | None = None
    es_encabezado: bool = False


@dataclass(slots=True)
class ParsedDocument:
    """Resultado del parser: texto del documento completo + bloques + metadatos.

    - `texto`: concatenación de los bloques (es el texto sobre el que se calculan TODOS los offsets).
    - `bloques`: bloques en orden de lectura, cada uno con `offset_inicio`/`offset_fin` ya asignados
      (posición de su `texto` dentro de `texto` del documento).
    - `num_paginas`: total de páginas del PDF.
    - `parser`: nombre del parser efectivo ("docling" | "pymupdf").
    - `idioma`: idioma detectado (o None si no se detecta; en V1 se asume español por defecto).
    """

    texto: str
    bloques: list["BloqueConOffset"]
    num_paginas: int
    parser: str
    idioma: str | None = None


@dataclass(slots=True)
class BloqueConOffset:
    """Bloque con sus offsets de carácter ya resueltos sobre el texto del documento."""

    texto: str
    pagina: int
    seccion: str | None
    seccion_path: list[str]
    bbox: dict | None
    es_encabezado: bool
    offset_inicio: int
    offset_fin: int


@dataclass(slots=True)
class ChunkData:
    """Un chunk listo para indexar (lo produce el chunker; lo consume embedder/indexer).

    V1: un chunk NO cruza páginas → `pagina_fin == pagina`. Offsets de carácter sobre el texto del
    documento. `embedding` se rellena en la etapa de embeddings (None hasta entonces).
    """

    chunk_index: int
    texto: str
    pagina: int
    pagina_fin: int
    seccion: str | None
    seccion_path: list[str]
    offset_inicio: int
    offset_fin: int
    bbox: dict | None
    token_count: int
    embedding: list[float] | None = None
