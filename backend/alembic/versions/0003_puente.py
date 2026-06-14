"""puente: conversations, messages, message_citations

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-14

DDL canónico: docs/DECISIONES.md (ADR-001 esquema, DDL).
- `conversations`: una sesión de un usuario sobre un documento (doc_id → SET NULL).
- `messages`: `groundedness REAL`, `llm_model`, `tts_audio_uri` nullable, tokens/latencia, etc.
- `message_citations`: citas RELACIONALES con snippet/offsets DENORMALIZADOS (nunca array
  cited_chunk_ids[]). `message_id → messages CASCADE`, `chunk_id → chunks ON DELETE SET NULL`
  para que las citas históricas sobrevivan al borrado del documento (snippet ya guardado).
- Índices (message_id) y (chunk_id) — este último para auditoría inversa "qué mensajes citaron
  este chunk".
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("titulo", sa.Text(), nullable=True),
        sa.Column(
            "modo_default", sa.Text(), nullable=False, server_default=sa.text("'estricto'")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "modo_default IN ('estricto','ampliado')", name="ck_conversations_modo_default"
        ),
    )
    op.create_index("idx_conversations_user_id", "conversations", ["user_id"])

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("modo", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.Text(), nullable=True),
        sa.Column("groundedness", sa.REAL(), nullable=True),
        sa.Column("retrieval_debug", postgresql.JSONB(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tts_audio_uri", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("role IN ('user','assistant','system')", name="ck_messages_role"),
        sa.CheckConstraint("modo IN ('estricto','ampliado')", name="ck_messages_modo"),
    )
    op.create_index("idx_messages_conversation_id", "messages", ["conversation_id"])

    # --- message_citations (citas relacionales, denormalizadas) ---
    op.create_table(
        "message_citations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("marcador", sa.Integer(), nullable=False),
        sa.Column("texto_afirmacion", sa.Text(), nullable=True),
        sa.Column("pagina", sa.Integer(), nullable=True),
        sa.Column("seccion", sa.Text(), nullable=True),
        sa.Column("offset_inicio", sa.Integer(), nullable=True),
        sa.Column("offset_fin", sa.Integer(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
    )
    op.create_index("idx_message_citations_message_id", "message_citations", ["message_id"])
    op.create_index("idx_message_citations_chunk_id", "message_citations", ["chunk_id"])


def downgrade() -> None:
    op.drop_index("idx_message_citations_chunk_id", table_name="message_citations")
    op.drop_index("idx_message_citations_message_id", table_name="message_citations")
    op.drop_table("message_citations")
    op.drop_index("idx_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("idx_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
