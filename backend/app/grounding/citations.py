"""Localizador de span de cita — V1 (docs/DECISIONES.md ADR-003).

Dado el texto de respuesta del LLM (con marcadores `[n]`) y los chunks recuperados, este módulo:

1. Parte la respuesta en AFIRMACIONES, cada una con sus marcadores `[n]`.
2. Mapea cada `[n]` → el chunk recuperado en la posición n (1-indexada).
3. Localiza el substring de la afirmación dentro de `chunks.texto` (match EXACTO → FUZZY) para
   producir `snippet` + `offset_inicio`/`offset_fin` A NIVEL DE AFIRMACIÓN.

Importante: el LLM NUNCA inventa offsets; los calcula el backend. Los offsets que se devuelven
son **de carácter sobre el texto extraído del documento completo**: como `chunks.offset_inicio`
es la posición del chunk dentro del documento, el offset de la afirmación = `chunk.offset_inicio`
+ (posición del match dentro de `chunk.texto`).

V1 usa solo la librería estándar (sin `rapidfuzz`): el fuzzy se hace con `difflib`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

from app.retrieval.vector import ChunkRecuperado

# Marcador de cita: uno o varios [n] consecutivos (admite espacios entre ellos).
_MARCADOR_RE = re.compile(r"\[(\d+)\]")
# Umbral mínimo de similitud (difflib ratio) para aceptar un match fuzzy.
_FUZZY_MIN_RATIO = 0.6
# Longitud máxima de ventana al barrer el chunk buscando el mejor match fuzzy.
_MAX_VENTANA = 600


@dataclass(slots=True)
class CitaResuelta:
    """Una cita ya localizada: liga una afirmación a un chunk con snippet + offsets.

    Estos campos se vuelcan luego en `message_citations` (denormalizados) y en el esquema `Cita`
    de la respuesta de `/query`.
    """

    marcador: int  # número [n] tal como aparece en la respuesta del LLM
    chunk_id: UUID | None
    doc_id: UUID | None
    pagina: int | None
    seccion: str | None
    texto_afirmacion: str
    snippet: str
    offset_inicio: int | None
    offset_fin: int | None
    localizado: bool  # True si se encontró el span (exacto o fuzzy) dentro del chunk


@dataclass(slots=True)
class _Afirmacion:
    """Fragmento de texto de la respuesta con los marcadores que lo respaldan."""

    texto: str
    marcadores: list[int]


def _partir_en_afirmaciones(respuesta: str) -> list[_Afirmacion]:
    """Divide la respuesta del LLM en afirmaciones, cada una con sus marcadores `[n]`.

    Estrategia: se trocea por marcadores. Cada vez que aparece uno o más `[n]`, el texto
    acumulado desde el marcador anterior es la afirmación que esos marcadores respaldan. El texto
    de la afirmación se limpia de los propios marcadores. Si quedara texto final sin marcador, se
    ignora para fines de cita (no hay a qué chunk ligarlo).
    """
    afirmaciones: list[_Afirmacion] = []
    ultimo_fin = 0
    i = 0
    n = len(respuesta)

    while i < n:
        m = _MARCADOR_RE.match(respuesta, i)
        if m:
            # Acumula todos los marcadores consecutivos (admite espacios entre ellos).
            marcadores: list[int] = []
            j = i
            while True:
                mm = _MARCADOR_RE.match(respuesta, j)
                if not mm:
                    break
                marcadores.append(int(mm.group(1)))
                j = mm.end()
                # Salta espacios/comas entre marcadores consecutivos.
                while j < n and respuesta[j] in " \t,":
                    j += 1
            texto_afirmacion = _limpiar_afirmacion(respuesta[ultimo_fin:i])
            if texto_afirmacion:
                afirmaciones.append(_Afirmacion(texto=texto_afirmacion, marcadores=marcadores))
            ultimo_fin = j
            i = j
        else:
            i += 1

    return afirmaciones


def _limpiar_afirmacion(texto: str) -> str:
    """Recorta una afirmación: quita marcadores residuales, espacios y puntuación de borde."""
    texto = _MARCADOR_RE.sub("", texto)
    # Si hay varias frases antes del marcador, nos quedamos con la última (la que el [n] cierra).
    partes = re.split(r"(?<=[.!?;:])\s+", texto.strip())
    candidato = partes[-1] if partes else texto
    return candidato.strip(" \t\n\r-—•·")


def _normalizar_afirmacion(texto: str) -> str:
    """Normaliza una afirmación para comparar texto generado vs. cita resuelta."""
    return re.sub(r"\s+", " ", _limpiar_afirmacion(texto)).casefold()


def _afirmaciones_visibles(respuesta: str) -> list[str]:
    """Extrae afirmaciones visibles de la respuesta, incluyendo las que no tienen marcador.

    Esta cuenta es deliberadamente sencilla para V1: divide por puntuación fuerte y saltos de
    línea, remueve marcadores `[n]` y descarta fragmentos vacíos. Sirve para penalizar respuestas
    que mezclan una afirmación citada con otra afirmación sin cita.
    """
    texto = _MARCADOR_RE.sub("", respuesta)
    partes = re.split(r"(?<=[.!?])\s+|\n+", texto)
    afirmaciones: list[str] = []
    for parte in partes:
        limpia = parte.strip(" \t\r\n-—•·")
        if limpia:
            afirmaciones.append(limpia)
    return afirmaciones


def _localizar_exacto(afirmacion: str, chunk_texto: str) -> tuple[int, int] | None:
    """Busca la afirmación literal dentro del texto del chunk (case-insensitive)."""
    if not afirmacion:
        return None
    idx = chunk_texto.find(afirmacion)
    if idx != -1:
        return idx, idx + len(afirmacion)
    # Reintento case-insensitive conservando la posición sobre el texto original.
    idx = chunk_texto.lower().find(afirmacion.lower())
    if idx != -1:
        return idx, idx + len(afirmacion)
    return None


def _normalizar_con_mapa(texto: str) -> tuple[str, list[int]]:
    """Normaliza para matching robusto y conserva mapa a índices del texto original.

    Colapsa espacios, quita diacríticos y usa `casefold()`. El mapa permite convertir un match
    sobre el texto normalizado al span original del chunk, preservando saltos de línea y escritura
    literal para el `snippet`.
    """
    normalizado: list[str] = []
    mapa: list[int] = []
    espacio_pendiente = False

    for idx, ch in enumerate(texto):
        if ch.isspace():
            if normalizado and not espacio_pendiente:
                normalizado.append(" ")
                mapa.append(idx)
                espacio_pendiente = True
            continue

        for base in unicodedata.normalize("NFD", ch.casefold()):
            if unicodedata.combining(base):
                continue
            normalizado.append(base)
            mapa.append(idx)
        espacio_pendiente = False

    if normalizado and normalizado[-1] == " ":
        normalizado.pop()
        mapa.pop()

    return "".join(normalizado), mapa


def _localizar_normalizado(afirmacion: str, chunk_texto: str) -> tuple[int, int] | None:
    """Busca la afirmación ignorando diferencias de acentos, mayúsculas y espacios."""
    if not afirmacion:
        return None

    af_norm, _ = _normalizar_con_mapa(afirmacion)
    chunk_norm, mapa = _normalizar_con_mapa(chunk_texto)
    if not af_norm or not chunk_norm:
        return None

    idx = chunk_norm.find(af_norm)
    if idx == -1:
        return None

    ini_original = mapa[idx]
    fin_original = mapa[idx + len(af_norm) - 1] + 1
    return ini_original, fin_original


def _localizar_fuzzy(afirmacion: str, chunk_texto: str) -> tuple[int, int, float] | None:
    """Localiza la mejor coincidencia aproximada de la afirmación dentro del chunk.

    Usa `difflib.SequenceMatcher.get_matching_blocks` para encontrar la región del chunk que
    mejor solapa con la afirmación, y luego ajusta una ventana de tamaño ~len(afirmacion)
    alrededor de ese bloque, eligiendo la de mayor `ratio`. Devuelve `(inicio, fin, ratio)` o
    `None` si no supera el umbral.
    """
    from difflib import SequenceMatcher

    if not afirmacion:
        return None

    afirmacion_l = afirmacion.lower()
    chunk_l = chunk_texto.lower()
    objetivo = min(len(afirmacion), _MAX_VENTANA)

    sm = SequenceMatcher(None, afirmacion_l, chunk_l, autojunk=False)
    bloques = sm.get_matching_blocks()
    # Centro aproximado del solape en el chunk (b = índice en el chunk).
    mejores = sorted(bloques, key=lambda blk: blk.size, reverse=True)
    centros = [blk.b for blk in mejores[:3] if blk.size > 0]
    if not centros:
        centros = [0]

    mejor: tuple[int, int, float] | None = None
    for centro in centros:
        inicio_base = max(0, centro - 5)
        for desplazamiento in (0, -objetivo // 2, -objetivo):
            inicio = max(0, min(len(chunk_texto) - 1, inicio_base + desplazamiento))
            fin = min(len(chunk_texto), inicio + objetivo)
            ventana = chunk_l[inicio:fin]
            ratio = SequenceMatcher(None, afirmacion_l, ventana, autojunk=False).ratio()
            if mejor is None or ratio > mejor[2]:
                mejor = (inicio, fin, ratio)

    if mejor and mejor[2] >= _FUZZY_MIN_RATIO:
        return mejor
    return None


def resolver_citas(
    respuesta: str,
    chunks: list[ChunkRecuperado],
) -> list[CitaResuelta]:
    """Resuelve los marcadores `[n]` de la respuesta a citas con snippet + offsets.

    Args:
        respuesta: texto generado por el LLM, con marcadores `[n]` (1-indexados sobre `chunks`).
        chunks: chunks recuperados en el MISMO orden con que se numeraron en el prompt.

    Returns:
        Lista de `CitaResuelta`. Si un marcador apunta fuera de rango (alucinado), se descarta.
        Si la afirmación no se localiza ni exacta ni fuzzy, se devuelve la cita con `localizado=
        False`, `snippet` = texto de la afirmación y offsets a nivel de chunk como respaldo (para
        no perder la cita), de modo que el visor pueda al menos ir a la página correcta.
    """
    afirmaciones = _partir_en_afirmaciones(respuesta)
    citas: list[CitaResuelta] = []

    for af in afirmaciones:
        for marcador in af.marcadores:
            # `[n]` es 1-indexado sobre la lista de chunks recuperados.
            if marcador < 1 or marcador > len(chunks):
                # Marcador alucinado / fuera de rango: se ignora (no hay chunk al que ligarlo).
                continue
            chunk = chunks[marcador - 1]
            cita = _resolver_una(marcador, af.texto, chunk)
            citas.append(cita)

    return citas


def _resolver_una(marcador: int, afirmacion: str, chunk: ChunkRecuperado) -> CitaResuelta:
    """Localiza una afirmación dentro de un chunk y arma la `CitaResuelta` con offsets globales."""
    base = chunk.offset_inicio  # offset del chunk dentro del documento completo

    exacto = _localizar_exacto(afirmacion, chunk.texto)
    if exacto is not None:
        ini_local, fin_local = exacto
        snippet = chunk.texto[ini_local:fin_local]
        return CitaResuelta(
            marcador=marcador,
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            pagina=chunk.pagina,
            seccion=chunk.seccion,
            texto_afirmacion=afirmacion,
            snippet=snippet,
            offset_inicio=base + ini_local,
            offset_fin=base + fin_local,
            localizado=True,
        )

    normalizado = _localizar_normalizado(afirmacion, chunk.texto)
    if normalizado is not None:
        ini_local, fin_local = normalizado
        snippet = chunk.texto[ini_local:fin_local]
        return CitaResuelta(
            marcador=marcador,
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            pagina=chunk.pagina,
            seccion=chunk.seccion,
            texto_afirmacion=afirmacion,
            snippet=snippet,
            offset_inicio=base + ini_local,
            offset_fin=base + fin_local,
            localizado=True,
        )

    fuzzy = _localizar_fuzzy(afirmacion, chunk.texto)
    if fuzzy is not None:
        ini_local, fin_local, _ratio = fuzzy
        snippet = chunk.texto[ini_local:fin_local].strip()
        # Reajusta offsets si el strip recortó espacios al inicio.
        recorte_izq = len(chunk.texto[ini_local:fin_local]) - len(
            chunk.texto[ini_local:fin_local].lstrip()
        )
        ini_local_adj = ini_local + recorte_izq
        fin_local_adj = ini_local_adj + len(snippet)
        return CitaResuelta(
            marcador=marcador,
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            pagina=chunk.pagina,
            seccion=chunk.seccion,
            texto_afirmacion=afirmacion,
            snippet=snippet,
            offset_inicio=base + ini_local_adj,
            offset_fin=base + fin_local_adj,
            localizado=True,
        )

    # No localizada: respaldo a nivel de chunk para no perder la cita (visor va a la página).
    return CitaResuelta(
        marcador=marcador,
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        pagina=chunk.pagina,
        seccion=chunk.seccion,
        texto_afirmacion=afirmacion,
        snippet=afirmacion,
        offset_inicio=chunk.offset_inicio,
        offset_fin=chunk.offset_fin,
        localizado=False,
    )


def calcular_groundedness(respuesta: str, citas: list[CitaResuelta]) -> float:
    """Heurística PROVISIONAL de groundedness en runtime (V1).

    Definición provisional (documentada como tal): proporción de afirmaciones visibles de la
    respuesta que tienen al menos una cita LOCALIZADA (exacta o fuzzy) dentro de su chunk. Esto
    penaliza explícitamente las afirmaciones sin marcador `[n]`, que violan el contrato de V1.

    Casos especiales:
    - Si la respuesta es exactamente la frase de "no encontrado", devuelve 1.0 (responder "no sé"
      cuando no hay evidencia es un comportamiento perfectamente fiel al grounding).
    - Si no hay ninguna cita localizada, devuelve 0.0 (respuesta sin respaldo verificable).

    La verificación real de fidelidad (faithfulness/RAGAS y el verificador de groundedness por
    afirmación) llega en V2; esta es solo una señal simple para V1.
    """
    from app.grounding.prompt import RESPUESTA_NO_ENCONTRADO

    if respuesta.strip() == RESPUESTA_NO_ENCONTRADO:
        return 1.0
    afirmaciones_totales = _afirmaciones_visibles(respuesta)
    if not afirmaciones_totales or not citas:
        return 0.0

    citas_localizadas = {
        (c.marcador, _normalizar_afirmacion(c.texto_afirmacion))
        for c in citas
        if c.localizado
    }
    afirmaciones_con_marcador = _partir_en_afirmaciones(respuesta)
    localizadas = 0
    for af in afirmaciones_con_marcador:
        af_norm = _normalizar_afirmacion(af.texto)
        if any((marcador, af_norm) in citas_localizadas for marcador in af.marcadores):
            localizadas += 1

    return min(localizadas, len(afirmaciones_totales)) / len(afirmaciones_totales)
