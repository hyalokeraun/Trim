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


def _recent_user_questions(history, n: int = 3) -> str:
    """Combine the last few user questions so follow-ups carry their topic."""
    if not history:
        return ""
    qs = []
    for turn in reversed(history[-8:]):
        role = turn.get("role") if isinstance(turn, dict) else getattr(turn, "role", "")
        text = turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", "")
        if role == "user" and (text or "").strip():
            qs.append(text.strip())
            if len(qs) >= n:
                break
    return " ".join(reversed(qs))


def retrieve(question: str, top_k: int = TOP_K,
             threshold: float = RELEVANCE_THRESHOLD, history=None) -> Dict[str, Any]:
    """Run search + threshold filter. Returns dict with status + chunks.

    Context-driven fallback: if a bare follow-up ("how many carry forward?",
    "what about sick leave?") finds nothing on its own, retry once with the
    previous user question prepended so pronouns/topics resolve.
    """
    hits, max_score = store.search_filtered(question, top_k=top_k, threshold=threshold)
    if not hits and history:
        prev = _recent_user_questions(history)
        if prev and question.strip().lower() not in prev.strip().lower():
            hits, max_score = store.search_filtered(f"{prev} {question}",
                                                    top_k=top_k, threshold=threshold)
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
