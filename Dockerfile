FROM python:3.11-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry==1.8.5 && poetry config virtualenvs.create false

FROM base AS deps
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only=main --no-root

FROM deps AS app
COPY . .
RUN poetry install --only=main

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
