.PHONY: help setup up down down-volumes logs db-shell migrate revision models eval openapi lint fmt test clean

help:                ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:               ## Copia .env.example -> .env e instala hooks
	cp -n .env.example .env || true
	pre-commit install || true

up:                  ## Levanta toda la pila (db + backend + frontend)
	docker compose up --build -d

down:                ## Detiene la pila (conserva datos)
	docker compose down

down-volumes:        ## Detiene y BORRA la base de datos (pgdata)
	docker compose down -v

logs:                ## Sigue los logs de todos los servicios
	docker compose logs -f

db-shell:            ## psql contra la base de datos de desarrollo
	docker compose exec db psql -U $${POSTGRES_USER:-rag} -d $${POSTGRES_DB:-rag}

migrate:             ## Aplica migraciones Alembic (DDL pgvector + HNSW)
	docker compose exec backend alembic upgrade head

revision:            ## Crea una migración nueva:  make revision m="mensaje"
	docker compose exec backend alembic revision -m "$(m)"

models:              ## Descarga pesos (BGE-m3, reranker, Piper, whisper) a ./models
	bash scripts/download_models.sh

eval:                ## Ejecuta la evaluación RAGAS sobre el set gold
	docker compose exec backend python -m eval.run_eval --gold eval/datasets/gold_v1.jsonl

openapi:             ## Exporta el OpenAPI del backend y regenera los tipos del frontend
	docker compose exec backend python -m app.export_openapi > frontend/openapi.json
	cd frontend && npm run gen:types

lint:                ## ruff (backend) + eslint (frontend)
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint

fmt:                 ## Formatea backend y frontend
	docker compose exec backend ruff format .
	docker compose exec frontend npm run format

test:                ## Tests del backend
	docker compose exec backend pytest -q

clean:               ## Limpia caches locales
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
