# Decisiones canónicas (reconciliación)

El diseño se hizo por piezas independientes y una revisión de consistencia detectó ~20 conflictos
(nombres de tabla distintos, contratos de API divergentes, varias rutas para el set *gold*, driver de
BD inconsistente, etc.). Este documento fija **una sola fuente de verdad** para cada punto. Si una pieza
de código contradice esto, gana este documento.

## ADR-001 · Esquema de base de datos único

La fuente de verdad del esquema es el DDL de abajo (no hay un segundo modelo de tablas). Tablas:
`users`, `documents`, `chunks`, `conversations`, `messages`, **`message_citations`**, `learner_profile`,
`eval_runs`, `eval_results`.

- **Citas relacionales, no array.** Se usa la tabla `message_citations` (una fila por cita, con
  `snippet`/offsets/`texto_afirmacion` **denormalizados**). Se descarta `messages.cited_chunk_ids UUID[]`
  porque (a) no guarda offsets/snippet por cita, que el contrato `/query` sí devuelve, y (b) al borrar un
  documento las citas históricas sobreviven (`chunk_id → ON DELETE SET NULL`, snippet ya guardado).
- **Extensiones:** solo `vector` y `pg_trgm`. `gen_random_uuid()` es nativo en PostgreSQL 13+. Se evita
  `citext` (email → `TEXT` + índice único sobre `lower(email)`) y `uuid-ossp`.
- **`groundedness`** es el nombre del score de fidelidad *en runtime* (columna `messages.groundedness` y
  campo de respuesta). No se llama `faithfulness` para no confundirlo con la métrica de evaluación RAGAS.
- **Estados de ingesta:** `pending | parsing | chunking | embedding | indexing | ready | failed`
  (minúsculas, incluye `indexing`). El CHECK de `documents.status` y las etiquetas del frontend usan
  exactamente estas cadenas.

## ADR-002 · Convención de nombres

- **Tablas e identificadores técnicos en inglés:** `id`, `doc_id`, `chunk_id`, `owner_id`, `user_id`,
  `session_id`, `content_sha256`, `embedding`, `created_at`, `status`.
- **Metadatos de posición en español (no negociable, según contexto acordado):** `pagina`, `pagina_fin`,
  `seccion`, `seccion_path`, `offset_inicio`, `offset_fin`, `bbox`. Prohibido `page`/`section`/`char_start`/`char_end`.
- **Campos de contenido en español:** `texto`, `titulo`, `contenido`, `snippet`, `texto_afirmacion`.
- **Valores de enum de dominio en español:** `modo ∈ {estricto, ampliado}`, `nivel ∈
  {principiante, intermedio, avanzado}`. El frontend envía estas mismas cadenas (coinciden con los CHECK
  de SQL). Nada de `strict`/`extended`.

## ADR-003 · Sistema de offsets y algoritmo de cita

- Los `offset_inicio`/`offset_fin` son **offsets de carácter sobre el texto extraído del documento
  completo** (estables e independientes del render). `pagina` acompaña a cada chunk/cita para el visor.
- **En V1 un chunk no cruza páginas** (`pagina_fin = pagina`); el chunker corta en frontera de página.
- **Resaltado en el visor:** el frontend localiza el `snippet` (texto) dentro de la capa de texto de la
  `pagina` indicada (búsqueda de substring robusta), usando los offsets como pista secundaria. Esto evita
  fragilidad de coordenadas.
- **Localización del span (backend):** el LLM responde con marcadores `[n]`; el backend mapea `[n] →
  chunk_id` (el chunk que se le pasó como contexto n) y localiza el substring de la afirmación dentro de
  `chunks.texto` (match exacto → fuzzy) para producir `snippet` + offsets **a nivel de afirmación**. El LLM
  **nunca inventa offsets**; los calcula el backend.

## ADR-004 · Contrato de la API (canónico)

Campos de dominio en español. Identidad por header `X-User-Id` en MVP (V1-V3); login real en V4.

