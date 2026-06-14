# Plan de implementación por versiones

Agente RAG sobre documentos (explica-PDF con cita exacta). Cada versión es un incremento
**demostrable y verificable** por un tesista trabajando solo. El orden ataca temprano el mayor
riesgo técnico (citas exactas con metadatos de posición) y deja algo funcionando de punta a punta
antes de añadir cada capa.

> Este plan es la síntesis de un diseño multi-agente (roadmap, backend, BD, evaluación, frontend,
> devops) reconciliado tras una revisión de consistencia. Las decisiones transversales que resuelven
> los conflictos entre piezas viven en [`DECISIONES.md`](DECISIONES.md) — léelo junto con este.

## Principios de la progresión

- **V0-V1** prueban el camino completo (subir PDF → responder con cita) con la pieza más simple posible.
- **V2** sube la calidad de recuperación y la **blinda con evaluación medible (RAGAS)**. Es la versión "tesis-defendible".
- **V3-V4** añaden los diferenciadores (voz y personalización), manteniendo **separados los dos ejes** (A: grounding, B: personalización).
- **V5** endurece para que sea reproducible y entregable.

**Convención de ramas/tags:** una rama por versión (`vN/...`), un tag `vN.0` al cumplir los criterios
de aceptación. No se pasa a `V(N+1)` hasta que la demo de `VN` pasa. Las *baselines* de evaluación se
etiquetan con la versión del roadmap (`baseline_v2`, `baseline_v3`…), no con un semver aparte.

---

## V0 — Scaffold del monorepo e infraestructura local  ✅ *(entregado)*

**Objetivo:** monorepo, base de datos con pgvector y servicios arrancando localmente con un
`docker compose up`, con un "hola mundo" extremo a extremo.

**Incluye:** estructura `backend/` + `frontend/`; `.gitignore` correcto; `docker-compose.yml` con
`pgvector/pgvector:pg16`; gestión de deps (`uv`/`pyproject.toml` en backend, `npm` en frontend);
Alembic inicializado con migración `0001` (extensiones `vector` + `pg_trgm`); `GET /health` que
verifica la conexión a Postgres; página raíz en Next.js que consume `/health`; `.env.example` completo;
`README.md`.

**Excluye:** toda lógica de ingesta/embeddings/RAG, autenticación, voz, personalización, reranker.

**Criterios de aceptación (demo):**
1. `docker compose up` levanta Postgres; `make migrate` corre sin error y `\dx` muestra `vector` y `pg_trgm`.
2. `curl localhost:8000/health` → `{"status":"ok","db":"ok"}`.
3. La página raíz del frontend muestra el estado del backend en verde.
4. `git status` limpio tras un build (ningún secreto, `node_modules`, `venv` ni modelo trackeado).

**Dependencias:** ninguna.

---

## V1 — MVP: un PDF, ingesta con posición, respuesta con cita exacta

**Objetivo:** el usuario sube un PDF, el sistema lo ingiere **preservando posición** y responde
preguntas citando **página + sección + fragmento textual exacto**.

**Incluye:**
- **Ingesta (offline):** parseo con **Docling** (PyMuPDF de respaldo) preservando página/posición →
  *chunking* por estructura **guardando metadatos** (`doc_id`, `pagina`, `seccion`, `offset_inicio`,
  `offset_fin`, `bbox` opcional) → embeddings **BGE-m3** → `pgvector` con índice **HNSW**.
- **Recuperación:** solo búsqueda **vectorial** (kNN sobre pgvector) → top-k chunks.
- **LLM detrás de interfaz intercambiable** (`LLMProvider`), implementación `ClaudeProvider` por
  defecto, con **grounding estricto**: el prompt obliga a responder solo con los chunks recuperados y
  a devolver citas con marcadores `[n]`.
- **Localización del span de cita:** el backend resuelve cada marcador `[n]` → `chunk_id` y localiza el
  substring exacto dentro de `chunks.texto` para producir `snippet` + `offset_inicio/offset_fin` **a
  nivel de afirmación** (ver algoritmo en `DECISIONES.md §Citas`).
- **Endpoints:** `POST /documents` (subida+ingesta), `GET /documents/{id}` (estado), `GET
  /documents/{id}/file` (sirve el PDF al visor), `POST /query` (no-streaming), `GET /sessions`,
  `GET /sessions/{id}`.
- **Identidad MVP:** header `X-User-Id` (un usuario fijo de desarrollo); sin login real todavía.
- **Frontend:** subir PDF, ver estado de ingesta, preguntar, ver respuesta con **citas clicables que
  resaltan página + fragmento** en un visor de PDF.
