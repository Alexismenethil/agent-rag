"""init: extensiones PostgreSQL (vector, pg_trgm)

Revision ID: 0001
Revises:
Create Date: 2026-06-14

Solo extensiones. gen_random_uuid() es nativo en PostgreSQL 13+, así que no se necesita
pgcrypto/uuid-ossp. citext se evita (email = TEXT + índice único sobre lower(email)).
Las tablas de negocio llegan en 0002+ (ver docs/PLAN.md y docs/DECISIONES.md).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
