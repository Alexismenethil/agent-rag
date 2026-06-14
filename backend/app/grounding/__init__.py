"""Grounding del RAG — V1: SOLO modo estricto.

Reúne el prompt de grounding estricto (`prompt.py`) y el localizador de span de cita
(`citations.py`). El modo ampliado y el verificador de fidelidad por afirmación llegan en V2
(ver docs/PLAN.md y docs/DECISIONES.md ADR-003).

Imports convenientes desde `app.grounding`:

    from app.grounding import (
        construir_system_prompt, construir_mensaje_usuario, RESPUESTA_NO_ENCONTRADO,
        resolver_citas, calcular_groundedness, CitaResuelta,
    )
"""

from app.grounding.citations import CitaResuelta, calcular_groundedness, resolver_citas
from app.grounding.prompt import (
    RESPUESTA_NO_ENCONTRADO,
    construir_contexto,
    construir_mensaje_usuario,
    construir_system_prompt,
)

__all__ = [
    "RESPUESTA_NO_ENCONTRADO",
    "construir_system_prompt",
    "construir_mensaje_usuario",
    "construir_contexto",
    "resolver_citas",
    "calcular_groundedness",
    "CitaResuelta",
]
