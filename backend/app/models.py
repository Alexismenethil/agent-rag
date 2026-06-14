"""Modelos ORM (SQLAlchemy 2.0) de las tablas de V1.

Fuente de verdad del esquema: `docs/DECISIONES.md` (ADR-001 esquema, ADR-002 naming, DDL canónico).
El esquema físico lo materializan las migraciones Alembic (`0002_eje_a`, `0003_puente`); estos
modelos reflejan ese esquema para usarse desde la app (consultas, inserciones, relaciones).

Naming canónico (no negociable):
- Identificadores técnicos en inglés (`id`, `doc_id`, `owner_id`, `created_at`, `status`, …).
- Metadatos de posición y campos de contenido en español (`pagina`, `pagina_fin`, `seccion`,
  `seccion_path`, `offset_inicio`, `offset_fin`, `bbox`, `texto`, `titulo`, `snippet`, …).
- Enums de dominio en español (`modo ∈ {estricto, ampliado}`); estados de ingesta en minúsculas.

V1: un chunk NO cruza páginas (`pagina_fin == pagina`). Los offsets son de carácter sobre el texto
extraído del documento.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base

# Estados válidos de ingesta de un documento (minúsculas, incluye `indexing`). ADR-001.
DOCUMENT_STATUSES = ("pending", "parsing", "chunking", "embedding", "indexing", "ready", "failed")
# Modos de respuesta del dominio (en español). ADR-002. En V1 solo se usa `estricto`.
MODOS = ("estricto", "ampliado")
# Roles de un mensaje en una conversación.
MESSAGE_ROLES = ("user", "assistant", "system")


class User(Base):
    """Usuario. En V1 mínima: solo se usa el usuario de desarrollo (sin login real)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    documents: Mapped[list[Document]] = relationship(back_populates="owner")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="user")


class Document(Base):
    """Documento PDF subido por un usuario; se ingiere preservando posición."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("owner_id", "content_sha256", name="uq_documents_owner_sha"),
        CheckConstraint(
            "status IN ('pending','parsing','chunking','embedding','indexing','ready','failed')",
            name="ck_documents_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    titulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    num_paginas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idioma: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped[User | None] = relationship(back_populates="documents")
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class Chunk(Base):
    """Fragmento de un documento con su embedding y metadatos de posición.

    V1: `pagina_fin == pagina` (un chunk no cruza páginas). `offset_inicio`/`offset_fin` son
    offsets de carácter sobre el texto extraído del documento. `tsv` es una columna GENERATED
    (`to_tsvector('spanish', texto)`) gestionada por la BD: no se escribe desde la app, por eso
    no se modela aquí como columna mapeada.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("doc_id", "chunk_index", name="uq_chunks_doc_index"),
        CheckConstraint("offset_fin >= offset_inicio", name="ck_chunks_offsets"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    pagina: Mapped[int] = mapped_column(Integer, nullable=False)
    pagina_fin: Mapped[int] = mapped_column(Integer, nullable=False)
    seccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    seccion_path: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    offset_inicio: Mapped[int] = mapped_column(Integer, nullable=False)
    offset_fin: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="chunks")


class Conversation(Base):
    """Sesión de conversación de un usuario sobre un documento."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "modo_default IN ('estricto','ampliado')", name="ck_conversations_modo_default"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    titulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    modo_default: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'estricto'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    """Mensaje dentro de una conversación (pregunta del usuario o respuesta del asistente)."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system')", name="ck_messages_role"),
        CheckConstraint("modo IN ('estricto','ampliado')", name="ck_messages_modo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    modo: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    groundedness: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_debug: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list[MessageCitation]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MessageCitation.marcador",
    )


class MessageCitation(Base):
    """Cita relacional de un mensaje (una fila por cita).

    Snippet, offsets y `texto_afirmacion` están DENORMALIZADOS (ADR-001): al borrar un documento
    las citas históricas sobreviven (`chunk_id → ON DELETE SET NULL`, snippet ya guardado). Nunca
    se usa un array `cited_chunk_ids[]` en `messages`.
    """

    __tablename__ = "message_citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    doc_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    marcador: Mapped[int] = mapped_column(Integer, nullable=False)
    texto_afirmacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    pagina: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    offset_inicio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offset_fin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped[Message] = relationship(back_populates="citations")
