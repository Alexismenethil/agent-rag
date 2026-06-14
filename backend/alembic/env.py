"""Entorno de migraciones Alembic (modo síncrono con psycopg).

La URL se toma de ALEMBIC_DATABASE_URL (o de la config del proyecto como respaldo).
Los objetos específicos de pgvector (tipo vector, índice HNSW, columnas generadas tsv)
se escriben a mano con op.execute(...) en cada revisión: Alembic no los autogenera bien.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _db_url() -> str:
    url = os.getenv("ALEMBIC_DATABASE_URL")
    if url:
        return url
    try:
        from app.config import settings

        return settings.alembic_database_url
    except Exception:  # noqa: BLE001
        return "postgresql+psycopg://rag:rag_dev_pwd@localhost:5432/rag"


config.set_main_option("sqlalchemy.url", _db_url())

# Migraciones escritas a mano (sin autogenerate); no hace falta metadata todavía.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
