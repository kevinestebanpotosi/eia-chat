FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Create dummy source so uv sync can resolve the project
RUN mkdir -p app/templates && touch app/__init__.py app/templates/__init__.py

# Install dependencies only (skip project install)
RUN uv sync --frozen --no-dev --no-install-project

# Now copy the real source code
COPY app/ ./app/

# Install the project itself (fast, deps already cached)
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE ${PORT}

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
