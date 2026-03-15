
# AIPE Backend — Production Dockerfile


FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Stage 1: Install Python dependencies (cached unless requirements.txt changes)
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Pre-download the embedding model (cached in image layer)
FROM dependencies AS model-cache

RUN python -c "\
from sentence_transformers import SentenceTransformer; \
model = SentenceTransformer('intfloat/multilingual-e5-large'); \
print(f'Model cached: {model.get_sentence_embedding_dimension()} dims')"

# Stage 3: Final image with app code (this layer changes on every deploy)
FROM model-cache AS final

COPY ./app ./app

ENV PORT=8000
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(f'http://localhost:{__import__(\"os\").environ.get(\"PORT\",\"8000\")}/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]