-- Se ejecuta una vez al crear el contenedor de Postgres (docker-entrypoint-initdb.d).
-- Habilita las extensiones. El esquema de tablas lo gestiona Alembic (make migrate).
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector: tipo vector + índice HNSW
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- apoyo a full-text / búsqueda léxica (BM25)
