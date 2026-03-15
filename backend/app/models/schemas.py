"""Pydantic models for AIPE API requests, responses, and internal data."""

from pydantic import BaseModel
from typing import Optional


# ─── Internal models ──────────────────────────────────────────────────────


class ConversationMessage(BaseModel):
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str


class Source(BaseModel):
    """A retrieved source chunk with full metadata."""
    source_type: str  # "interview" or "government_plan"
    candidate_name: str
    party_name: str
    speaker_role: Optional[str] = None
    program_name: Optional[str] = None
    interview_date: Optional[str] = None
    youtube_link: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    pdf_link: Optional[str] = None
    chunk_text: str
    similarity: float
    is_context: bool = False
    chunk_index: Optional[int] = None
    interview_id: Optional[str] = None


# ─── API models ───────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for /chat and /chat/stream."""
    message: str
    conversation_history: Optional[list[ConversationMessage]] = None


class ChatResponse(BaseModel):
    """Response body for /chat (non-streaming)."""
    answer: str
    sources: list[Source]
    query_type: str  # "specific" or "general"
    detected_candidates: list[str] = []
    detected_parties: list[str] = []


class HealthResponse(BaseModel):
    """Response body for /health."""
    status: str = "ok"
    model: str
    embedding_model: str