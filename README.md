# AIPE — Análisis Inteligente de Propuestas Electorales

AI-powered RAG application for analyzing Peruvian presidential candidates' proposals (2026 elections). Ask questions in Spanish and get sourced answers comparing what candidates **said** in interviews vs. what their **party plans** propose.

## How it works

```
User question
    │
    ▼
Embed query (multilingual-e5-large, CPU)
    │
    ▼
Vector search (pgvector / Supabase)
    │
    ▼
Enrich with metadata (SQL joins)
    │
    ▼
LLM synthesis (Qwen3 32B via Groq)
    │
    ▼
Structured answer with source citations
```

The system distinguishes between two source types:
- **Interviews**: What the candidate personally said (YouTube transcriptions)
- **Government plans**: What the party formally proposes (JNE PDF documents)

## Backend Setup

### Prerequisites
- Python 3.12+
- Groq API key ([console.groq.com](https://console.groq.com))
- Supabase database with ingested data (see [ingestion pipeline](https://github.com/your-user/peru-election-ingestion))

### Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env with your Groq API key and Supabase connection string
```

### Run

```bash
uvicorn app.main:app --reload
```

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check + model info |
| `/chat` | POST | Ask a question, get full answer + sources |
| `/chat/stream` | POST | Ask a question, get SSE stream |

### Example request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Qué candidato quiere aumentar el presupuesto para educación?"}'
```

## Tech Stack

- **LLM**: Qwen3 32B via Groq (OpenAI-compatible API)
- **Embeddings**: intfloat/multilingual-e5-large (1024 dims)
- **Vector DB**: PostgreSQL + pgvector (Supabase)
- **Backend**: FastAPI + asyncpg
- **Deployment**: Railway (backend) + Supabase (database)

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # Settings from env vars
│   ├── routers/
│   │   └── chat.py          # /chat and /chat/stream endpoints
│   ├── services/
│   │   ├── embedder.py      # Query embedding (CPU)
│   │   ├── retriever.py     # Vector search + SQL enrichment
│   │   └── llm.py           # Groq API (streaming + non-streaming)
│   ├── prompts/
│   │   └── system.py        # System prompt + context builder
│   └── models/
│       └── schemas.py       # Pydantic request/response models
├── requirements.txt
├── Dockerfile
└── .env.example
```

## License

MIT