"""Retrieval: query -> TF-IDF search -> relevance filter + ambiguity detection."""
import re
from typing import Dict, Any

from app.config import TOP_K, RELEVANCE_THRESHOLD, NOT_FOUND_MESSAGE
from app.services.vectorstore import store


def is_ambiguous(query: str) -> bool:
    """Very short / single-word queries like 'leave?' need clarification first."""
    q = query.strip().lower().rstrip("?!.").strip()
    if not q:
        return False  # empty handled separately
    tokens = re.findall(r"[a-z0-9]+", q)
    # 1-2 generic tokens with no question structure -> ambiguous
    if len(tokens) <= 2 and len(q) < 25:
        return True
    return False


def clarifying_question(query: str) -> str:
    topic = query.strip().strip("?!. ")
    return (
        f"Your question \"{topic}\" is a bit short — could you clarify? "
        f"For example: are you asking about {topic} eligibility, limits, or how to apply?"
    )


def retrieve(question: str, top_k: int = TOP_K,
             threshold: float = RELEVANCE_THRESHOLD) -> Dict[str, Any]:
    """Run search + threshold filter. Returns dict with status + chunks."""
    hits, max_score = store.search_filtered(question, top_k=top_k, threshold=threshold)
    if not hits:
        return {
            "status": "not_found",
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
            "confidence": round(max_score, 3),
        }
    sources = [
        {
            "document": h["source"],
            "section": h["section"],
            "snippet": h["text"][:600],
            "score": round(h["score"], 3),
        }
        for h in hits
    ]
    return {
        "status": "found",
        "chunks": hits,
        "sources": sources,
        "confidence": round(max(h["score"] for h in hits), 3),
    }
