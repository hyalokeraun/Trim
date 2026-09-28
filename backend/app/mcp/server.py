"""Bonus: MCP server exposing the knowledge base as a tool.

Run standalone:  python -m app.mcp.server   (or: fastmcp run app/mcp/server.py)
Other apps/agents can then call `search_knowledge_base(query)`.
"""
from app.services.vectorstore import store
from app.config import TOP_K, RELEVANCE_THRESHOLD

try:
    from fastmcp import FastMCP
except ImportError:  # older `mcp` package exposes the same class
    from mcp.server.fastmcp import FastMCP  # type: ignore

mcp = FastMCP("enterprise-knowledge-assistant")


@mcp.tool()
def search_knowledge_base(query: str, top_k: int = TOP_K) -> dict:
    """Search enterprise policy documents. Returns ranked excerpts with source + section."""
    if not (query or "").strip():
        return {"answer": "Please provide a search query.", "sources": []}
    hits = store.search(query, top_k=top_k)
    passing = [h for h in hits if h["score"] >= RELEVANCE_THRESHOLD]
    if not passing:
        return {"answer": "I couldn't find this in the available documents.", "sources": []}
    return {
        "answer": f"Found {len(passing)} relevant excerpt(s).",
        "sources": [
            {"document": h["source"], "section": h.get("section", "N/A"),
             "snippet": h["text"][:600], "score": round(h["score"], 3)}
            for h in passing
        ],
    }


@mcp.tool()
def list_documents() -> dict:
    """List documents currently indexed in the knowledge base."""
    stats = store.stats()
    return {"documents": stats["documents"], "total_chunks": stats["total_chunks"]}


if __name__ == "__main__":
    mcp.run()
