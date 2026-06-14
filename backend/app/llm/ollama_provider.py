"""Implementación de `LLMProvider` para un servidor LLM local (Ollama).

Habla con la API OpenAI-compatible que expone Ollama (también vLLM, LM Studio, etc.):
`POST {LOCAL_LLM_BASE_URL}/chat/completions`. La base (`settings.local_llm_base_url`) ya termina
en `/v1`, así que la ruta final es `{base}/chat/completions`.

Decisiones:
- Se usa `httpx` (ya es dependencia del proyecto). NO se añade el paquete `openai`.
- Timeout amplio (120s) porque un modelo local en CPU puede tardar en la primera respuesta.
- El `model` del `LLMResult` refleja el id REAL devuelto por el servidor (`choices[0]`/`model`);
  si no viniera, se cae a `settings.local_llm_model` como respaldo razonable.
- Cualquier fallo de red/HTTP/parsing se propaga como `RuntimeError` con un mensaje claro; el
  router de `/query` ya lo convierte en un 502 limpio.

V1 expone solo `complete` (no-streaming). El streaming llega en V2.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.llm.base import LLMMessage, LLMProvider, LLMResult, LLMUsage

logger = logging.getLogger("uvicorn.error")

# Timeout amplio: un modelo local (especialmente en CPU) puede tardar bastante en responder.
_TIMEOUT_SEGUNDOS = 120.0


class OllamaProvider(LLMProvider):
    """Proveedor de LLM respaldado por un servidor local OpenAI-compatible (Ollama).

    No requiere API key. La URL base y el modelo se leen de la config (`.env`):
    `settings.local_llm_base_url` (debe terminar en `/v1`) y `settings.local_llm_model`.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        base = base_url if base_url is not None else settings.local_llm_base_url
        # Normaliza: quita la barra final para concatenar la ruta de forma predecible.
        self._base_url = base.rstrip("/")
        self._model = model or settings.local_llm_model

    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float,
    ) -> LLMResult:
        """Genera una respuesta no-streaming contra el servidor local.

        Arma el cuerpo en formato OpenAI Chat Completions: el `system` va como primer mensaje
        con rol `system`, seguido del historial user/assistant. Devuelve un `LLMResult` cuyo
        `model` es el id REAL que reporta el servidor.
        """
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            cuerpo = exc.response.text[:500] if exc.response is not None else ""
            logger.warning(
                "El servidor LLM local respondió con error HTTP %s en %s. %s",
                exc.response.status_code if exc.response is not None else "?",
                url,
                cuerpo,
            )
            raise RuntimeError(
                f"El servidor LLM local devolvió un error HTTP "
                f"{exc.response.status_code if exc.response is not None else '?'} en {url}. "
                f"Revisa que el modelo '{self._model}' exista en el servidor (ollama pull)."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Fallo de red al llamar al LLM local en %s: %s", url, exc)
            raise RuntimeError(
                f"No se pudo contactar al servidor LLM local en {url} ({type(exc).__name__}). "
                "Verifica LOCAL_LLM_BASE_URL (desde el contenedor el host es host.docker.internal, "
                "no localhost) y que el servidor Ollama esté arriba."
            ) from exc

        return self._to_result(data)

    def _to_result(self, data: object) -> LLMResult:
        """Convierte la respuesta OpenAI-compatible a `LLMResult`.

        Espera la forma estándar: `choices[0].message.content`, `model` y `usage` con
        `prompt_tokens`/`completion_tokens`. Es defensivo ante campos ausentes.
        """
        if not isinstance(data, dict):
            raise RuntimeError(
                "Respuesta inesperada del servidor LLM local: no es un objeto JSON."
            )

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(
                "El servidor LLM local no devolvió 'choices' en la respuesta."
            )

        mensaje = choices[0].get("message") if isinstance(choices[0], dict) else None
        texto = (mensaje.get("content") if isinstance(mensaje, dict) else None) or ""
        texto = texto.strip()

        modelo_real = data.get("model") or self._model

        usage_obj = data.get("usage") or {}
        usage = LLMUsage(
            prompt_tokens=usage_obj.get("prompt_tokens", 0) or 0,
            completion_tokens=usage_obj.get("completion_tokens", 0) or 0,
        )

        stop_reason = choices[0].get("finish_reason") if isinstance(choices[0], dict) else None

        return LLMResult(
            text=texto,
            model=modelo_real,
            usage=usage,
            stop_reason=stop_reason,
        )
