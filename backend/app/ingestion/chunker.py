"""Chunking por estructura, SIN cruzar páginas (V1).

Reglas (docs/DECISIONES.md ADR-003, docs/PLAN.md V1):
- Un chunk NO cruza páginas → `pagina_fin == pagina`. El chunker corta en frontera de página.
- Agrupa bloques contiguos de la MISMA página hasta un objetivo de tamaño (en caracteres como proxy
  de tokens), respetando la frontera de bloque (no parte un bloque por la mitad salvo que el bloque
  por sí solo exceda el objetivo, en cuyo caso se trocea por oraciones).
- Solape razonable entre chunks consecutivos de la misma página (continuidad de contexto).
- Metadatos por chunk: `pagina`, `seccion` (la del primer bloque del chunk), `seccion_path`,
  `offset_inicio`/`offset_fin` (offsets de carácter sobre el texto del documento, tomados de los
  bloques: el chunk es siempre un substring contiguo del texto del documento), `bbox` (unión de las
  bboxes de sus bloques en esa página), `chunk_index` (global, 0-based) y `token_count` aproximado.

Importante: como los offsets salen directamente del texto del documento, `documento.texto[ini:fin]`
== `chunk.texto`. Esto es lo que hace que el span de cita sea localizable a nivel de carácter.
"""

from __future__ import annotations

import re

from app.ingestion.types import BloqueConOffset, ChunkData, ParsedDocument

# Objetivo y mínimo de tamaño de chunk (en caracteres; proxy estable de tokens sin tokenizer pesado).
_OBJETIVO_CHARS = 1200
_MAX_CHARS = 1600
_SOLAPE_CHARS = 200

# Aproximación de tokens: ~4 caracteres por token (suficiente para `token_count` orientativo).
_CHARS_POR_TOKEN = 4

_RE_ORACION = re.compile(r"(?<=[.!?])\s+")


def aproximar_tokens(texto: str) -> int:
    """Aproxima el número de tokens de un texto (sin cargar un tokenizer pesado)."""
    return max(1, round(len(texto) / _CHARS_POR_TOKEN))


def chunk_document(parsed: ParsedDocument) -> list[ChunkData]:
    """Convierte un `ParsedDocument` en una lista de `ChunkData` (sin cruzar páginas).

    Recorre los bloques agrupándolos por página y por tamaño objetivo. Devuelve los chunks en orden
    de lectura con `chunk_index` global empezando en 0.
    """
    chunks: list[ChunkData] = []
    indice = 0
    # Agrupa bloques por página preservando el orden.
    for bloques_pagina in _por_pagina(parsed.bloques):
        for grupo in _agrupar_en_chunks(bloques_pagina, parsed.texto):
            chunks.append(_construir_chunk(grupo, indice, parsed.texto))
            indice += 1
    return chunks


def _por_pagina(bloques: list[BloqueConOffset]) -> list[list[BloqueConOffset]]:
    """Parte la lista de bloques en sublistas contiguas de la misma página (frontera de página)."""
    grupos: list[list[BloqueConOffset]] = []
    actual: list[BloqueConOffset] = []
    pagina_actual: int | None = None
    for b in bloques:
        if pagina_actual is None or b.pagina == pagina_actual:
            actual.append(b)
            pagina_actual = b.pagina
        else:
            grupos.append(actual)
            actual = [b]
            pagina_actual = b.pagina
    if actual:
        grupos.append(actual)
    return grupos


def _agrupar_en_chunks(
    bloques: list[BloqueConOffset], texto_doc: str
) -> list[list[tuple[int, int, BloqueConOffset]]]:
    """Agrupa bloques de UNA página en chunks por tamaño objetivo, con solape entre chunks.

    Cada elemento del grupo es `(offset_inicio, offset_fin, bloque)` (los offsets pueden recortarse
    respecto a los del bloque cuando un bloque enorme se trocea por oraciones). El span de cada chunk
    sigue siendo un substring contiguo del texto del documento.
    """
    # Primero, expande bloques demasiado grandes en sub-spans por oración (sin cruzar el bloque).
    spans: list[tuple[int, int]] = []
    for b in bloques:
        if (b.offset_fin - b.offset_inicio) <= _MAX_CHARS:
            spans.append((b.offset_inicio, b.offset_fin))
        else:
            spans.extend(_trocear_por_oraciones(b.offset_inicio, b.offset_fin, texto_doc))

    grupos: list[list[tuple[int, int]]] = []
    actual: list[tuple[int, int]] = []
    for ini, fin in spans:
        if actual:
            inicio_grupo = actual[0][0]
            # El tamaño real del chunk es `max_fin - min_inicio` (es un substring contiguo del texto):
            # se cierra el grupo si añadir este span superaría el objetivo de tamaño.
            if (fin - inicio_grupo) > _OBJETIVO_CHARS:
                grupos.append(actual)
                # Solape: el siguiente chunk reincluye los últimos spans hasta ~_SOLAPE_CHARS.
                actual = _con_solape(actual)
        actual.append((ini, fin))
    if actual:
        grupos.append(actual)

    # Mapea cada span de cada grupo de vuelta a su bloque (para arrastrar metadatos: sección/bbox).
    resultado: list[list[tuple[int, int, BloqueConOffset]]] = []
    for grupo in grupos:
        resultado.append([(ini, fin, _bloque_de(ini, bloques)) for ini, fin in grupo])
    return resultado