- **DB:** tablas `users` (mínima), `documents`, `chunks`, `conversations`, `messages`,
  `message_citations`.

**Excluye:** BM25/RRF, reranker, modo ampliado, verificación automática de groundedness, RAGAS, voz,
personalización, multiusuario real, streaming.

**Criterios de aceptación (demo):**
1. Subir un PDF real (20-40 págs.) deja `documents.status = 'ready'` y `chunks` con
   `pagina`/`offset_inicio`/`offset_fin` no nulos.
2. Una pregunta cuyo dato está en la página N devuelve una cita con `pagina == N` y el `snippet`
   aparece **literalmente** en esa página (verificable abriendo el PDF).
3. Una pregunta sin respuesta en el documento produce *"no encontrado en el documento"* en lugar de inventar.
4. El frontend resalta el fragmento citado al hacer clic en la cita.
5. Un PDF **sin capa de texto** (escaneado) se rechaza con `status='failed'`, `error_msg="needs_ocr"`
   (OCR queda para V5).

**Dependencias:** V0.

---

## V2 — Recuperación híbrida + reranker + modos + evaluación RAGAS

**Objetivo:** elevar calidad y fidelidad con recuperación híbrida y reranker, ofrecer modo
estricto/ampliado, y **medirlo** con RAGAS. Versión "tesis-defendible".

**Incluye:**
- **Recuperación híbrida:** vector (pgvector) + **BM25/full-text** de Postgres (`tsvector` +
  `ts_rank_cd` + `websearch_to_tsquery('spanish', …)`), **fusión RRF** (`k=60`). (SQL canónico en `DECISIONES.md`.)
- **Reranker** cross-encoder **BGE-reranker-v2-m3** sobre los candidatos fusionados → top-n final.
- **Verificación de fidelidad (groundedness) en runtime:** cada afirmación citada debe estar soportada
  por sus chunks; bajo `GROUNDEDNESS_THRESHOLD` (=0.6) se degrada a "no encontrado".
- **Dos modos de respuesta:**
  - *Estricto:* solo documento + cita.
  - *Ampliado:* información extra **etiquetada aparte** ("Fuera del documento"), nunca mezclada en la
    misma frase con lo citado.
- **Streaming:** `POST /query/stream` (SSE) con eventos `token`, `citation`, `extended_token`,
  `groundedness`, `done`. `LLMProvider` gana un método `stream()`.
- **Evaluación RAGAS:** set *gold* de **30-50 preguntas** (`backend/eval/datasets/gold_v1.jsonl`,
  evidencia identificada por `doc_sha256 + chunk_index + offsets`, estable a recrear la BD); runner
  `python -m eval.run_eval` que calcula `faithfulness`, `answer_relevancy`, `context_precision`,
  `context_recall` y vuelca reporte (tabla + JSON + filas en `eval_runs`/`eval_results`). Endpoint
  opcional `POST /eval/run` como envoltorio delgado del CLI.

**Criterios de aceptación (demo):**
1. Para 5 preguntas de prueba, híbrida + reranker devuelve el chunk correcto en top-3 con mejor ranking
   que V1 (comparación lado a lado).
2. En modo ampliado, la salida separa visiblemente "Del documento (citado)" de "Fuera del documento
   (no citado)"; ninguna frase mezcla ambas.
3. `make eval` produce un reporte con las 4 métricas RAGAS sobre las 30-50 preguntas, con
   **`faithfulness ≥ 0.85`** y **`context_recall ≥ 0.80`** (umbrales de gate; confírmalos con tu asesor).
4. La verificación de groundedness marca/rechaza una respuesta cuando se le inyecta una afirmación no soportada.

> **Tres umbrales distintos — no confundirlos:** (1) *runtime* groundedness `0.6` (degradar respuesta
> en vivo); (2) gate de evaluación RAGAS `faithfulness ≥ 0.85`; (3) gate `context_recall ≥ 0.80`.
> Son escalas/medidas diferentes (verificador propio vs. juez RAGAS). Ver `DECISIONES.md`.

**Dependencias:** V1.

---

## V3 — Voz local: TTS (Piper) + STT (faster-whisper)

**Objetivo:** preguntar por voz y escuchar la respuesta, con motores 100% locales y en español.

**Incluye:** `POST /voice/stt` (audio → texto con faster-whisper), `POST /voice/tts` (texto/`message_id`
→ audio con Piper, cacheado en `data/tts_cache/{message_id}.wav`, registrado en
`messages.tts_audio_uri`); UX en el frontend para grabar la pregunta y reproducir la respuesta.

**Excluye:** personalización, hardening de despliegue.

