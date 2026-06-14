"""Parser de PDF: extrae bloques con su posición (página, sección, bbox) y arma el texto del documento.

Estrategia (V1, docs/PLAN.md):
1. **Docling** (preferido): preserva estructura (encabezados/secciones) y posición. Si está instalado
   y parsea con texto, se usa su salida.
2. **PyMuPDF / fitz** (respaldo): extracción por bloques con bbox y página; heurística simple de
   encabezados (líneas cortas en mayúsculas / numeración de sección) para `seccion`/`seccion_path`.

Detección de PDF SIN capa de texto (escaneado): si tras parsear no hay texto extraíble, se lanza
`IngestaError('needs_ocr')`. El pipeline lo traduce a `documents.status='failed'`, `error_msg='needs_ocr'`.
OCR queda para V5.

Offsets (ADR-003): se concatenan los bloques con un separador fijo (`\n\n`) y se asigna a cada bloque
`offset_inicio`/`offset_fin` = posición de su texto dentro del texto del documento. Esos offsets son la
referencia estable que luego usan chunks y citas. Las dependencias pesadas (docling/fitz) se importan de
forma PEREZOSA para no exigir el extra `[rag]` al importar el paquete.
"""

from __future__ import annotations

import logging
import re

from app.ingestion.types import Bloque, BloqueConOffset, IngestaError, ParsedDocument

logger = logging.getLogger("uvicorn.error")

# Separador entre bloques al construir el texto del documento. Es fijo y conocido para que los
# offsets sean reproducibles (mismo PDF → mismos offsets, requisito del set gold por offsets).
_SEP = "\n\n"

# Texto mínimo (caracteres no-espacio) para considerar que el PDF SÍ tiene capa de texto.
_MIN_CHARS_TEXTO = 32

# Heurística de encabezado: numeración de sección (1, 1.2, 3.4.1) o título corto en mayúsculas.
_RE_NUM_SECCION = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s+\S")


def parse_pdf(data: bytes) -> ParsedDocument:
    """Parsea el PDF (bytes) y devuelve `ParsedDocument` con texto, bloques y offsets.

    Intenta Docling; si no está disponible o falla, usa PyMuPDF. Si ninguno extrae texto suficiente,
    lanza `IngestaError('needs_ocr')`.
    """
    bloques: list[Bloque] = []
    num_paginas = 0
    parser_usado = ""

    # 1) Docling (preferido).
    try:
        bloques, num_paginas = _parse_docling(data)
        parser_usado = "docling"
    except IngestaError:
        raise
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de docling cae al respaldo
        logger.info("Docling no disponible o falló (%s); usando PyMuPDF de respaldo.", exc)

    # 2) PyMuPDF (respaldo) si Docling no produjo bloques con texto.
    if not _hay_texto(bloques):
        bloques, num_paginas = _parse_pymupdf(data)
        parser_usado = "pymupdf"

    # 3) Sin capa de texto → OCR (no soportado en V1).
    if not _hay_texto(bloques):
        raise IngestaError(
            "needs_ocr",
            detalle="El PDF no tiene capa de texto extraíble (probablemente escaneado).",
        )

    texto, bloques_offset = _ensamblar_texto(bloques)
    return ParsedDocument(
        texto=texto,
        bloques=bloques_offset,
        num_paginas=num_paginas,
        parser=parser_usado,
        idioma="es",
    )


def _hay_texto(bloques: list[Bloque]) -> bool:
    """True si los bloques contienen suficiente texto real (no solo espacios)."""
    total = sum(len(b.texto.strip()) for b in bloques)
    return total >= _MIN_CHARS_TEXTO


def _ensamblar_texto(bloques: list[Bloque]) -> tuple[str, list[BloqueConOffset]]:
    """Concatena los bloques en el texto del documento y asigna offsets de carácter a cada uno.

    El offset de cada bloque es la posición de su texto dentro del texto del documento completo
    (estable e independiente del render, ADR-003).
    """
    partes: list[str] = []
    con_offset: list[BloqueConOffset] = []
    cursor = 0
    for i, b in enumerate(bloques):
        if i > 0:
            cursor += len(_SEP)
            partes.append(_SEP)
        inicio = cursor
        fin = inicio + len(b.texto)
        partes.append(b.texto)
        cursor = fin
        con_offset.append(
            BloqueConOffset(
                texto=b.texto,
                pagina=b.pagina,
                seccion=b.seccion,
                seccion_path=list(b.seccion_path),
                bbox=b.bbox,
                es_encabezado=b.es_encabezado,
                offset_inicio=inicio,
                offset_fin=fin,
            )
        )
    return "".join(partes), con_offset