| Método | Ruta | Notas |
|--------|------|-------|
| `GET`  | `/health` | `{status, db}` |
| `POST` | `/documents` | multipart; → `202 {doc_id, status}` |
| `GET`  | `/documents` | lista del usuario |
| `GET`  | `/documents/{doc_id}` | `{doc_id, status, progress, num_paginas, error_msg}` |
| `GET`  | `/documents/{doc_id}/file` | `application/pdf` (para el visor) |
| `DELETE` | `/documents/{doc_id}` | cascada chunks; citas sobreviven (snippet denormalizado) |
| `POST` | `/query` | no-streaming (V1) |
| `POST` | `/query/stream` | SSE (V2): eventos `token`,`citation`,`extended_token`,`groundedness`,`done` |
| `GET`  | `/sessions` · `/sessions/{id}` | historial (detalle con mensajes embebidos) |
| `GET/PUT` | `/me/profile` · `/me/preferences` | eje B (V4) |
| `POST` | `/voice/stt` · `/voice/tts` | voz local (V3); `/voice/tts` acepta `{message_id}` o `{texto, voz, formato}` |
| `POST` | `/eval/run` | envoltorio delgado del CLI (opcional) |

**`POST /query` — request:**
```json
{ "doc_id": "uuid", "pregunta": "…", "modo": "estricto", "session_id": "uuid|null", "top_k": 8 }
```
**`POST /query` — response:**
```json
{
  "message_id": "uuid",
  "session_id": "uuid",
  "respuesta": "Texto con marcadores [1] [2] …",
  "citas": [
    { "marcador": 1, "chunk_id": "uuid", "doc_id": "uuid", "pagina": 4, "seccion": "3.2 Métodos",
      "offset_inicio": 1820, "offset_fin": 1944, "snippet": "…fragmento literal…",
      "texto_afirmacion": "…la afirmación que esta cita respalda…" }
  ],
  "informacion_ampliada": null,
  "groundedness": 0.92,
  "modelo": "claude-sonnet-4-6"
}
```
En **modo ampliado**, `informacion_ampliada` lleva el texto extra **etiquetado aparte**; nunca se mezcla
con `respuesta`. El campo `modelo` refleja el `model_id` real devuelto por el provider (no se hardcodea).

## ADR-005 · Infraestructura

- **Driver de BD:** la app FastAPI usa **asyncpg** → `DATABASE_URL=postgresql+asyncpg://…`. **Alembic**
  corre síncrono con **psycopg** → `ALEMBIC_DATABASE_URL=postgresql+psycopg://…`. Ambas en `.env` y `compose`.
- **Alembic** vive en `backend/alembic/` (`alembic.ini`, `alembic/env.py`, `alembic/versions/`).
  Migraciones por eje: `0001` extensiones · `0002` eje A (`documents`,`chunks`, HNSW, GIN) · `0003` puente
  (`conversations`,`messages`,`message_citations`) · `0004` eje B (`learner_profile`) · `0005` evaluación.
- **IDs de modelo Claude:** siempre desde `.env` (`LLM_MODEL`/`LLM_MODEL_FALLBACK`), nunca hardcodeados.
  Vigentes (ene-2026): `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`. Default del
  proyecto: **sonnet** (balance costo/calidad para tesis); opus para máxima calidad.
- **Gestores de paquetes:** backend `uv` + `pyproject.toml`; frontend `npm`.

## ADR-006 · Evaluación (una sola ubicación y un solo comando)

- Harness en `backend/eval/` (fuera de `app/`). Comando único: `python -m eval.run_eval`
  (alias `make eval`). Endpoint opcional `POST /eval/run` envuelve el mismo CLI.
- Set *gold* único: `backend/eval/datasets/gold_v1.jsonl` (versionado en git). La evidencia se identifica
  por **`doc_sha256 + chunk_index + offset_inicio + offset_fin`** (estable a recrear la BD), **no** por el
  UUID volátil de cada ingesta.
- **Tres umbrales, conceptos distintos:** runtime `GROUNDEDNESS_THRESHOLD=0.6` (degradar respuesta en
  vivo) ≠ gate RAGAS `faithfulness ≥ 0.85` ≠ gate `context_recall ≥ 0.80`. Documentar siempre cuál es cuál.
- **Protocolo de eje B (V4):** misma pregunta con dos perfiles distintos ⇒ `chunk_id`/offsets de las citas
  **idénticos**, solo cambia el texto de presentación.

## ADR-007 · Privacidad por diseño

PDFs subidos (`data/uploads/`) y pesos (`models/`) **nunca** entran a git. `.env` nunca se commitea (solo
`.env.example`). Logs sin texto íntegro de documentos (`ANONYMIZE_LOGS=true`). Borrado total a petición y
purga por `DATA_RETENTION_DAYS`. Detalle y encuadre para la tesis en [`privacy_ethics.md`](privacy_ethics.md).