**Criterios de aceptación (demo):**
1. Una pregunta **hablada** se transcribe, se responde con citas y la respuesta se reproduce en audio
   inteligible — **todo sin red externa** (motores locales).
2. El audio TTS se cachea por `message_id` y no se regenera al re-reproducir.

**Dependencias:** V2. *(V3 y V4 dependen de V2 pero son independientes entre sí: pueden hacerse en paralelo.)*

---

## V4 — Personalización: perfil/memoria del estudiante (eje B)

**Objetivo:** adaptar el **estilo y la presentación** a las preferencias del estudiante, **sin tocar el
grounding ni las citas**.

**Incluye:** tabla `learner_profile` (idioma, nivel, modo preferido, estilo, temas, `preferencias`
JSONB, `memoria_resumen`); endpoints `GET/PUT /me/profile`, `GET/PUT /me/preferences`; el perfil se
resume en 2-3 líneas que **solo modulan el prompt** del LLM (no la recuperación ni los embeddings);
login/identidad real (sustituye al `X-User-Id` de desarrollo) y aislamiento de historial por usuario.

**Criterios de aceptación (demo):**
1. Cambiar las preferencias **altera el estilo** de la respuesta pero deja **los mismos chunks y citas**
   (mismo `chunk_id`/offsets) — *protocolo de eje B:* misma pregunta + dos perfiles → citas idénticas,
   solo cambia el texto de presentación.
2. El historial queda aislado por usuario.

**Dependencias:** V2 (no requiere V3).

---

## V5 — Hardening: seguridad, observabilidad, Docker, despliegue

**Objetivo:** reproducible y entregable en máquina limpia.

**Incluye:** `docker-compose.prod.yml`; validación/límite de subidas (tamaño, tipo, PDF malicioso);
**OCR** para PDFs escaneados (cierra el caso excluido en V1); logging estructurado y trazas del pipeline
(qué chunks se recuperaron, scores RRF/reranker); suite de smoke tests + gate RAGAS reproducible en CI;
política de **retención/borrado** (`DELETE /documents/{id}` con cascada + purga por
`DATA_RETENTION_DAYS`); documentación de despliegue y guía "cómo cambiar a LLM local".

**Criterios de aceptación (demo):**
1. En máquina limpia, `docker compose -f docker-compose.prod.yml up` levanta todo y la demo completa
   (subir PDF → preguntar por voz → respuesta citada y personalizada) corre sin pasos manuales extra.
2. Una subida maliciosa/oversize se rechaza con error controlado; sin secretos en imágenes ni logs.
3. Los logs permiten reconstruir, para una pregunta dada, qué chunks se recuperaron y el score del reranker.
4. El gate RAGAS pasa los umbrales en el commit de entrega.

**Dependencias:** V1-V4.

---

## Tabla resumen

| Versión | Objetivo (1 frase) | Criterio de aceptación clave |
|---|---|---|
| **V0** | Monorepo + Postgres/pgvector + servicios arrancando localmente. | `compose up` + `make migrate`; `/health` verde; `vector`+`pg_trgm` activas; git limpio. |
| **V1** | Subir 1 PDF, ingesta con posición, responder citando página + fragmento exacto. | Cita con `pagina` correcto y `snippet` literal del PDF; sin respuesta → no inventa. |
| **V2** | Híbrida + reranker + modo estricto/ampliado + RAGAS. | `make eval`: 4 métricas, `faithfulness ≥ 0.85`; modo ampliado separa citado de no citado. |
| **V3** | Voz local: Piper (TTS) + faster-whisper (STT) en español. | Pregunta hablada → respondida con citas → respuesta hablada, sin red externa. |
| **V4** | Personalización del estilo, separada del grounding. | Cambiar preferencias altera estilo pero deja chunks/citas idénticos; historial por usuario. |
| **V5** | Hardening: seguridad, observabilidad, OCR, despliegue. | Demo completa en máquina limpia con compose prod; gate RAGAS pasa; logs reconstruyen recuperación. |

## Preguntas abiertas (decídelas con tu asesor antes de V2/V4)

- **Umbrales del gate RAGAS:** propuesta `faithfulness ≥ 0.85`, `context_recall ≥ 0.80`. Ajustar con el asesor.
- **Multiusuario en V4:** ¿identificación simple basta para la tesis o se requiere login real (email/OAuth)?
- **Corpus de demo:** ¿un PDF por usuario en V1-V2 o varios desde V1? (el esquema soporta varios; la UI mínima asume uno).
- **`bbox`:** ¿se requiere resaltado visual exacto sobre el render del PDF (necesita `bbox`) o basta con
  resaltar el fragmento textual por `snippet`/offsets? Impacta el esfuerzo de ingesta en V1.
