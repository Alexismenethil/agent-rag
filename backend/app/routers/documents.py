"""Documentos: subida + ingesta + servicio del PDF.

STUB (V0): define el contrato canónico (ver docs/DECISIONES.md ADR-004) y devuelve 501.
La implementación real (Docling → chunking con metadatos → BGE-m3 → pgvector) llega en V1.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.deps import get_current_user_id

router = APIRouter(prefix="/documents", tags=["documents"])

_NOT_YET = "Disponible en V1 (ingesta de PDF). Ver docs/PLAN.md."


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def subir_documento(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Sube un PDF e inicia la ingesta. → 202 {doc_id, status}."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("")
async def listar_documentos(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/{doc_id}")
async def estado_documento(doc_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    """Estado de ingesta: {doc_id, status, progress, num_paginas, error_msg}."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/{doc_id}/file")
async def servir_pdf(doc_id: str, user_id: str = Depends(get_current_user_id)):
    """Sirve el PDF original (application/pdf) para el visor con resaltado de citas."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_documento(doc_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    """Borra el documento y sus chunks (las citas conservan su snippet). V5."""
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)