---

## DDL canónico (resumen)

El DDL completo se materializa en las migraciones de `backend/alembic/versions/`. Estructura de tablas:

```
users(id, email[uniq lower], nombre, hashed_password, created_at, updated_at)

documents(id, owner_id→users(SET NULL), titulo, filename, content_sha256,
          mime_type, num_paginas, idioma, parser, embedding_model, storage_uri,
          status[CHECK pending..failed], error_msg, metadata jsonb, created_at, updated_at,
          UNIQUE(owner_id, content_sha256))

chunks(id, doc_id→documents(CASCADE), chunk_index, texto, embedding vector(1024),
       pagina, pagina_fin, seccion, seccion_path text[], offset_inicio, offset_fin, bbox jsonb,
       tsv tsvector GENERATED from to_tsvector('spanish', texto), token_count, metadata, created_at,
       UNIQUE(doc_id, chunk_index), CHECK(offset_fin >= offset_inicio))
  · idx HNSW (embedding vector_cosine_ops)  · idx GIN (tsv)  · idx (doc_id)  · idx (doc_id, pagina)

conversations(id, user_id→users(CASCADE), doc_id→documents(SET NULL), titulo,
              modo_default[CHECK], created_at, updated_at)

messages(id, conversation_id→conversations(CASCADE), role[CHECK], contenido, modo[CHECK],
         llm_model, groundedness real, retrieval_debug jsonb, prompt_tokens, completion_tokens,
         latency_ms, tts_audio_uri, created_at)

message_citations(id, message_id→messages(CASCADE), chunk_id→chunks(SET NULL), doc_id,
                  marcador, texto_afirmacion, pagina, seccion, offset_inicio, offset_fin, snippet)
  · idx (message_id)  · idx (chunk_id)   -- auditoría inversa "qué mensajes citaron este chunk"

learner_profile(user_id→users(CASCADE) PK, idioma_preferido, nivel[CHECK], modo_preferido[CHECK],
                voz_activada, voz_piper, estilo_respuesta, temas_interes text[],
                preferencias jsonb, memoria_resumen, updated_at)

eval_runs(id, nombre, git_sha, config jsonb, dataset, faithfulness, answer_relevancy,
          context_precision, context_recall, created_at)
eval_results(id, run_id→eval_runs(CASCADE), pregunta, ground_truth, answer, contexts jsonb,
             faithfulness, answer_relevancy, context_precision, context_recall, metadata, created_at)
```

## Búsqueda híbrida con RRF (SQL canónico, V2)

```sql
-- Parámetros que pasa el backend:
--   :q_embedding vector(1024), :q_text text, :doc_id uuid,
--   :k int = 60, :n_vec int = 30, :n_bm25 int = 30, :n_out int = 50
-- (Antes de la query vectorial: SET hnsw.ef_search = 100;)
WITH vec AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> :q_embedding) AS rank
  FROM chunks WHERE doc_id = :doc_id
  ORDER BY embedding <=> :q_embedding LIMIT :n_vec
),
bm25 AS (
  SELECT id, ROW_NUMBER() OVER (
           ORDER BY ts_rank_cd(tsv, websearch_to_tsquery('spanish', :q_text)) DESC) AS rank
  FROM chunks
  WHERE doc_id = :doc_id AND tsv @@ websearch_to_tsquery('spanish', :q_text)
  ORDER BY ts_rank_cd(tsv, websearch_to_tsquery('spanish', :q_text)) DESC LIMIT :n_bm25
),
fused AS (
  SELECT COALESCE(vec.id, bm25.id) AS chunk_id,
         COALESCE(1.0/(:k + vec.rank), 0.0) + COALESCE(1.0/(:k + bm25.rank), 0.0) AS rrf_score
  FROM vec FULL OUTER JOIN bm25 ON vec.id = bm25.id
)
SELECT c.id, c.doc_id, c.texto, c.pagina, c.pagina_fin, c.seccion, c.seccion_path,
       c.offset_inicio, c.offset_fin, c.bbox, f.rrf_score
FROM fused f JOIN chunks c ON c.id = f.chunk_id
ORDER BY f.rrf_score DESC LIMIT :n_out;   -- entra al reranker BGE-reranker-v2-m3 (top_n=8) y al LLM
```
