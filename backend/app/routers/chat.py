"""Chat router: /chat and /chat/stream endpoints."""

import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest, ChatResponse
from app.services.query_analyzer import analyze_query
from app.services.retriever import retrieve
from app.services.llm import generate_answer, generate_answer_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

NO_RESULTS_MSG = (
    "No encontré información relevante en las fuentes disponibles "
    "para responder tu pregunta. Intenta reformular la consulta o "
    "pregunta sobre otro tema relacionado con las elecciones."
)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat: returns full answer + sources."""

    # Stage 1: LLM router classifies the query
    analysis = await analyze_query(request.message)

    # Stage 2: Retrieve with the right strategy
    sources = await retrieve(request.message, analysis)

    if not sources:
        return ChatResponse(
            answer=NO_RESULTS_MSG,
            sources=[],
            query_type="specific" if analysis.is_specific else "general",
            detected_candidates=analysis.candidate_names,
            detected_parties=analysis.party_names,
        )

    # Stage 3: Generate answer with conversation history
    answer = await generate_answer(
        request.message,
        sources,
        conversation_history=request.conversation_history,
    )

    return ChatResponse(
        answer=answer,
        sources=sources,
        query_type="specific" if analysis.is_specific else "general",
        detected_candidates=analysis.candidate_names,
        detected_parties=analysis.party_names,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat: returns answer as Server-Sent Events."""

    analysis = await analyze_query(request.message)
    sources = await retrieve(request.message, analysis)

    async def event_stream():
        yield f"data: {json.dumps({'type': 'analysis', 'query_type': 'specific' if analysis.is_specific else 'general', 'detected_candidates': analysis.candidate_names, 'detected_parties': analysis.party_names})}\n\n"

        sources_data = [s.model_dump(mode="json") for s in sources]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

        if not sources:
            yield f"data: {json.dumps({'type': 'text', 'content': NO_RESULTS_MSG})}\n\n"
            yield "data: [DONE]\n\n"
            return

        async for chunk in generate_answer_stream(
            request.message,
            sources,
            conversation_history=request.conversation_history,
        ):
            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(), media_type="text/event-stream"
    )