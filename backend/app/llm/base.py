"""Interfaz intercambiable del proveedor de LLM.

El RAG depende de esta abstracción, no de un SDK concreto. La implementación por defecto
(`ClaudeProvider`) lee el modelo y la clave desde la config (`.env`) y NUNCA hardcodea el
`model_id`; el campo `model` del resultado refleja el id real devuelto por el proveedor.

V1 expone solo `complete` (no-streaming). El método `stream` llega en V2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

# Roles aceptados en el historial que se pasa al LLM.
LLMRole = Literal["user", "assistant"]


@dataclass(slots=True)
class LLMMessage:
    """Un turno de la conversación que se envía al LLM.

    El `system` prompt va aparte (parámetro de `complete`), no como mensaje con rol.
    """

    role: LLMRole
    content: str


@dataclass(slots=True)
class LLMUsage:
    """Consumo de tokens reportado por el proveedor."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class LLMResult:
    """Resultado de una llamada `complete`.

    - `text`: texto generado por el modelo.
    - `model`: `model_id` REAL devuelto por el proveedor (lo que se guarda en `messages.llm_model`
      y se expone como `modelo` en la respuesta de `/query`). No es el valor de config: es el de
      la respuesta.
    - `usage`: tokens de prompt/completion.
    - `stop_reason`: razón de parada reportada por el proveedor (opcional).
    """

    text: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    stop_reason: str | None = None


class LLMProvider(ABC):
    """Contrato del proveedor de LLM. Implementaciones: `ClaudeProvider` (default)."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float,
    ) -> LLMResult:
        """Genera una respuesta no-streaming.

        Args:
            system: prompt de sistema (instrucciones de grounding estricto, formato de citas `[n]`).
            messages: historial de turnos user/assistant (la pregunta actual es el último `user`).
            max_tokens: tope de tokens de salida.
            temperature: temperatura de muestreo.

        Returns:
            `LLMResult` con el texto, el `model_id` real y el consumo de tokens.
        """
        raise NotImplementedError
