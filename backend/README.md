# Backend — FastAPI + RAG

API y pipeline RAG del agente. Python 3.11+, SQLAlchemy 2.0 async (asyncpg), Alembic, pgvector.

## Estructura

```
backend/
├── pyproject.toml          # deps núcleo (V0/V1) + extras rag/voice/eval
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py              # URL desde ALEMBIC_DATABASE_URL (psycopg, síncrono)
│   └── versions/0001_init_extensions.py   # CREATE EXTENSION vector, pg_trgm
├── app/
│   ├── main.py             # FastAPI app + CORS + routers
│   ├── config.py           # settings desde .env (pydantic-settings)
│   ├── db.py               # engine async + get_session + ping
│   ├── deps.py             # get_current_user_id (X-User-Id en MVP)
│   ├── export_openapi.py   # `make openapi`
│   └── routers/
│       ├── health.py       # GET /health (implementado)
│       ├── documents.py    # subida/ingesta/servir PDF (stub → V1)
│       └── query.py        # POST /query con contrato de citas (stub → V1)
├── eval/                   # evaluación RAGAS (comando: python -m eval.run_eval) → V2
└── tests/
```

> Pendiente de crear en V1 (mantiene los dos ejes separados, ver docs/DECISIONES.md):
> `app/models/` (ORM), `app/schemas/`, `app/ingestion/` (Parser→Chunker→Embedder→Indexer),
> `app/retrieval/` (HybridRetriever→Reranker), `app/llm/` (LLMProvider intercambiable),
> `app/grounding/` (prompts estricto/ampliado + FaithfulnessChecker).

## Desarrollo

Con Docker (recomendado): desde la raíz del repo `make up && make migrate`.

Local sin Docker:
```bash
cd backend
uv pip install --system ".[dev]"      # núcleo + herramientas
# necesitas un Postgres con pgvector escuchando (ver docker-compose.yml o scripts/init_db.sql)
alembic upgrade head
uvicorn app.main:app --reload
pytest -q
```
