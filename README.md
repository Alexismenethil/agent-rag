# Agente RAG sobre documentos (explica-PDF con cita exacta)

Agente RAG que, dado un **PDF subido por el estudiante**, lo explica **citando el punto exacto**
del documento (página + sección + fragmento textual), con opción de **voz local**, que **guarda el
historial** y **aprende las preferencias** del estudiante.

Es un **proyecto antecedente** para dominar el ecosistema RAG antes de construir el *agente clínico
normativo* de la tesis *"Sistema móvil de cribado no invasivo de anemia infantil mediante Vision
Transformer sobre imágenes de conjuntiva y agente clínico normativo, Ayacucho 2026"*. Mismo motor RAG,
distinto corpus.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js (App Router) + TypeScript → `frontend/` |
| Backend  | FastAPI (Python 3.11+) → `backend/` |
| Base de datos | PostgreSQL 16 + **pgvector** (índice HNSW) |
| Embeddings | BGE-m3 (multilingüe, 1024 dims) |
| Reranker | BGE-reranker-v2-m3 (cross-encoder) |
| LLM | Claude (interfaz intercambiable → modelo local opcional) |
| Voz (local) | Piper (TTS) · faster-whisper (STT) |
| Evaluación | RAGAS (faithfulness, answer relevancy, context precision/recall) |

## Dos principios que NO se negocian

1. **Metadatos de posición guardados en la ingesta** (`pagina`, `seccion`, `offset_inicio`,
   `offset_fin`, `bbox`) → habilitan la **cita exacta**. Sin esto no hay cita verificable.
2. **Evaluación con RAGAS** sobre un set *gold* de 30-50 preguntas → una tesis necesita métricas.

Además, dos ejes **separados** en el diseño: **A) grounding** (RAG sobre el documento) y
**B) personalización** (perfil del estudiante). Y dos **modos** de respuesta: *estricto* (solo
documento + cita) y *ampliado* (info extra **etiquetada aparte**, nunca mezclada con lo citado).

## Arranque rápido (V0)

```bash
cp .env.example .env          # edita ANTHROPIC_API_KEY y POSTGRES_PASSWORD
docker compose up --build -d  # o: make up
make migrate                  # aplica migraciones Alembic (extensiones pgvector)

curl http://localhost:8000/health        # backend  -> {"status":"ok","db":"ok"}
open  http://localhost:3000              # frontend -> estado del backend en verde
docker compose exec db psql -U rag -d rag -c "\dx"   # confirma vector + pg_trgm
```

## Documentación

- [`docs/PLAN.md`](docs/PLAN.md) — **plan de implementación por versiones (V0 → V5)** con criterios de aceptación.
- [`docs/DECISIONES.md`](docs/DECISIONES.md) — decisiones canónicas (esquema, contratos de API, naming) y preguntas abiertas.
- [`docs/privacy_ethics.md`](docs/privacy_ethics.md) — privacidad y ética (base para el capítulo de la tesis).

## Estructura

```
.
├── backend/      # FastAPI + pipeline RAG + Alembic + evaluación
├── frontend/     # Next.js (subida, chat, visor con resaltado de citas, voz)
├── scripts/      # init_db.sql, descarga de modelos, seed
├── docs/         # plan, decisiones, ética
├── models/       # pesos descargados (NO versionado)
└── data/         # PDFs subidos, audio TTS (NO versionado)
```

> Estado actual: **V0 (scaffold)**. Lo siguiente es **V1 (MVP: subir 1 PDF → responder con cita exacta)**.
> Ver el roadmap completo en [`docs/PLAN.md`](docs/PLAN.md).
