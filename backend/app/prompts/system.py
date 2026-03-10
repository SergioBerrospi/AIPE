"""System prompt for AIPE's RAG generation.

This is the most critical piece for answer quality. The prompt instructs the
LLM to synthesize across source types and cite properly.
"""

SYSTEM_PROMPT = """\
Eres AIPE (Análisis Inteligente de Propuestas Electorales), un asistente \
especializado en analizar las propuestas de los candidatos presidenciales del \
Perú para las elecciones 2026.

Tu trabajo es responder preguntas del usuario basándote EXCLUSIVAMENTE en las \
fuentes proporcionadas. Nunca inventes información.

## Tipos de fuentes

1. **Entrevistas** — Transcripciones de entrevistas en YouTube donde el \
candidato habló directamente. Algunas fuentes incluyen la pregunta del \
entrevistador (marcada como CONTEXTO) seguida de la respuesta del candidato. \
LEE AMBAS para entender la respuesta completa del candidato.

2. **Planes de gobierno** — Documentos oficiales presentados por el partido \
político ante el JNE.

## Reglas para responder

1. **Distingue siempre entre fuentes**: Deja claro si la información viene de \
una entrevista (lo que el candidato dijo) o del plan de gobierno (lo que el \
partido propone).

2. **Usa el contexto del entrevistador**: Cuando una fuente incluye la \
pregunta del entrevistador (CONTEXTO), úsala para dar sentido a la respuesta \
del candidato. Si el candidato dice "sí, un 10%", la pregunta del \
entrevistador te dice A QUÉ se refiere ese "sí".

3. **Cita las fuentes**: Para entrevistas menciona el programa y fecha. \
Para planes de gobierno menciona el partido y la página/sección.

4. **Compara entre candidatos** cuando la pregunta lo requiera.

5. **Señala contradicciones** entre lo que el candidato dijo y lo que su plan propone.

6. **Sé honesto**: Si las fuentes no cubren un tema, dilo claramente.

7. **Responde en español**, de forma clara y directa.
"""


def build_prompt(query: str, sources: list) -> list[dict]:
    """Build the messages array for the LLM call.

    Groups context chunks (interviewer questions) with their corresponding
    candidate answer chunks for clearer presentation.
    """
    # Separate sources by type
    interview_sources = []
    plan_sources = []
    for s in sources:
        if s.source_type == "interview" or (s.is_context and s.source_type == "interview"):
            interview_sources.append(s)
        else:
            plan_sources.append(s)

    # Build interview section
    interview_parts = []
    source_num = 0
    i = 0
    while i < len(interview_sources):
        source = interview_sources[i]

        if source.is_context and i + 1 < len(interview_sources):
            source_num += 1
            main_source = interview_sources[i + 1]
            header = _build_header(source_num, main_source)
            text = (
                f"[CONTEXTO - Pregunta del entrevistador]:\n"
                f"{source.chunk_text}\n\n"
                f"[RESPUESTA del candidato]:\n"
                f"{main_source.chunk_text}"
            )
            interview_parts.append(f"{header}\n{text}")
            i += 2
        else:
            source_num += 1
            header = _build_header(source_num, source)
            interview_parts.append(f"{header}\n{source.chunk_text}")
            i += 1

    # Build plan section
    plan_parts = []
    for source in plan_sources:
        source_num += 1
        header = _build_header(source_num, source)
        plan_parts.append(f"{header}\n{source.chunk_text}")

    # Combine with clear section headers
    sections = []
    if interview_parts:
        sections.append(
            "## BASADO EN ENTREVISTAS (lo que el candidato dijo)\n\n"
            + "\n\n---\n\n".join(interview_parts)
        )
    if plan_parts:
        sections.append(
            "## BASADO EN PLANES DE GOBIERNO (lo que el partido propone)\n\n"
            + "\n\n---\n\n".join(plan_parts)
        )

    context_block = "\n\n===\n\n".join(sections)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"## Fuentes recuperadas\n\n{context_block}\n\n"
                f"---\n\n## Pregunta del usuario\n\n{query}"
            ),
        },
    ]
    return messages


def _build_header(num: int, source) -> str:
    """Build a metadata header for a source."""
    parts = [f"[Fuente {num}]"]
    parts.append(f"Tipo: {_source_type_label(source.source_type)}")
    parts.append(f"Candidato: {source.candidate_name}")
    parts.append(f"Partido: {source.party_name}")

    if source.source_type == "interview":
        if source.program_name:
            parts.append(f"Programa: {source.program_name}")
        if source.interview_date:
            parts.append(f"Fecha: {source.interview_date}")
        if source.youtube_link:
            link = source.youtube_link
            if source.start_time is not None:
                link += f"&t={int(source.start_time)}"
            parts.append(f"Enlace: {link}")
    elif source.source_type == "government_plan":
        if source.page_number is not None:
            parts.append(f"Página: {source.page_number}")
        if source.section_title:
            parts.append(f"Sección: {source.section_title}")
        if source.pdf_link:
            parts.append(f"Enlace PDF: {source.pdf_link}")

    return " | ".join(parts)


def _source_type_label(source_type: str) -> str:
    labels = {
        "interview": "Entrevista",
        "government_plan": "Plan de Gobierno",
    }
    return labels.get(source_type, source_type)