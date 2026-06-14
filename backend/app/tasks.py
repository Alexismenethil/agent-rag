"""Tareas en segundo plano (BackgroundTasks de FastAPI).

V1 ejecuta la ingesta de un documento de forma asíncrona tras responder 202 al cliente. Se usa
`BackgroundTasks` (no Celery/RQ) por simplicidad del MVP: el trabajo corre en el mismo proceso, en
el event loop, y delega las etapas pesadas (parseo/embeddings) a hilos (`asyncio.to_thread`).

Este módulo es un envoltorio delgado sobre `app.ingestion.pipeline` para que el router no dependa
directamente del pipeline y para tener un único punto de entrada de las tareas de fondo.
"""

from __future__ import annotations

import logging
import uuid

from app.ingestion.pipeline import ingerir_documento

logger = logging.getLogger("uvicorn.error")


async def tarea_ingesta(doc_id: uuid.UUID, data: bytes) -> None:
    """Punto de entrada de la ingesta en segundo plano (lo agenda el router con `add_task`).

    Captura cualquier excepción para que un fallo de la tarea de fondo no quede sin registrar; el
    pipeline ya marca `documents.status='failed'` ante errores, así que aquí solo se loguea.
    """
    try:
        await ingerir_documento(doc_id, data)
    except Exception:  # noqa: BLE001 - una tarea de fondo nunca debe propagar sin loguear
        logger.exception("Fallo no controlado en la tarea de ingesta de %s", doc_id)
