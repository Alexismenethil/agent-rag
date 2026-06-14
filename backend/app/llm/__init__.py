"""Paquete del proveedor de LLM (interfaz intercambiable).

Reexporta el contrato y la fábrica para que el resto de la app importe desde `app.llm`:

    from app.llm import LLMProvider, LLMMessage, LLMResult, LLMUsage
    from app.llm import get_provider  # selecciona el proveedor según settings.llm_provider

La selección concreta del proveedor (`ClaudeProvider` / `OllamaProvider`) vive en
`app/llm/factory.py`; aquí solo se re-exporta para tener un punto de import estable.
"""

from app.llm.base import LLMMessage, LLMProvider, LLMResult, LLMRole, LLMUsage
from app.llm.factory import get_provider

__all__ = [
    "LLMProvider",
    "LLMMessage",
    "LLMResult",
    "LLMUsage",
    "LLMRole",
    "get_provider",
]
