"""Pydantic request/response schemas for the API."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., description="User question")


class Source(BaseModel):
    document: str
    section: str = "N/A"
    snippet: str
    score: float = 0.0


class AskResponse(BaseModel):
    answer: str
    sources: List[Source] = []
    confidence: float = 0.0
    # exact | clarify | not_found — lets the frontend render appropriately
    result_type: Literal["exact", "clarify", "not_found"] = "exact"


class UploadResponse(BaseModel):
    filename: str
    chunks_created: int
    message: str


class DocumentInfo(BaseModel):
    filename: str
    chunks: int
    chars: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total_chunks: int


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    ollama_model: str
    llm_provider: str = "ollama"
    llm_ready: bool = False
    documents: int
    chunks: int
