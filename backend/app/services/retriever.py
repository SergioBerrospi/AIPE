"""Retriever service: smart two-strategy retrieval with context expansion.

Strategy A (SPECIFIC query): User mentioned a candidate/party name.
  → Filter chunks by candidate_id, then semantic search within that scope.
  → Fewer chunks needed since they're all relevant.

Strategy B (GENERAL query): No candidate/party mentioned.
  → For each candidate: retrieve top N chunks per source type.
  → Ensures coverage across all candidates instead of one dominating.

Both strategies expand results with adjacent chunks (chunk_index ± 1)
to capture interviewer questions that give context to candidate answers.

All SQL queries are logged for debugging.
"""

import logging
import asyncpg
from app.config import get_settings
from app.services.embedder import embed_query
from app.services.query_analyzer import QueryAnalysis
from app.models.schemas import Source

logger = logging.getLogger(__name__)


# ─── Strategy A: Specific candidate/party query ───────────────────────────

SPECIFIC_BY_SOURCE_SQL = """
WITH ranked AS (
    SELECT
        c.chunk_id,
        c.source_type,
        c.chunk_text,
        c.chunk_index,
        c.speaker_role,
        c.start_time,
        c.end_time,
        c.page_number,
        c.section_title,
        c.interview_id,
        c.plan_id,
        c.candidate_id,
        1 - (c.embedding <=> $1::vector) AS similarity,
        -- Prioritize candidate speech over interviewer questions
        -- Interviewer chunks get fetched as adjacent context anyway
        CASE WHEN c.speaker_role = 'candidate' THEN 0
             WHEN c.speaker_role IS NULL THEN 0
             ELSE 1
        END AS speaker_priority
    FROM chunks c
    WHERE c.candidate_id = ANY($2::int[])
      AND c.source_type = $3
      AND 1 - (c.embedding <=> $1::vector) > $4
    ORDER BY speaker_priority, c.embedding <=> $1::vector
    LIMIT $5
)
SELECT
    r.*,
    cand.full_name AS candidate_name,
    pp.party_name,
    pp.abbreviation AS party_abbreviation,
    i.program_name,
    i.interview_date,
    i.youtube_link,
    gp.pdf_link
FROM ranked r
LEFT JOIN candidates cand ON cand.candidate_id = r.candidate_id
LEFT JOIN political_parties pp ON pp.party_id = cand.party_id
LEFT JOIN interviews i ON i.interview_id = r.interview_id
LEFT JOIN government_plans gp ON gp.plan_id = r.plan_id
ORDER BY r.similarity DESC;
"""


# ─── Strategy B: General query (per-candidate retrieval) ──────────────────

GENERAL_SEARCH_SQL = """
WITH per_candidate AS (
    SELECT
        c.chunk_id,
        c.source_type,
        c.chunk_text,
        c.chunk_index,
        c.speaker_role,
        c.start_time,
        c.end_time,
        c.page_number,
        c.section_title,
        c.interview_id,
        c.plan_id,
        c.candidate_id,
        1 - (c.embedding <=> $1::vector) AS similarity,
        CASE WHEN c.speaker_role = 'candidate' THEN 0
             WHEN c.speaker_role IS NULL THEN 0
             ELSE 1
        END AS speaker_priority,
        ROW_NUMBER() OVER (
            PARTITION BY c.candidate_id, c.source_type
            ORDER BY
                CASE WHEN c.speaker_role = 'candidate' THEN 0
                     WHEN c.speaker_role IS NULL THEN 0
                     ELSE 1
                END,
                c.embedding <=> $1::vector
        ) AS rank_in_group
    FROM chunks c
    WHERE 1 - (c.embedding <=> $1::vector) > $2
)
SELECT
    pc.*,
    cand.full_name AS candidate_name,
    pp.party_name,
    pp.abbreviation AS party_abbreviation,
    i.program_name,
    i.interview_date,
    i.youtube_link,
    gp.pdf_link
FROM per_candidate pc
LEFT JOIN candidates cand ON cand.candidate_id = pc.candidate_id
LEFT JOIN political_parties pp ON pp.party_id = cand.party_id
LEFT JOIN interviews i ON i.interview_id = pc.interview_id
LEFT JOIN government_plans gp ON gp.plan_id = pc.plan_id
WHERE pc.rank_in_group <= $3
ORDER BY pc.candidate_id, pc.source_type, pc.similarity DESC;
"""


