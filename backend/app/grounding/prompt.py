"""Prompts de grounding — V1: SOLO modo estricto.

El modo estricto obliga al modelo a responder ÚNICAMENTE con la información de los chunks
recuperados, numerados `[1..k]`, y a marcar cada afirmación con el `[n]` del chunk que la
respalda. Si la respuesta no está en el contexto, debe decir EXACTAMENTE la frase de "no
encontrado" y no inventar.

El modo ampliado (información extra etiquetada aparte) llega en V2; aquí no se implementa.

Decisiones relacionadas: docs/DECISIONES.md ADR-003 (citas con marcadores `[n]`; el backend
calcula los offsets, el LLM nunca los inventa) y ADR-004 (contrato `/query`).
"""

from __future__ import annotations

from app.retrieval.vector import ChunkRecuperado

# Frase EXACTA que debe emitir el modelo cuando la respuesta no está en el contexto.
# El localizador de citas y la heurística de groundedness dependen de esta cadena literal.
RESPUESTA_NO_ENCONTRADO = "No encontrado en el documento."


SYSTEM_PROMPT_ESTRICTO = """\
Eres un asistente que responde preguntas SOLO con la información de los fragmentos de un \
documento que se te entregan a continuación. Trabajas en modo ESTRICTO.

Reglas obligatorias (no las violes):
1. Responde únicamente con lo que dicen los fragmentos numerados [1], [2], … No uses \
conocimiento externo ni inventes datos que no estén en los fragmentos.
2. Cada afirmación de tu respuesta debe terminar con el marcador [n] del fragmento que la \
respalda (por ejemplo: "La fotosíntesis ocurre en los cloroplastos [2]."). Si una afirmación \
se apoya en varios fragmentos, pon todos sus marcadores ([1][3]).
3. Usa el texto de los fragmentos lo más literal posible al redactar la afirmación que vas a \
citar, para que el marcador apunte a un fragmento donde esa afirmación aparece textualmente.
4. Si la respuesta NO está contenida en los fragmentos, responde EXACTAMENTE con esta frase y \
nada más: "{frase_no_encontrado}"
5. No incluyas offsets, números de página ni metadatos de posición en tu respuesta: solo el \
texto y los marcadores [n]. El sistema calcula las posiciones por su cuenta.
6. Responde en español, de forma clara y concisa.
"""


def construir_system_prompt(modo: str = "estricto") -> str:
    """Devuelve el system prompt según el modo. En V1 solo se soporta `estricto`.

    Args:
        modo: `"estricto"` (único soportado en V1). Cualquier otro valor cae a estricto con la
            misma política de grounding (el modo ampliado se añade en V2).
    """
    # En V1 ignoramos otros modos y siempre aplicamos la política estricta.
    return SYSTEM_PROMPT_ESTRICTO.format(frase_no_encontrado=RESPUESTA_NO_ENCONTRADO)


def construir_contexto(chunks: list[ChunkRecuperado]) -> str:
    """Renderiza los chunks recuperados como contexto numerado `[1..k]` para el LLM.

    El número `[n]` corresponde a la POSICIÓN (1-indexada) del chunk en la lista recuperada; es
    el mismo índice que luego resuelve el localizador de citas (`citations.resolver_citas`).
    Se incluyen página y sección como ayuda al modelo, pero se le instruye no copiarlas en la
    respuesta (el backend es quien produce los metadatos de la cita).
    """
    bloques: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        encabezado = f"[{i}]"
        ubic = f"(página {ch.pagina}"
        if ch.seccion:
            ubic += f", sección: {ch.seccion}"
        ubic += ")"
        bloques.append(f"{encabezado} {ubic}\n{ch.texto}")
    return "\n\n".join(bloques)


def construir_mensaje_usuario(pregunta: str, chunks: list[ChunkRecuperado]) -> str:
    """Arma el contenido del turno `user`: contexto numerado + la pregunta.

    El contexto va primero (fragmentos `[1..k]`) y luego la pregunta, de modo que el modelo
    razone solo sobre lo entregado.
    """
    contexto = construir_contexto(chunks)
    return (
        "Fragmentos del documento (úsalos como única fuente):\n\n"
        f"{contexto}\n\n"
        "----\n"
        f"Pregunta: {pregunta}\n\n"
        "Responde siguiendo las reglas del modo estricto, marcando cada afirmación con su [n]."
    )
