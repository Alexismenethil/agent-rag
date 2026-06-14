"""eje A: users (mínima), documents, chunks (+ HNSW, GIN, tsv generada)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14

DDL canónico: docs/DECISIONES.md (ADR-001 esquema, ADR-002 naming, DDL).
- Naming técnico en inglés; metadatos de posición y contenido en español.
- `documents.status` con CHECK de los 7 estados (minúsculas, incluye `indexing`).
- `chunks.embedding` es `vector(1024)`; índice HNSW (vector_cosine_ops).
- `chunks.tsv` es columna GENERATED (`to_tsvector('spanish', texto)`) STORED + índice GIN.
- El tipo `vector`, el índice HNSW y la columna generada se escriben con `op.execute` (Alembic no
  los autogenera bien). `gen_random_uuid()` es nativo en PG13+ (extensiones ya creadas en 0001).
- V1: un chunk no cruza páginas (`pagina_fin = pagina`); CHECK(offset_fin >= offset_inicio).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users (mínima para V1) ---
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=True),
        sa.Column("hashed_password", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
    )
    # Email único sin distinguir mayúsculas (en vez de citext): índice sobre lower(email).
    op.execute("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))")

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("titulo", sa.Text(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("num_paginas", sa.Integer(), nullable=True),
        sa.Column("idioma", sa.Text(), nullable=True),
        sa.Column("parser", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending','parsing','chunking','embedding','indexing','ready','failed')",
            name="ck_documents_status",
        ),
        sa.UniqueConstraint("owner_id", "content_sha256", name="uq_documents_owner_sha"),
    )

    # --- chunks ---
    # `embedding vector(1024)` y la columna generada `tsv` se crean con SQL crudo (op.execute).
    op.create_table(
        "chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        # embedding se añade luego como vector(1024) con op.execute
        sa.Column("pagina", sa.Integer(), nullable=False),
        sa.Column("pagina_fin", sa.Integer(), nullable=False),
        sa.Column("seccion", sa.Text(), nullable=True),
        sa.Column("seccion_path", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("offset_inicio", sa.Integer(), nullable=False),
        sa.Column("offset_fin", sa.Integer(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("offset_fin >= offset_inicio", name="ck_chunks_offsets"),
        sa.UniqueConstraint("doc_id", "chunk_index", name="uq_chunks_doc_index"),
    )

    # Columna de embedding: tipo vector(1024) (pgvector). Se añade con SQL crudo.
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1024)")

    # Columna tsv: GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED.
    op.execute(
        "ALTER TABLE chunks ADD COLUMN tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED"
    )

    # Índices.
    # HNSW sobre el embedding con distancia coseno (búsqueda vectorial V1; híbrida V2).
    op.execute(
        "CREATE INDEX idx_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    # GIN sobre la columna full-text (BM25 en V2).
    op.execute("CREATE INDEX idx_chunks_tsv ON chunks USING gin (tsv)")
    # Filtro por documento y por (documento, página).
    op.create_index("idx_chunks_doc_id", "chunks", ["doc_id"])
    op.create_index("idx_chunks_doc_pagina", "chunks", ["doc_id", "pagina"])


def downgrade() -> None:
    op.drop_index("idx_chunks_doc_pagina", table_name="chunks")
    op.drop_index("idx_chunks_doc_id", table_name="chunks")
    op.execute("DROP INDEX IF EXISTS idx_chunks_tsv")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")
    op.drop_table("users")
