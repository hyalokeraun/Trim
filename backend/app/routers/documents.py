"""GET /api/documents, DELETE /api/documents/{filename}, POST /api/reindex."""
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.config import SAMPLE_DOCS_DIR
from app.models.schemas import DocumentListResponse, DocumentInfo
from app.services.ingestion import ingest_file
from app.services.vectorstore import store

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
def list_documents():
    stats = store.stats()
    docs = []
    for filename, count in sorted(stats["documents"].items()):
        chars = sum(len(c["text"]) for c in store.chunks if c.get("source") == filename)
        docs.append(DocumentInfo(filename=filename, chunks=count, chars=chars))
    return DocumentListResponse(documents=docs, total_chunks=stats["total_chunks"])


@router.delete("/documents/{filename}")
def delete_document(filename: str):
    removed = store.remove_document(filename)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"No document named '{filename}' found.")
    return {"message": f"Deleted '{filename}' ({removed} chunks removed)."}


@router.post("/reindex")
def reindex():
    """Clear the store and ingest all bundled sample docs. Handy for demos/resets."""
    store.clear()
    files = []
    total = 0
    sample_dir = Path(SAMPLE_DOCS_DIR)
    if sample_dir.exists():
        for path in sorted(sample_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}:
                try:
                    chunks = ingest_file(path)
                    store.add_chunks(chunks)
                    total += len(chunks)
                    files.append({"filename": path.name, "chunks": len(chunks)})
                except Exception as e:
                    files.append({"filename": path.name, "error": str(e)})
    return {"message": f"Reindexed {len(files)} files ({total} chunks).", "files": files}
