"""POST /api/ask — grounded Q&A with edge-case handling."""
from fastapi import APIRouter, HTTPException

from app.config import NOT_FOUND_MESSAGE, EMPTY_QUESTION_MESSAGE
from app.models.schemas import AskRequest, AskResponse, Source
from app.services import retriever
from app.services.llm import generate_answer, LLMError

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail=EMPTY_QUESTION_MESSAGE)

    # Ambiguous / very short query -> one clarifying question, no retrieval
    if retriever.is_ambiguous(q):
        return AskResponse(
            answer=retriever.clarifying_question(q),
            sources=[],
            confidence=0.0,
            result_type="clarify",
        )

    result = retriever.retrieve(q)
    if result["status"] == "not_found":
        return AskResponse(
            answer=NOT_FOUND_MESSAGE,
            sources=[],
            confidence=result["confidence"],
            result_type="not_found",
        )

    try:
        answer = generate_answer(q, result["chunks"])
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Safety net: model refuted everything -> normalize to not_found
    if "couldn't find this in the available documents" in answer.lower():
        return AskResponse(answer=NOT_FOUND_MESSAGE, sources=[],
                           confidence=result["confidence"], result_type="not_found")

    sources = [Source(**s) for s in result["sources"]]
    return AskResponse(answer=answer, sources=sources,
                       confidence=result["confidence"], result_type="exact")
