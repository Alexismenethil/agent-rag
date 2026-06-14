"""Configuración central leída desde variables de entorno (.env).

Una sola fuente de verdad para los parámetros del backend. Ver `.env.example` en la raíz.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # --- App ---
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 50
    dev_user_id: str = "00000000-0000-0000-0000-000000000001"

    # --- Base de datos ---
    # La app usa asyncpg; Alembic usa ALEMBIC_DATABASE_URL (psycopg). Ver docs/DECISIONES.md ADR-005.
    database_url: str = "postgresql+asyncpg://rag:rag_dev_pwd@localhost:5432/rag"
    alembic_database_url: str = "postgresql+psycopg://rag:rag_dev_pwd@localhost:5432/rag"

    # --- LLM (interfaz intercambiable) ---
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    llm_model_fallback: str = "claude-haiku-4-5-20251001"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.1
    # Modo local offline: servidor OpenAI-compatible (Ollama / vLLM). Desde el contenedor el
    # host es `host.docker.internal`, no `localhost`. La base ya termina en `/v1`.
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "qwen2.5:7b-instruct"

    # --- Embeddings / reranker (V1/V2) ---
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"
    embedding_dim: int = 1024
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_top_n: int = 8

    # --- Recuperación híbrida (V2) ---
    retrieval_top_k_vector: int = 30
    retrieval_top_k_bm25: int = 30
    rrf_k: int = 60
    hnsw_ef_search: int = 100

    # --- Verificación de fidelidad EN RUNTIME (≠ gate de evaluación RAGAS) ---
    groundedness_threshold: float = 0.6

    # --- Rutas ---
    data_dir: str = "./data"
    uploads_dir: str = "./data/uploads"
    tts_cache_dir: str = "./data/tts_cache"
    models_dir: str = "./models"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