def _trocear_por_oraciones(inicio: int, fin: int, texto_doc: str) -> list[tuple[int, int]]:
    """Trocea un span grande en sub-spans por oración, respetando el objetivo de tamaño.

    Devuelve sub-spans (offsets absolutos sobre el texto del documento) CONTIGUOS que recubren
    exactamente `[inicio, fin)` sin huecos ni solapes: cada sub-span termina en la frontera de
    oración más cercana sin pasar `_OBJETIVO_CHARS`, y el separador entre oraciones queda adherido al
    sub-span previo (así `texto_doc[a:b]` de cada sub-span es contiguo y los offsets son estables).
    """
    # Fronteras de oración (offsets absolutos) dentro de [inicio, fin): fin de cada match del patrón.
    fronteras: list[int] = []
    for m in _RE_ORACION.finditer(texto_doc, inicio, fin):
        fronteras.append(m.end())  # corte tras el espacio que sigue al signo de puntuación

    sub: list[tuple[int, int]] = []
    actual_ini = inicio
    ultima_frontera = inicio
    for f in fronteras:
        if (f - actual_ini) > _OBJETIVO_CHARS and ultima_frontera > actual_ini:
            # Cierra en la última frontera válida (mantiene oraciones completas cuando se puede).
            sub.append((actual_ini, ultima_frontera))
            actual_ini = ultima_frontera
        ultima_frontera = f
    if fin > actual_ini:
        sub.append((actual_ini, fin))
    return sub or [(inicio, fin)]


def _con_solape(grupo: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Arranca el siguiente chunk con el solape de contexto del anterior.

    Devuelve un único span sintético `(inicio_solape, fin_grupo)` que cubre como mucho `_SOLAPE_CHARS`
    caracteres finales del grupo. Se recorta sobre el texto (no se arrastran spans completos), de modo
    que el solape nunca infla el chunk siguiente por encima del objetivo. El span sigue siendo un
    sub-rango contiguo del texto del documento, así que la invariante `texto[ini:fin]` se mantiene.
    """
    if not grupo:
        return []
    inicio_grupo = grupo[0][0]
    fin_grupo = grupo[-1][1]
    inicio_solape = max(inicio_grupo, fin_grupo - _SOLAPE_CHARS)
    return [(inicio_solape, fin_grupo)]


def _bloque_de(offset: int, bloques: list[BloqueConOffset]) -> BloqueConOffset:
    """Devuelve el bloque que contiene un offset dado (para arrastrar sección/bbox)."""
    for b in bloques:
        if b.offset_inicio <= offset < b.offset_fin:
            return b
    return bloques[0]


def _construir_chunk(
    grupo: list[tuple[int, int, BloqueConOffset]], indice: int, texto_doc: str
) -> ChunkData:
    """Construye un `ChunkData` a partir de un grupo de spans de la MISMA página.

    El texto del chunk es el substring contiguo `[min_inicio, max_fin)` del texto del documento, de
    modo que `texto_doc[offset_inicio:offset_fin] == chunk.texto` (clave para localizar citas).
    """
    offset_inicio = min(ini for ini, _f, _b in grupo)
    offset_fin = max(fin for _i, fin, _b in grupo)
    texto = texto_doc[offset_inicio:offset_fin]

    primero = grupo[0][2]
    pagina = primero.pagina  # todos comparten página (no cruza páginas)
    seccion = primero.seccion
    seccion_path = list(primero.seccion_path)
    bbox = _unir_bboxes([b for _i, _f, b in grupo])

    return ChunkData(
        chunk_index=indice,
        texto=texto,
        pagina=pagina,
        pagina_fin=pagina,  # V1: un chunk no cruza páginas
        seccion=seccion,
        seccion_path=seccion_path or None,
        offset_inicio=offset_inicio,
        offset_fin=offset_fin,
        bbox=bbox,
        token_count=aproximar_tokens(texto),
    )


def _unir_bboxes(bloques: list[BloqueConOffset]) -> dict | None:
    """Une las bboxes de los bloques de un chunk (misma página) en una caja envolvente."""
    cajas = [b.bbox for b in bloques if b.bbox]
    if not cajas:
        return None
    x0 = min(c["x0"] for c in cajas)
    y0 = min(c["y0"] for c in cajas)
    x1 = max(c["x1"] for c in cajas)
    y1 = max(c["y1"] for c in cajas)
    page = cajas[0].get("page")
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "page": page}
