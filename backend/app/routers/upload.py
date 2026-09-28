"""POST /api/upload — ingest PDF/TXT/MD into the vector store."""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import ALLOWED_EXTENSIONS
from app.models.schemas import UploadResponse
from app.services.ingestion import ingest_bytes
from app.services.vectorstore import store

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Please upload PDF, TXT, or MD.",
        )
    # replace existing doc with same name (avoid duplicate chunks)
    store.remove_document(file.filename)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail=f"'{file.filename}' is empty.")
    try:
        chunks = ingest_bytes(file.filename, raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.add_chunks(chunks)
    return UploadResponse(
        filename=file.filename,
        chunks_created=len(chunks),
        message=f"Ingested '{file.filename}' ({len(chunks)} chunks).",
    )
