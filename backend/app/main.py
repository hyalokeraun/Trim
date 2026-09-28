"""FastAPI entry point: CORS + routers + startup reindex + /api/ask-agent."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    FRONTEND_ORIGIN, SAMPLE_DOCS_DIR, OLLAMA_MODEL,
    EMPTY_QUESTION_MESSAGE, NOT_FOUND_MESSAGE,
)
from app.models.schemas import AskRequest, AskResponse, Source, HealthResponse
from app.routers import ask as ask_router, upload as upload_router, documents as documents_router
from app.services.ingestion import ingest_file
from app.services.vectorstore import store
from app.services.llm import check_ollama, check_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-ingest bundled sample docs on first boot (skip if store already populated)
    if not store.chunks:
        sample_dir = Path(SAMPLE_DOCS_DIR)
        if sample_dir.exists():
            for path in sorted(sample_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}:
                    try:
                        store.add_chunks(ingest_file(path))
                    except Exception as e:
                        print(f"[startup] skip {path.name}: {e}")
    print(f"[startup] indexed {len(store.chunks)} chunks from {len(store.stats()['documents'])} docs")
    yield


app = FastAPI(title="Intelligent Enterprise Knowledge Assistant", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask_router.router, prefix="/api", tags=["ask"])
app.include_router(upload_router.router, prefix="/api", tags=["upload"])
app.include_router(documents_router.router, prefix="/api", tags=["documents"])


@app.get("/api/health", response_model=HealthResponse)
def health():
    stats = store.stats()
    provider, ready = check_llm()
    return HealthResponse(
        status="ok",
        ollama_reachable=check_ollama(),
        ollama_model=OLLAMA_MODEL,
        llm_provider=provider,
        llm_ready=ready,
        documents=len(stats["documents"]),
        chunks=stats["total_chunks"],
    )


@app.post("/api/ask-agent", response_model=AskResponse)
def ask_agent(body: AskRequest):
    """Bonus endpoint running the LangGraph retrieve->grade->generate->cite flow."""
    from app.services import retriever
    from app.services.llm import LLMError
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail=EMPTY_QUESTION_MESSAGE)
    if retriever.is_ambiguous(q):
        return AskResponse(answer=retriever.clarifying_question(q),
                           sources=[], confidence=0.0, result_type="clarify")
    from app.agent.graph import run_agent
    history = [h.model_dump() for h in (body.history or [])][-6:]
    try:
        out = run_agent(q, history=history)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return AskResponse(answer=out["answer"], sources=[Source(**s) for s in out["sources"]],
                       confidence=out["confidence"], result_type=out.get("result_type", "exact"))


@app.get("/")
def root():
    return {"service": "knowledge-assistant", "docs": "/docs",
            "health": "/api/health", " hint": "POST /api/ask with {\"question\": \"...\"}"}
