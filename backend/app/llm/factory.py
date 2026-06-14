"""Fábrica de proveedores de LLM: selecciona la implementación según `settings.llm_provider`.

Punto único de selección para que el router (y los tests) no dependan de un proveedor concreto.
La instanciación es barata: ni Anthropic ni Ollama cargan nada pesado en el constructor (el
cliente HTTP se crea perezosamente en la primera llamada a `complete`).

Valores de `LLM_PROVIDER` (.env):
- `anthropic` (por defecto) → `ClaudeProvider`.
- `local` o `ollama`        → `OllamaProvider` (servidor OpenAI-compatible local).
"""

from __future__ import annotations

from app.config import settings
from app.llm.base import LLMProvider

# Alias aceptados para el proveedor local.
_PROVEEDORES_LOCALES = {"local", "ollama"}


def get_provider() -> LLMProvider:
    """Devuelve la instancia del proveedor de LLM según `settings.llm_provider`.

    Por defecto (o ante un valor desconocido) usa Anthropic, que es el proveedor de V1.
    """
    proveedor = (settings.llm_provider or "").strip().lower()

    if proveedor in _PROVEEDORES_LOCALES:
        # Import perezoso para no exigir el módulo local cuando se usa Anthropic.
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider()

    from app.llm.anthropic_provider import get_default_provider

    return get_default_provider()