# ─── Adjacent chunk expansion (for interviewer context) ───────────────────

ADJACENT_CHUNKS_SQL = """
SELECT
    c.chunk_id,
    c.source_type,
    c.chunk_text,
    c.chunk_index,
    c.speaker_role,
    c.start_time,
    c.end_time,
    c.page_number,
    c.section_title,
    c.interview_id,
    c.plan_id,
    c.candidate_id,
    0.0 AS similarity,
    cand.full_name AS candidate_name,
    pp.party_name,
    pp.abbreviation AS party_abbreviation,
    i.program_name,
    i.interview_date,
    i.youtube_link,
    gp.pdf_link
FROM chunks c
LEFT JOIN candidates cand ON cand.candidate_id = c.candidate_id
LEFT JOIN political_parties pp ON pp.party_id = cand.party_id
LEFT JOIN interviews i ON i.interview_id = c.interview_id
LEFT JOIN government_plans gp ON gp.plan_id = c.plan_id
WHERE c.interview_id = $1
  AND c.chunk_index = $2
  AND c.chunk_id != ALL($3::int[]);
"""


def _row_to_source(row: dict, is_context: bool = False) -> Source:
    """Convert a database row to a Source object."""
    

    return Source(
        source_type=row["source_type"],
        candidate_name=row["candidate_name"] or "Desconocido",
        party_name=row["party_name"] or "Desconocido",
        speaker_role=row.get("speaker_role"),
        program_name=row.get("program_name"),
        interview_date=(
            str(row["interview_date"]) if row.get("interview_date") else None
        ),
        youtube_link=row.get("youtube_link"),
        start_time=row.get("start_time"),
        end_time=row.get("end_time"),
        page_number=row.get("page_number"),
        section_title=row.get("section_title"),
        pdf_link=row.get("pdf_link"), 
        chunk_text=row["chunk_text"],
        similarity=float(row["similarity"]),
        is_context=is_context,
        chunk_index=row.get("chunk_index"),
        interview_id=row.get("interview_id"),
    )


async def _expand_with_adjacent(
    conn: asyncpg.Connection,
    sources: list[Source],
    rows: list[dict],
) -> list[Source]:
    """For interview chunks, fetch the previous chunk (chunk_index - 1)
    to capture the interviewer's question that gives context to the
    candidate's answer.

    Only expands interview chunks, not government plan chunks.
    """
    existing_ids = [r["chunk_id"] for r in rows]
    expanded = []

    for i, row in enumerate(rows):
        # Add the original source
        expanded.append(sources[i])

        # Only expand interview chunks where candidate is speaking
        if row["source_type"] != "interview":
            continue
        if row.get("interview_id") is None:
            continue
        if row.get("speaker_role") == "interviewer":
            continue  # Don't expand interviewer chunks

        prev_index = row["chunk_index"] - 1
        if prev_index < 0:
            continue

        logger.debug(
            f"Fetching adjacent chunk: interview_id={row['interview_id']}, "
            f"chunk_index={prev_index}"
        )

        adj_rows = await conn.fetch(
            ADJACENT_CHUNKS_SQL,
            row["interview_id"],
            prev_index,
            existing_ids,
        )

        for adj_row in adj_rows:
            adj_source = _row_to_source(dict(adj_row), is_context=True)
            # Insert context chunk BEFORE the candidate's answer
            expanded.insert(len(expanded) - 1, adj_source)
            existing_ids.append(adj_row["chunk_id"])

    return expanded


async def retrieve(query: str, analysis: QueryAnalysis) -> list[Source]:
    """Main retrieval function. Uses query analysis to pick the right strategy.

    Args:
        query: The user's raw question
        analysis: Result from query_analyzer.analyze_query()

    Returns:
        List of Source objects with metadata, including adjacent context chunks.
    """
    settings = get_settings()

    # Embed the query
    query_embedding = embed_query(query)
    embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

    conn = await asyncpg.connect(settings.database_url)
    try:
        if analysis.is_specific:
            sources, rows = await _retrieve_specific(
                conn, embedding_str, analysis, settings
            )
        else:
            sources, rows = await _retrieve_general(
                conn, embedding_str, settings
            )

        # Expand interview chunks with adjacent context
        sources = await _expand_with_adjacent(conn, sources, rows)

    finally:
        await conn.close()

    # Token budget: estimate and trim if needed
    sources = _trim_to_token_budget(sources, settings)

    logger.info(
        f"Retrieval complete: strategy={'SPECIFIC' if analysis.is_specific else 'GENERAL'} | "
        f"final_chunks={len(sources)} | "
        f"query='{query[:80]}'"
    )
    return sources


