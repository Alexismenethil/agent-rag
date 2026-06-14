"""Documentos: subida + ingesta + servicio del PDF (implementación de V1).

Contrato canónico: docs/DECISIONES.md ADR-004. Todos los endpoints identifican al usuario por el
header `X-User-Id` (`get_current_user_id`, usuario de desarrollo por defecto en el MVP).

Flujo de `POST /documents`:
1. Valida que sea PDF (content-type y firma `%PDF`) y que no exceda `settings.max_upload_mb`.
2. Calcula `content_sha256` del binario (identidad de contenido para re-ingesta idempotente).
3. Si el usuario ya tiene un documento con ese sha:
   - `ready` → lo devuelve tal cual (no re-ingiere).
   - otro estado → reutiliza la fila y re-lanza la ingesta.
   Si no existe, crea la fila `documents(status='pending', owner_id=user, content_sha256, …)`.
4. Guarda el PDF en `settings.uploads_dir/{doc_id}.pdf` y persiste `storage_uri`.
5. Agenda la ingesta en segundo plano (`BackgroundTasks`) y responde 202 `{doc_id, status}`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import get_current_user_id
from app.models import Document
from app.schemas import DocumentListItem, DocumentStatusResponse, DocumentUploadResponse
from app.services import storage
from app.tasks import tarea_ingesta

router = APIRouter(prefix="/documents", tags=["documents"])

# Firma de un PDF: los primeros bytes son siempre "%PDF-".
_PDF_MAGIC = b"%PDF-"

# Avance orientativo de la ingesta por estado (para `GET /documents/{id}.progress`).
_PROGRESO_POR_ESTADO: dict[str, float] = {
    "pending": 0.0,
    "parsing": 0.2,
    "chunking": 0.4,
    "embedding": 0.6,
    "indexing": 0.85,
    "ready": 1.0,
    "failed": 1.0,
}


def _uuid_usuario(user_id: str) -> uuid.UUID:
    """Convierte el `X-User-Id` (str) a UUID; 400 si no es un UUID válido."""
    try:
        return uuid.UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-User-Id no es un UUID válido")


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=DocumentUploadResponse)
async def subir_documento(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    """Sube un PDF e inicia la ingesta en segundo plano. → 202 {doc_id, status}."""
    owner_id = _uuid_usuario(user_id)

    # Validación de tipo (content-type + extensión). La firma se valida tras leer los bytes.
    nombre = file.filename or "documento.pdf"
    es_pdf_ct = (file.content_type or "").lower() in ("application/pdf", "application/x-pdf")
    if not (es_pdf_ct or nombre.lower().endswith(".pdf")):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Solo se aceptan archivos PDF."
        )

    # Lee el binario respetando el límite de tamaño (sin cargar más de lo permitido).
    data = await _leer_con_limite(file, settings.max_upload_mb)

    # Valida la firma del PDF (evita renombrar otro archivo a .pdf).
    if not data.startswith(_PDF_MAGIC):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "El archivo no es un PDF válido (firma %PDF ausente).",
        )

    sha256 = storage.sha256_bytes(data)

    # Re-ingesta idempotente por contenido: UNIQUE(owner_id, content_sha256).
    existente = (
        await session.execute(
            select(Document).where(
                Document.owner_id == owner_id, Document.content_sha256 == sha256
            )
        )
    ).scalar_one_or_none()

    if existente is not None:
        if existente.status == "ready":
            # Ya ingerido: no se reprocesa, se devuelve el doc existente.
            return DocumentUploadResponse(doc_id=existente.id, status=existente.status)
        # Existe pero no está listo (o falló): se reutiliza la fila y se re-lanza la ingesta.
        doc = existente
        doc.status = "pending"
        doc.error_msg = None
        doc.titulo = doc.titulo or _titulo_desde_nombre(nombre)
        doc.filename = nombre
        doc.storage_uri = storage.guardar_pdf(doc.id, data)
        await session.commit()
    else:
        doc = Document(
            owner_id=owner_id,
            titulo=_titulo_desde_nombre(nombre),
            filename=nombre,
            content_sha256=sha256,
            mime_type="application/pdf",
            status="pending",
        )
        session.add(doc)
        # `flush` materializa el id generado por la BD sin cerrar la transacción.
        await session.flush()
        doc.storage_uri = storage.guardar_pdf(doc.id, data)
        await session.commit()

    # Agenda la ingesta tras responder 202 (no bloquea la respuesta).
    background.add_task(tarea_ingesta, doc.id, data)
    return DocumentUploadResponse(doc_id=doc.id, status="pending")


@router.get("", response_model=list[DocumentListItem])
async def listar_documentos(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[Document]:
    """Lista los documentos del usuario (más recientes primero)."""
    owner_id = _uuid_usuario(user_id)
    filas = (
        await session.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )
    ).scalars().all()
    return list(filas)


@router.get("/{doc_id}", response_model=DocumentStatusResponse)
async def estado_documento(
    doc_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> DocumentStatusResponse:
    """Estado de ingesta: {doc_id, status, progress, num_paginas, error_msg}."""
    doc = await _obtener_propio(session, doc_id, user_id)
    return DocumentStatusResponse(
        doc_id=doc.id,
        status=doc.status,
        progress=_PROGRESO_POR_ESTADO.get(doc.status, 0.0),
        num_paginas=doc.num_paginas,
        error_msg=doc.error_msg,
    )


@router.get("/{doc_id}/file")
async def servir_pdf(
    doc_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Sirve el PDF original (application/pdf) para el visor con resaltado de citas."""
    doc = await _obtener_propio(session, doc_id, user_id)
    ruta = storage.pdf_path(doc.id)
    if not ruta.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El archivo del documento no está disponible.")
    return FileResponse(
        path=str(ruta),
        media_type="application/pdf",
        filename=doc.filename or f"{doc.id}.pdf",
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_documento(
    doc_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Borra el documento y sus chunks (CASCADE). Las citas históricas conservan su snippet.

    El `chunk_id` de `message_citations` queda en NULL (ON DELETE SET NULL) pero el snippet/offsets
    denormalizados sobreviven (ADR-001). También elimina el PDF del disco.
    """
    doc = await _obtener_propio(session, doc_id, user_id)
    await session.delete(doc)  # CASCADE borra chunks; SET NULL en citas
    await session.commit()
    storage.borrar_pdf(doc_id)


# --------------------------------------------------------------------------------------
# Helpers internos
# --------------------------------------------------------------------------------------
async def _obtener_propio(
    session: AsyncSession, doc_id: uuid.UUID, user_id: str
) -> Document:
    """Devuelve el documento si pertenece al usuario; 404 si no existe o no es suyo.

    Se devuelve 404 (no 403) para no revelar la existencia de documentos de otros usuarios.
    """
    owner_id = _uuid_usuario(user_id)
    doc = (
        await session.execute(
            select(Document).where(Document.id == doc_id, Document.owner_id == owner_id)
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    return doc


async def _leer_con_limite(file: UploadFile, max_mb: int) -> bytes:
    """Lee el `UploadFile` por trozos, abortando con 413 si supera `max_mb` megabytes."""
    limite = max_mb * 1024 * 1024
    trozos: list[bytes] = []
    leidos = 0
    while True:
        trozo = await file.read(1024 * 1024)  # 1 MiB
        if not trozo:
            break
        leidos += len(trozo)
        if leidos > limite:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"El PDF supera el límite de {max_mb} MB.",
            )
        trozos.append(trozo)
    if leidos == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo está vacío.")
    return b"".join(trozos)


def _titulo_desde_nombre(filename: str) -> str:
    """Deriva un título legible a partir del nombre de archivo (sin extensión)."""
    base = filename.rsplit("/", 1)[-1]
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    return base.strip() or "Documento sin título"
