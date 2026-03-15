"""Query analyzer: LLM-powered routing that classifies user questions.

Uses a fast LLM call to determine:
1. Whether the question targets specific candidates/parties or is general
2. Which candidate_ids are referenced (by name, nickname, indirect reference, etc.)

This replaces the naive string-matching approach which failed on:
- Indirect references: "la hija de Fujimori" → Keiko Fujimori
- Colloquial names: "el partido de la estrella" → Fuerza Popular
- Comparative queries: "Keiko o López Chau" → two specific candidates
- Generic words matching name fragments: "cada candidato" → false positive on "costa"
"""

import json
import logging
import asyncpg
from dataclasses import dataclass, field
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """Result of analyzing a user query."""

    raw_query: str

    # Detected entities
    candidate_ids: list[int] = field(default_factory=list)
    party_ids: list[int] = field(default_factory=list)

    # Human-readable names (for logging)
    candidate_names: list[str] = field(default_factory=list)
    party_names: list[str] = field(default_factory=list)

    # Query type
    is_specific: bool = False

    @property
    def is_general(self) -> bool:
        return not self.is_specific


# ─── Entity cache ─────────────────────────────────────────────────────────

_candidates_cache: list[dict] | None = None
_parties_cache: list[dict] | None = None


async def _load_entities():
    """Load all candidates and parties into memory for the LLM prompt."""
    global _candidates_cache, _parties_cache

    if _candidates_cache is not None and _parties_cache is not None:
        return

    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)

    try:
        if _candidates_cache is None:
            rows = await conn.fetch("""
                SELECT c.candidate_id, c.full_name, c.party_id,
                       pp.party_name, pp.abbreviation
                FROM candidates c
                JOIN political_parties pp ON pp.party_id = c.party_id
            """)
            _candidates_cache = [dict(r) for r in rows]
            logger.info(f"Loaded {len(_candidates_cache)} candidates into cache")

        if _parties_cache is None:
            rows = await conn.fetch("""
                SELECT party_id, party_name, abbreviation
                FROM political_parties
            """)
            _parties_cache = [dict(r) for r in rows]
            logger.info(f"Loaded {len(_parties_cache)} parties into cache")
    finally:
        await conn.close()


def _build_candidate_list() -> str:
    """Build a formatted candidate/party list for the router prompt."""
    lines = []
    for c in _candidates_cache:
        abbrev = f" ({c['abbreviation']})" if c.get("abbreviation") else ""
        lines.append(
            f"- candidate_id={c['candidate_id']}: {c['full_name']} — "
            f"Partido: {c['party_name']}{abbrev} (party_id={c['party_id']})"
        )
    return "\n".join(lines)


# ─── Router prompt ────────────────────────────────────────────────────────

ROUTER_SYSTEM_PROMPT = """\
Clasificador de preguntas para un sistema electoral del Perú 2026.

Determina si la pregunta menciona candidatos/partidos específicos o es general.

SPECIFIC: La pregunta NOMBRA a un candidato o partido (por nombre, apellido, apodo o referencia).
Ejemplos SPECIFIC:
- "¿Qué dice Keiko Fujimori sobre economía?" → SPECIFIC, candidate_id de Keiko
- "¿Qué propone López Aliaga?" → SPECIFIC, candidate_id de López Aliaga  
- "¿Qué dice Fuerza Popular?" → SPECIFIC, candidate_ids del partido
- "Compara a Keiko y López Aliaga" → SPECIFIC, ambos candidate_ids
- "¿Qué propone el partido de Keiko?" → SPECIFIC, candidate_id de Keiko

GENERAL: La pregunta NO nombra a nadie en particular.
Ejemplos GENERAL:
- "¿Qué candidato propone mejorar la educación?" → GENERAL
- "¿Quién habla de seguridad?" → GENERAL
- "¿Qué propuestas económicas hay?" → GENERAL

REGLA CLAVE: Si aparece el nombre o apellido de un candidato en la pregunta → SIEMPRE es SPECIFIC. \
No importa si también pregunta sobre un tema. "¿Qué dice Keiko sobre economía?" es SPECIFIC porque nombra a Keiko.

Solo clasifica como GENERAL si NO aparece ningún nombre de candidato o partido.

Responde ÚNICAMENTE con JSON válido, sin texto extra:

{"query_type": "specific" o "general", "candidate_ids": [IDs], "reasoning": "una línea"}
"""


async def analyze_query(query: str) -> QueryAnalysis:
    """Use LLM to classify the query and extract referenced candidates.

    Makes a fast, low-token Groq call with the candidate list as context.
    Falls back to GENERAL classification if the LLM call fails.
    """
    from app.services.llm import get_client

    await _load_entities()

    settings = get_settings()
    client = get_client()
    candidate_list = _build_candidate_list()

    user_message = (
        f"## Candidatos y partidos disponibles\n\n"
        f"{candidate_list}\n\n"
        f"## Pregunta del usuario\n\n"
        f"{query}"
    )

    try:
        response = await client.chat.completions.create(
            model=settings.groq_router_model,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=200,
            temperature=0,
        )

        raw_text = response.choices[0].message.content.strip()

        # Clean potential markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()

        result = json.loads(raw_text)
        logger.info(f"LLM router response: {result}")

    except Exception as e:
        logger.error(f"LLM router failed: {e}. Falling back to GENERAL.")
        return QueryAnalysis(raw_query=query, is_specific=False)

    # Build the QueryAnalysis from the LLM response
    analysis = QueryAnalysis(raw_query=query)

    query_type = result.get("query_type", "general")
    llm_candidate_ids = result.get("candidate_ids", [])

    if query_type == "specific" and llm_candidate_ids:
        analysis.is_specific = True

        # Map LLM-returned candidate_ids to our cached data
        valid_ids = {c["candidate_id"] for c in _candidates_cache}
        for cid in llm_candidate_ids:
            if cid in valid_ids:
                analysis.candidate_ids.append(cid)
                # Look up names for logging
                for c in _candidates_cache:
                    if c["candidate_id"] == cid:
                        analysis.candidate_names.append(c["full_name"])
                        if c["party_id"] not in analysis.party_ids:
                            analysis.party_ids.append(c["party_id"])
                            analysis.party_names.append(c["party_name"])
                        break

        # If LLM said specific but all IDs were invalid, fall back to general
        if not analysis.candidate_ids:
            logger.warning(
                f"LLM returned specific with ids={llm_candidate_ids} "
                f"but none were valid. Falling back to GENERAL."
            )
            analysis.is_specific = False

    logger.info(
        f"Query analysis: type={'SPECIFIC' if analysis.is_specific else 'GENERAL'} | "
        f"candidates={analysis.candidate_names} | parties={analysis.party_names} | "
        f"reasoning={result.get('reasoning', 'N/A')} | "
        f"query='{query[:80]}'"
    )

    return analysis