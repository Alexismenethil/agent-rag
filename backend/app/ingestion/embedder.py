"""Embeddings BGE-m3 (1024 dims, normalizados) con sentence-transformers.

- Modelo: `settings.embedding_model` (por defecto `BAAI/bge-m3`), device `settings.embedding_device`.
- Dimensión: `settings.embedding_dim` (1024). Los vectores se normalizan (norma L2) para que la
  distancia coseno del índice HNSW (`vector_cosine_ops`) sea consistente.
- Carga PEREZOSA y SINGLETON del modelo: la primera llamada descarga/carga los pesos (varios cientos
  de MB) y las siguientes lo reutilizan. `sentence-transformers` se importa dentro de la función para
  no exigir el extra `[rag]` al importar el paquete ni al correr `compileall`.

La ingesta corre en un hilo de fondo (BackgroundTasks); `embed_textos` es síncrono (cómputo CPU/GPU).
"""

from __future__ import annotations

import threading

from app.config import settings

# Singleton perezoso del modelo + cerrojo para inicialización segura entre hilos.
_modelo = None
_lock = threading.Lock()


def _get_modelo():
    """Devuelve la instancia singleton del modelo de embeddings, cargándola la primera vez."""
    global _modelo
    if _modelo is None:
        with _lock:
            if _modelo is None:
                # Import perezoso: requiere el extra `[rag]` (sentence-transformers).
                from sentence_transformers import SentenceTransformer

                _modelo = SentenceTransformer(
                    settings.embedding_model,
                    device=settings.embedding_device,
                )
    return _modelo


def embed_textos(textos: list[str], *, batch_size: int = 16) -> list[list[float]]:
    """Calcula los embeddings normalizados de una lista de textos.

    Args:
        textos: textos a vectorizar (p.ej. el `texto` de cada chunk).
        batch_size: tamaño de lote para el encoder.

    Returns:
        Lista de vectores (cada uno de `settings.embedding_dim` floats, norma L2 = 1).
    """
    if not textos:
        return []
    modelo = _get_modelo()
    vectores = modelo.encode(
        textos,
        batch_size=batch_size,
        normalize_embeddings=True,  # norma L2: coherente con vector_cosine_ops
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    salida = [vec.tolist() for vec in vectores]
    _validar_dim(salida)
    return salida


def embed_texto(texto: str) -> list[float]:
    """Embedding normalizado de un solo texto (atajo para una consulta)."""
    return embed_textos([texto])[0]


def _validar_dim(vectores: list[list[float]]) -> None:
    """Verifica que la dimensión coincide con `settings.embedding_dim` (1024)."""
    if vectores and len(vectores[0]) != settings.embedding_dim:
        raise ValueError(
            f"Dimensión de embedding inesperada: {len(vectores[0])} "
            f"(esperado {settings.embedding_dim}). ¿Modelo distinto a BGE-m3?"
        )
