"""LLM service: Groq API calls using the OpenAI-compatible interface.

Supports conversation history for follow-up questions.
"""

import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import get_settings
from app.models.schemas import Source, ConversationMessage
from app.prompts.system import build_prompt

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Lazy-init the Groq-compatible OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


def _build_messages(
    query: str,
    sources: list[Source],
    conversation_history: list[ConversationMessage] | None = None,
) -> list[dict]:
    """Build the full messages array including conversation history.

    Structure:
    1. System prompt (always first)
    2. Previous conversation turns (for follow-up context)
    3. Current user message with retrieved sources
    """
    base_messages = build_prompt(query, sources)

    if not conversation_history:
        return base_messages

    # Insert conversation history between system prompt and current message
    system_msg = base_messages[0]  # system prompt
    current_msg = base_messages[1]  # current user message with sources

    history_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation_history[-6:]  # Keep last 3 exchanges max
    ]

    return [system_msg] + history_messages + [current_msg]


async def generate_answer(
    query: str,
    sources: list[Source],
    conversation_history: list[ConversationMessage] | None = None,
) -> str:
    """Generate a complete (non-streaming) answer."""
    settings = get_settings()
    client = get_client()
    messages = _build_messages(query, sources, conversation_history)

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        max_tokens=settings.groq_max_tokens,
        temperature=0.3,
        extra_body={"reasoning_effort": "none"},
    )

    answer = response.choices[0].message.content

    logger.info(
        f"LLM answer generated | query='{query[:80]}' | "
        f"answer_length={len(answer)} chars"
    )
    logger.info(f"LLM full answer:\n{answer}")

    return answer


async def generate_answer_stream(
    query: str,
    sources: list[Source],
    conversation_history: list[ConversationMessage] | None = None,
) -> AsyncGenerator[str, None]:
    """Generate a streaming answer, yielding text chunks."""
    settings = get_settings()
    client = get_client()
    messages = _build_messages(query, sources, conversation_history)

    stream = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        max_tokens=settings.groq_max_tokens,
        temperature=0.3,
        stream=True,
        extra_body={"reasoning_effort": "none"},
    )

    # Accumulate the full answer while streaming
    full_answer = []

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            full_answer.append(delta.content)
            yield delta.content

    # Log the complete answer after streaming finishes
    answer_text = "".join(full_answer)
    logger.info(
        f"LLM streamed answer | query='{query[:80]}' | "
        f"answer_length={len(answer_text)} chars"
    )
    logger.info(f"LLM full answer:\n{answer_text}")