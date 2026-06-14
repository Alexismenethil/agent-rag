"""Recuperación vectorial (kNN) sobre pgvector — V1.

Dado un `doc_id` y la pregunta del usuario, embebe la pregunta con el MISMO embedder de la
ingesta (`app.ingestion.embedder`) y recupera los `top_k` chunks más cercanos por distancia
coseno (operador `<=>`), acotando la búsqueda al documento.

V1 = SOLO búsqueda vectorial (sin BM25/RRF/reranker; eso llega en V2, ver docs/PLAN.md).

Notas de implementación:
- Se hace `SET LOCAL hnsw.ef_search = settings.hnsw_ef_search` dentro de la misma transacción
  para afinar el recall del índice HNSW.
- La distancia coseno se expone como `score` (1 - distancia) para que mayor sea mejor; el orden
  real lo da `ORDER BY embedding <=> :q`.
- El embedder de ingesta es propiedad del agente de ingesta y aún puede no existir cuando se
  importa este módulo; por eso se importa de forma PEREZOSA (dentro de la función) y se adapta a
  varios nombres de API convencionales.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


@dataclass(slots=True)
class ChunkRecuperado:
    """Un chunk recuperado por similitud vectorial, con sus metadatos de posición.

    Estos campos alimentan tanto el prompt de grounding (numerados `[1..k]`) como el localizador
    de span de cita (`app.grounding.citations`), que necesita `texto` y los offsets/página.
    """

    chunk_id: UUID
    doc_id: UUID
    chunk_index: int
    texto: str
    pagina: int
    pagina_fin: int
    seccion: str | None
    seccion_path: list[str] | None
    offset_inicio: int
    offset_fin: int
    score: float  # 1 - distancia_coseno (mayor = más similar). Provisional/orientativo.


def embed_pregunta(pregunta: str) -> list[float]:
    """Embebe la pregunta con el MISMO embedder de la ingesta (`app.ingestion.embedder`).

    El módulo de ingesta es propiedad del agente de ingesta; se importa perezosamente para no
    acoplar el arranque de la API a su existencia. Se aceptan varias formas convencionales de la
    API del embedder (función o instancia), priorizando la dedicada a *queries* cuando exista
    (algunos embedders, como BGE-m3, aplican una instrucción distinta a consultas vs. pasajes).

    Returns:
        El vector de la pregunta como `list[float]` de dimensión `settings.embedding_dim`.

    Raises:
        RuntimeError: si el módulo `app.ingestion.embedder` no está disponible todavía o no
        expone una API reconocible.
    """
    try:
        from app.ingestion import embedder as _embedder  # import perezoso (propiedad de ingesta)
    except Exception as exc:  # noqa: BLE001 - el módulo aún puede no existir en algunos entornos
        raise RuntimeError(
            "No se pudo importar 'app.ingestion.embedder' (¿ingesta aún no integrada?). "
            "La recuperación vectorial necesita el MISMO embedder que la ingesta."
        ) from exc

    vector = _invocar_embedder(_embedder, pregunta)
    return _normalizar_vector(vector)


def _invocar_embedder(modulo: object, pregunta: str) -> object:
    """Localiza e invoca el punto de entrada del embedder, tolerando varios nombres de API.

    Orden de preferencia:
    1. Funciones que vectorizan un solo texto: `embed_texto` (API real de ingesta), `embed_query`,
       `encode_query`, `embed_text`, `embed`, `encode`.
    2. Funciones por lotes: `embed_textos` (API real de ingesta), `embed_queries`, `embed_texts`
       (reciben `[pregunta]` y se toma el primer vector).
    3. Una instancia/objeto exportado (`embedder`/`default_embedder`) con esos mismos métodos.

    La API canónica del módulo de ingesta es `embed_texto`/`embed_textos` (ver
    `app/ingestion/embedder.py`); el resto de nombres son respaldos por robustez.
    """
    candidatos_singular = (
        "embed_texto",
        "embed_query",
        "encode_query",
        "embed_text",
        "embed",
        "encode",
    )
    candidatos_plural = ("embed_textos", "embed_queries", "embed_texts")

    # 1-2) Funciones de módulo.
    for nombre in candidatos_singular:
        fn = getattr(modulo, nombre, None)
        if callable(fn):
            return fn(pregunta)
    for nombre in candidatos_plural:
        fn = getattr(modulo, nombre, None)
        if callable(fn):
            return _primero(fn([pregunta]))

    # 3) Objeto/instancia exportada por el módulo.
    for attr in ("embedder", "default_embedder", "Embedder"):
        obj = getattr(modulo, attr, None)
        if obj is None:
            continue
        instancia = obj() if isinstance(obj, type) else obj
        for nombre in candidatos_singular:
            fn = getattr(instancia, nombre, None)
            if callable(fn):
                return fn(pregunta)
        for nombre in candidatos_plural:
            fn = getattr(instancia, nombre, None)
            if callable(fn):
                return _primero(fn([pregunta]))

    raise RuntimeError(
        "El módulo 'app.ingestion.embedder' no expone una API reconocible "
        "(se buscó embed_query/embed_text/embed/encode o un objeto 'embedder')."
    )


def _primero(resultado: object) -> object:
    """Devuelve el primer elemento de un resultado por lotes (lista de vectores)."""
    try:
        return resultado[0]  # type: ignore[index]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("El embedder por lotes no devolvió una secuencia indexable.") from exc


def _normalizar_vector(vector: object) -> list[float]:
    """Convierte el vector devuelto por el embedder a `list[float]` y valida su dimensión."""
    # Soporta numpy arrays/tensores (vía .tolist()) y secuencias normales.
    if hasattr(vector, "tolist"):
        vector = vector.tolist()  # type: ignore[assignment]
    try:
        valores = [float(x) for x in vector]  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "El embedder devolvió un valor no convertible a list[float]."
        ) from exc
    if len(valores) != settings.embedding_dim:
        raise RuntimeError(
            f"Dimensión del embedding inesperada: {len(valores)} "
            f"(se esperaba {settings.embedding_dim})."
        )
    return valores


async def buscar_chunks(
    session: AsyncSession,
    doc_id: UUID,
    pregunta: str,
    top_k: int,
) -> list[ChunkRecuperado]:
    """Recupera los `top_k` chunks más similares a la pregunta dentro de `doc_id`.

    Embebe la pregunta (mismo embedder que ingesta) y consulta pgvector por distancia coseno
    (`<=>`), afinando `hnsw.ef_search` para esta transacción. Solo considera chunks con embedding
    no nulo (los que ya pasaron la fase `embedding`/`indexing`).

    Args:
        session: sesión async de SQLAlchemy.
        doc_id: documento sobre el que se busca.
        pregunta: texto de la pregunta del usuario.
        top_k: número de chunks a devolver.

    Returns:
        Lista de `ChunkRecuperado` ordenada por similitud descendente (más similar primero).
    """
    q_embedding = embed_pregunta(pregunta)
    return await buscar_chunks_con_embedding(session, doc_id, q_embedding, top_k)


async def buscar_chunks_con_embedding(
    session: AsyncSession,
    doc_id: UUID,
    q_embedding: list[float],
    top_k: int,
) -> list[ChunkRecuperado]:
    """Variante que recibe el embedding ya calculado (útil para tests y reuso).

    El embedding se serializa al formato literal de pgvector (`[v1,v2,...]`) y se castea a
    `vector` en SQL, evitando depender del binding de tipos del driver.
    """
    # Afina el recall del índice HNSW solo para esta transacción.
    # OJO: `SET` no admite parámetros ($1), así que se usa set_config(clave, valor_texto, is_local=true),
    # que es equivalente a `SET LOCAL` pero sí acepta bind parameters.
    await session.execute(
        text("SELECT set_config('hnsw.ef_search', :ef, true)"),
        {"ef": str(int(settings.hnsw_ef_search))},
    )

    vector_literal = "[" + ",".join(repr(float(x)) for x in q_embedding) + "]"

    sql = text(
        """
        SELECT
            c.id            AS chunk_id,
            c.doc_id        AS doc_id,
            c.chunk_index   AS chunk_index,
            c.texto         AS texto,
            c.pagina        AS pagina,
            c.pagina_fin    AS pagina_fin,
            c.seccion       AS seccion,
            c.seccion_path  AS seccion_path,
            c.offset_inicio AS offset_inicio,
            c.offset_fin    AS offset_fin,
            (c.embedding <=> CAST(:q AS vector)) AS distancia
        FROM chunks c
        WHERE c.doc_id = :doc_id
          AND c.embedding IS NOT NULL
        ORDER BY c.embedding <=> CAST(:q AS vector)
        LIMIT :top_k
        """
    )

    result = await session.execute(
        sql, {"q": vector_literal, "doc_id": str(doc_id), "top_k": int(top_k)}
    )
    filas = result.mappings().all()

    recuperados: list[ChunkRecuperado] = []
    for fila in filas:
        distancia = float(fila["distancia"])
        recuperados.append(
            ChunkRecuperado(
                chunk_id=fila["chunk_id"],
                doc_id=fila["doc_id"],
                chunk_index=fila["chunk_index"],
                texto=fila["texto"],
                pagina=fila["pagina"],
                pagina_fin=fila["pagina_fin"],
                seccion=fila["seccion"],
                seccion_path=fila["seccion_path"],
                offset_inicio=fila["offset_inicio"],
                offset_fin=fila["offset_fin"],
                score=1.0 - distancia,
            )
        )
    return recuperados
