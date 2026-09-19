FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim AS builder-base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./

FROM builder-base AS builder-development
RUN uv sync --locked

FROM builder-base AS builder-production
RUN uv sync --locked --no-dev

FROM python:3.10-slim-bookworm AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --create-home --no-log-init app
WORKDIR /app
USER app
ENV PATH="/app/.venv/bin:$PATH"

# Development stage
FROM base AS development
COPY --from=builder-development --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .
EXPOSE 8000
# Run with hot-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
COPY --from=builder-production --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
