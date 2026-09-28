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
    history: List[Dict[str, str]]
    search_query: str
    retries: int
    hits: List[Dict[str, Any]]
    graded: List[Dict[str, Any]]
    answer: str
    sources: List[Dict[str, Any]]
    result_type: str


def retrieve_node(state: AgentState) -> AgentState:
    hits = store.search(state.get("search_query") or state["question"], top_k=TOP_K)
    return {"hits": hits}


def grade_node(state: AgentState) -> AgentState:
    """Grade relevance with the SAME rule as the plain pipeline (threshold + margin)."""
    from app.services.vectorstore import VectorStore
    graded = VectorStore.apply_filter(state.get("hits", []), RELEVANCE_THRESHOLD)
    return {"graded": graded}


def generate_node(state: AgentState) -> AgentState:
    from app.services.llm import generate_answer
    graded = state.get("graded", [])
    if not graded:
        return {"answer": NOT_FOUND_MESSAGE, "sources": [], "result_type": "not_found"}
    answer = generate_answer(state["question"], graded, history=state.get("history"))
    sources = [
        {"document": h["source"], "section": h.get("section", "N/A"),
         "snippet": h["text"][:600], "score": round(h["score"], 3)}
        for h in graded
    ]
    rtype = "not_found" if "couldn't find this in the available documents" in answer.lower() else "exact"
    return {"answer": answer, "sources": sources, "result_type": rtype}


def _route(state: AgentState) -> str:
    """The agentic bit: grade outcome decides the next step dynamically."""
    if state.get("graded"):
        return "generate"
    if state.get("retries", 0) >= 1:
        return "no_answer"  # one rewrite already tried — stop, don't loop forever
    return "rewrite"


def rewrite_node(state: AgentState) -> AgentState:
    """First retrieval failed: let the LLM rephrase into policy vocabulary and retry."""
    from app.services.llm import rewrite_query
    keywords = rewrite_query(state["question"], state.get("history"))
    return {"search_query": keywords, "retries": state.get("retries", 0) + 1}


def _no_answer(state: AgentState) -> AgentState:
    return {"answer": NOT_FOUND_MESSAGE, "sources": [], "result_type": "not_found"}


_graph = None
if _HAS_LG:
    _g = StateGraph(AgentState)
    _g.add_node("retrieve", retrieve_node)
    _g.add_node("grade", grade_node)
    _g.add_node("rewrite", rewrite_node)
    _g.add_node("generate", generate_node)
    _g.add_node("no_answer", _no_answer)
    _g.set_entry_point("retrieve")
    _g.add_edge("retrieve", "grade")
    _g.add_conditional_edges("grade", _route, {"generate": "generate", "rewrite": "rewrite", "no_answer": "no_answer"})
    _g.add_edge("rewrite", "retrieve")
    _g.add_edge("generate", END)
    _g.add_edge("no_answer", END)
    _graph = _g.compile()


def run_agent(question: str, history=None) -> Dict[str, Any]:
    """Execute retrieve->grade->generate->cite. Returns {answer, sources, result_type, confidence}."""
    history = list(history or [])
    if _graph is not None:
        out = _graph.invoke({"question": question, "history": history, "retries": 0})
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
    res = retriever.retrieve(question, history=history)
    if res["status"] == "not_found":
        return {"answer": NOT_FOUND_MESSAGE, "sources": [],
                "result_type": "not_found", "confidence": res["confidence"]}
    return {"answer": _gen(question, res["chunks"], history=history), "sources": res["sources"],
            "result_type": "exact", "confidence": res["confidence"]}