async def _retrieve_specific(
    conn: asyncpg.Connection,
    embedding_str: str,
    analysis: QueryAnalysis,
    settings,
) -> tuple[list[Source], list[dict]]:
    """Strategy A: Search within specific candidate(s), independently per source type.

    Runs two separate queries:
    1. Top N interview chunks for the candidate(s)
    2. Top N government plan chunks for the candidate(s)/party

    This guarantees both source types are represented — interview chunks
    can't push out plan chunks or vice versa.
    """
    candidate_ids = analysis.candidate_ids

    # Query 1: Interview chunks
    logger.info(
        f"SQL [specific interviews]: candidate_ids={candidate_ids}, "
        f"threshold={settings.similarity_threshold}, "
        f"top_k={settings.top_k_specific_interviews}"
    )
    interview_rows = await conn.fetch(
        SPECIFIC_BY_SOURCE_SQL,
        embedding_str,
        candidate_ids,
        "interview",
        settings.similarity_threshold,
        settings.top_k_specific_interviews,
    )

    # Query 2: Government plan chunks
    logger.info(
        f"SQL [specific plans]: candidate_ids={candidate_ids}, "
        f"threshold={settings.similarity_threshold}, "
        f"top_k={settings.top_k_specific_plans}"
    )
    plan_rows = await conn.fetch(
        SPECIFIC_BY_SOURCE_SQL,
        embedding_str,
        candidate_ids,
        "government_plan",
        settings.similarity_threshold,
        settings.top_k_specific_plans,
    )

    # Combine: interviews first, then plans (for structured prompt output)
    all_raw = [dict(r) for r in interview_rows] + [dict(r) for r in plan_rows]
    all_sources = [_row_to_source(r) for r in all_raw]

    logger.info(
        f"Specific retrieval: {len(interview_rows)} interview + "
        f"{len(plan_rows)} plan chunks for candidates {analysis.candidate_names}"
    )
    return all_sources, all_raw


async def _retrieve_general(
    conn: asyncpg.Connection,
    embedding_str: str,
    settings,
) -> tuple[list[Source], list[dict]]:
    """Strategy B: Retrieve top N chunks per candidate per source type.

    This ensures every candidate gets representation in the results,
    instead of one candidate dominating all top-K slots.
    """

    per_group = settings.top_k_per_group

    logger.info(
        f"SQL [general search]: threshold={settings.similarity_threshold}, "
        f"per_group={per_group}"
    )

    rows = await conn.fetch(
        GENERAL_SEARCH_SQL,
        embedding_str,
        settings.similarity_threshold,
        per_group,
    )

    raw_rows = [dict(r) for r in rows]
    sources = [_row_to_source(r) for r in raw_rows]

    # Log per-candidate breakdown
    from collections import Counter
    breakdown = Counter(
        (s.candidate_name, s.source_type) for s in sources
    )
    logger.info(
        f"General retrieval: {len(sources)} total chunks | "
        f"breakdown: {dict(breakdown)}"
    )

    return sources, raw_rows


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters for Spanish text."""
    return len(text) // 4


def _trim_to_token_budget(sources: list[Source], settings) -> list[Source]:
    """Trim sources to fit within the token budget.

    Keeps sources in order (context chunks stay next to their parent).
    Stops adding when we'd exceed the budget. Prevents 413 errors from Groq.
    """
    max_context_tokens = settings.max_context_tokens

    result = []
    total_tokens = 0

    for source in sources:
        chunk_tokens = _estimate_tokens(source.chunk_text) + 50  # +50 for metadata header
        if total_tokens + chunk_tokens > max_context_tokens:
            logger.warning(
                f"Token budget reached ({total_tokens}/{max_context_tokens}). "
                f"Trimmed {len(sources) - len(result)} chunks."
            )
            break
        result.append(source)
        total_tokens += chunk_tokens

    logger.info(f"Token budget: ~{total_tokens}/{max_context_tokens} tokens used")
    return result