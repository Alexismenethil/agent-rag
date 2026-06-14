"""Implementación de `LLMProvider` con el SDK de Anthropic (Claude).

Es la implementación por defecto de la interfaz intercambiable (`app.llm.base.LLMProvider`).
Lee el modelo y la clave desde la config (`.env`), NUNCA hardcodea el `model_id`, y el campo
`model` del `LLMResult` refleja el id REAL devuelto por la respuesta de Anthropic (no el de config).

V1 expone solo `complete` (no-streaming). El streaming llega en V2.

Decisiones (docs/DECISIONES.md ADR-005):
- `settings.llm_model` es el modelo principal; `settings.llm_model_fallback` se intenta si el
  principal falla (p.ej. modelo no disponible / sobrecarga puntual).
- `max_tokens`/`temperature` los pasa el llamador (vienen de `settings.llm_max_tokens` /
  `settings.llm_temperature` en el router).
"""

from __future__ import annotations

import logging

from anthropic import APIError, APIStatusError, AsyncAnthropic

from app.config import settings
from app.llm.base import LLMMessage, LLMProvider, LLMResult, LLMUsage

logger = logging.getLogger("uvicorn.error")


class ClaudeProvider(LLMProvider):
    """Proveedor de LLM respaldado por Claude (Anthropic).

    El cliente se construye con `settings.anthropic_api_key`. Si la clave está vacía, el
    constructor no falla (para no romper el arranque de la app ni los imports), pero la primera
    llamada a `complete` lanzará un error claro.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        model_fallback: str | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.anthropic_api_key
        self._model = model or settings.llm_model
        self._model_fallback = (
            model_fallback if model_fallback is not None else settings.llm_model_fallback
        )
        # El cliente async se crea perezosamente para no exigir la clave en import-time.
        self._client: AsyncAnthropic | None = None

    def _get_client(self) -> AsyncAnthropic:
        if not self._api_key:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY en la configuración (.env). El proveedor Claude no "
                "puede llamar a la API sin una clave válida."
            )
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float,
    ) -> LLMResult:
        """Genera una respuesta no-streaming con Claude.

        Intenta primero `settings.llm_model`; si esa llamada falla con un error de la API y hay
        un modelo de respaldo distinto configurado, reintenta con el respaldo. Devuelve un
        `LLMResult` cuyo `model` es el id REAL que reporta Anthropic en la respuesta.
        """
        client = self._get_client()
        payload = [{"role": m.role, "content": m.content} for m in messages]

        modelos_a_intentar = [self._model]
        if self._model_fallback and self._model_fallback != self._model:
            modelos_a_intentar.append(self._model_fallback)

        ultimo_error: Exception | None = None
        for modelo in modelos_a_intentar:
            try:
                resp = await client.messages.create(
                    model=modelo,
                    system=system,
                    messages=payload,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return self._to_result(resp, modelo_solicitado=modelo)
            except (APIStatusError, APIError) as exc:  # noqa: PERF203 - reintento con fallback
                ultimo_error = exc
                logger.warning(
                    "Fallo al llamar a Claude con el modelo '%s' (%s). %s",
                    modelo,
                    type(exc).__name__,
                    "Reintentando con el modelo de respaldo."
                    if modelo != modelos_a_intentar[-1]
                    else "Sin más modelos de respaldo.",
                )

        # Si ningún modelo respondió, propagamos el último error con contexto.
        raise RuntimeError(
            "No se pudo obtener respuesta de Claude con ninguno de los modelos configurados "
            f"({modelos_a_intentar}): {ultimo_error}"
        ) from ultimo_error

    @staticmethod
    def _to_result(resp: object, modelo_solicitado: str) -> LLMResult:
        """Convierte la respuesta del SDK a `LLMResult` con el `model_id` REAL.

        El `model` se toma de `resp.model` (lo que devuelve Anthropic), no del valor solicitado;
        si por algún motivo no viniera, se cae al modelo solicitado como respaldo razonable.
        """
        # Texto: concatena los bloques de tipo "text" del contenido.
        partes: list[str] = []
        for bloque in getattr(resp, "content", []) or []:
            if getattr(bloque, "type", None) == "text":
                partes.append(getattr(bloque, "text", ""))
        texto = "".join(partes).strip()

        modelo_real = getattr(resp, "model", None) or modelo_solicitado

        usage_obj = getattr(resp, "usage", None)
        usage = LLMUsage(
            prompt_tokens=getattr(usage_obj, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage_obj, "output_tokens", 0) or 0,
        )

        return LLMResult(
            text=texto,
            model=modelo_real,
            usage=usage,
            stop_reason=getattr(resp, "stop_reason", None),
        )


def get_default_provider() -> LLMProvider:
    """Fábrica del proveedor por defecto (lee la config). Punto único para inyección/tests."""
    return ClaudeProvider()
