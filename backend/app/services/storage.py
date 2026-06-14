"""Almacenamiento del PDF original en disco.

El archivo subido se guarda en `settings.uploads_dir` con el nombre `{doc_id}.pdf`. El `storage_uri`
que se persiste en `documents.storage_uri` es la ruta absoluta del archivo guardado.

Privacidad (ADR-007): los PDFs viven bajo `data/uploads/` y NUNCA entran a git. Aquí solo se
gestiona el guardado/lectura/borrado del binario; el control de acceso por dueño lo hace el router.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from app.config import settings


def _uploads_dir() -> Path:
    """Carpeta de subidas (se crea si no existe)."""
    d = Path(settings.uploads_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def sha256_bytes(data: bytes) -> str:
    """SHA-256 hexadecimal del contenido (identidad de contenido para re-ingesta idempotente)."""
    return hashlib.sha256(data).hexdigest()


def pdf_path(doc_id: uuid.UUID | str) -> Path:
    """Ruta destino del PDF de un documento: `{uploads_dir}/{doc_id}.pdf`."""
    return _uploads_dir() / f"{doc_id}.pdf"


def guardar_pdf(doc_id: uuid.UUID | str, data: bytes) -> str:
    """Escribe el PDF en disco y devuelve su `storage_uri` (ruta absoluta).

    Args:
        doc_id: id del documento (define el nombre del archivo).
        data: bytes del PDF ya leídos del `UploadFile`.

    Returns:
        Ruta absoluta del archivo guardado (para `documents.storage_uri`).
    """
    destino = pdf_path(doc_id)
    destino.write_bytes(data)
    return str(destino.resolve())


def borrar_pdf(doc_id: uuid.UUID | str) -> None:
    """Borra el PDF del disco si existe (idempotente)."""
    destino = pdf_path(doc_id)
    try:
        destino.unlink(missing_ok=True)
    except OSError:
        # El borrado de la fila en BD ya ocurrió; un fallo al limpiar el archivo no debe romper.
        pass