# --------------------------------------------------------------------------------------
# Docling
# --------------------------------------------------------------------------------------
def _parse_docling(data: bytes) -> tuple[list[Bloque], int]:
    """Parsea con Docling. Importa docling de forma perezosa (extra `[rag]`).

    Recorre los ítems del documento Docling preservando texto, página, bbox y la jerarquía de
    encabezados para `seccion`/`seccion_path`. Lanza la excepción original si docling no está.
    """
    import tempfile
    from pathlib import Path

    from docling.document_converter import DocumentConverter  # type: ignore

    # Docling parte de un archivo; usamos un temporal con el PDF.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        converter = DocumentConverter()
        result = converter.convert(Path(tmp.name))

    doc = result.document
    bloques: list[Bloque] = []
    seccion_actual: str | None = None
    seccion_path: list[str] = []
    paginas_vistas: set[int] = set()

    # `iterate_items` recorre los elementos del cuerpo en orden de lectura.
    for item, _level in doc.iterate_items():
        texto = (getattr(item, "text", None) or "").strip()
        if not texto:
            continue

        pagina = _docling_pagina(item)
        if pagina:
            paginas_vistas.add(pagina)
        bbox = _docling_bbox(item, pagina)

        label = str(getattr(item, "label", "") or "").lower()
        es_encabezado = "header" in label or "title" in label or "section" in label
        if es_encabezado:
            seccion_actual = texto
            seccion_path = _actualizar_path(seccion_path, texto)

        bloques.append(
            Bloque(
                texto=texto,
                pagina=pagina or 1,
                seccion=seccion_actual,
                seccion_path=list(seccion_path),
                bbox=bbox,
                es_encabezado=es_encabezado,
            )
        )

    num_paginas = getattr(getattr(doc, "pages", None), "__len__", lambda: 0)()
    if not num_paginas:
        num_paginas = max(paginas_vistas) if paginas_vistas else 0
    return bloques, num_paginas


def _docling_pagina(item) -> int | None:
    """Extrae el número de página 1-based de un ítem de Docling (tolerante a versiones)."""
    prov = getattr(item, "prov", None)
    if prov:
        first = prov[0]
        pno = getattr(first, "page_no", None)
        if pno is not None:
            return int(pno)
    return None


def _docling_bbox(item, pagina: int | None) -> dict | None:
    """Extrae la bbox de un ítem de Docling como dict {x0,y0,x1,y1,page} (o None)."""
    prov = getattr(item, "prov", None)
    if not prov:
        return None
    bbox = getattr(prov[0], "bbox", None)
    if bbox is None:
        return None
    try:
        return {
            "x0": float(bbox.l),
            "y0": float(bbox.t),
            "x1": float(bbox.r),
            "y1": float(bbox.b),
            "page": pagina,
        }
    except (AttributeError, TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------
# PyMuPDF (respaldo)
# --------------------------------------------------------------------------------------
def _parse_pymupdf(data: bytes) -> tuple[list[Bloque], int]:
    """Parsea con PyMuPDF (fitz). Importa fitz de forma perezosa (extra `[rag]`).

    Extrae bloques de texto por página con su bbox; aplica una heurística simple para detectar
    encabezados (numeración de sección o títulos cortos en mayúsculas) y mantener `seccion`/`path`.
    """
    import fitz  # type: ignore  # PyMuPDF

    bloques: list[Bloque] = []
    seccion_actual: str | None = None
    seccion_path: list[str] = []

    with fitz.open(stream=data, filetype="pdf") as pdf:
        num_paginas = pdf.page_count
        for indice_pagina in range(num_paginas):
            page = pdf.load_page(indice_pagina)
            pagina = indice_pagina + 1  # 1-based
            datos = page.get_text("dict")
            for block in datos.get("blocks", []):
                if block.get("type", 0) != 0:  # 0 = bloque de texto (1 = imagen)
                    continue
                texto = _texto_de_bloque(block)
                if not texto.strip():
                    continue
                bbox = _bbox_de_bloque(block, pagina)
                es_encabezado = _es_encabezado(texto)
                if es_encabezado:
                    seccion_actual = texto.strip()
                    seccion_path = _actualizar_path(seccion_path, seccion_actual)
                bloques.append(
                    Bloque(
                        texto=texto,
                        pagina=pagina,
                        seccion=seccion_actual,
                        seccion_path=list(seccion_path),
                        bbox=bbox,
                        es_encabezado=es_encabezado,
                    )
                )
    return bloques, num_paginas


def _texto_de_bloque(block: dict) -> str:
    """Reconstruye el texto de un bloque de PyMuPDF (líneas → spans), normalizando espacios."""
    lineas: list[str] = []
    for line in block.get("lines", []):
        spans = [span.get("text", "") for span in line.get("spans", [])]
        linea = "".join(spans).strip()
        if linea:
            lineas.append(linea)
    return "\n".join(lineas).strip()


def _bbox_de_bloque(block: dict, pagina: int) -> dict | None:
    """Convierte la bbox de PyMuPDF (tupla x0,y0,x1,y1) a dict, añadiendo la página."""
    caja = block.get("bbox")
    if not caja or len(caja) != 4:
        return None
    x0, y0, x1, y1 = caja
    return {"x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1), "page": pagina}


def _es_encabezado(texto: str) -> bool:
    """Heurística de encabezado: numeración de sección o título corto sin punto final."""
    t = texto.strip()
    if not t or len(t) > 120:
        return False
    if _RE_NUM_SECCION.match(t):
        return True
    # Título corto (pocas palabras) sin terminar en punto y con mayúscula inicial.
    palabras = t.split()
    if len(palabras) <= 12 and not t.endswith(".") and t[:1].isupper():
        # Evita confundir una frase normal: exige que no sea claramente prosa larga.
        return t.isupper() or len(palabras) <= 8
    return False


def _actualizar_path(path_actual: list[str], encabezado: str) -> list[str]:
    """Actualiza la jerarquía de secciones a partir de la numeración del encabezado.

    Si el encabezado tiene numeración (p.ej. "3.2 Datos"), el nivel = nº de componentes; se recorta
    el path a ese nivel y se reemplaza el último. Sin numeración, se trata como sección de nivel 1.
    """
    m = _RE_NUM_SECCION.match(encabezado)
    if m:
        nivel = len(m.group(1).split("."))
        nuevo = path_actual[: nivel - 1]
        nuevo.append(encabezado.strip())
        return nuevo
    return [encabezado.strip()]
