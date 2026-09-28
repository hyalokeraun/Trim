"""Bonus: LangGraph agent flow — retrieve -> grade -> generate -> cite.

Exposes `run_agent(question)` used by /api/ask-agent and the MCP tool.
Falls back gracefully if langgraph isn't installed (uses plain pipeline).
"""
from typing import TypedDict, List, Dict, Any

from app.config import TOP_K, RELEVANCE_THRESHOLD, NOT_FOUND_MESSAGE
from app.services.vectorstore import store

try:
    from langgraph.graph import StateGraph, END
    _HAS_LG = True
except Exception:
    _HAS_LG = False


class AgentState(TypedDict, total=False):
    question: str
    hits: List[Dict[str, Any]]
    graded: List[Dict[str, Any]]
    answer: str
    sources: List[Dict[str, Any]]
    result_type: str


def retrieve_node(state: AgentState) -> AgentState:
    hits = store.search(state["question"], top_k=TOP_K)
    return {"hits": hits}


def grade_node(state: AgentState) -> AgentState:
    """Grade relevance: keep chunks above threshold (LLM-as-judge could plug in here)."""
    graded = [h for h in state.get("hits", []) if h["score"] >= RELEVANCE_THRESHOLD]
    return {"graded": graded}


def generate_node(state: AgentState) -> AgentState:
    from app.services.llm import generate_answer
    graded = state.get("graded", [])
    if not graded:
        return {"answer": NOT_FOUND_MESSAGE, "sources": [], "result_type": "not_found"}
    answer = generate_answer(state["question"], graded)
    sources = [
        {"document": h["source"], "section": h.get("section", "N/A"),
         "snippet": h["text"][:600], "score": round(h["score"], 3)}
        for h in graded
    ]
    rtype = "not_found" if "couldn't find this in the available documents" in answer.lower() else "exact"
    return {"answer": answer, "sources": sources, "result_type": rtype}


def _route(state: AgentState) -> str:
    return "generate" if state.get("graded") else "no_answer"


def _no_answer(state: AgentState) -> AgentState:
    return {"answer": NOT_FOUND_MESSAGE, "sources": [], "result_type": "not_found"}


_graph = None
if _HAS_LG:
    _g = StateGraph(AgentState)
    _g.add_node("retrieve", retrieve_node)
    _g.add_node("grade", grade_node)
    _g.add_node("generate", generate_node)
    _g.add_node("no_answer", _no_answer)
    _g.set_entry_point("retrieve")
    _g.add_edge("retrieve", "grade")
    _g.add_conditional_edges("grade", _route, {"generate": "generate", "no_answer": "no_answer"})
    _g.add_edge("generate", END)
    _g.add_edge("no_answer", END)
    _graph = _g.compile()


def run_agent(question: str) -> Dict[str, Any]:
    """Execute retrieve->grade->generate->cite. Returns {answer, sources, result_type, confidence}."""
    if _graph is not None:
        out = _graph.invoke({"question": question})
        graded = out.get("graded", [])
        conf = round(max((h["score"] for h in graded), default=0.0), 3)
        return {
            "answer": out.get("answer", NOT_FOUND_MESSAGE),
            "sources": out.get("sources", []),
            "result_type": out.get("result_type", "exact"),
            "confidence": conf,
        }
    # fallback: plain pipeline without langgraph
    from app.services import retriever
    from app.services.llm import generate_answer as _gen
    res = retriever.retrieve(question)
    if res["status"] == "not_found":
        return {"answer": NOT_FOUND_MESSAGE, "sources": [],
                "result_type": "not_found", "confidence": res["confidence"]}
    return {"answer": _gen(question, res["chunks"]), "sources": res["sources"],
            "result_type": "exact", "confidence": res["confidence"]}
