FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim AS builder
# numcodecs (pulled in via titiler.xarray -> zarr) has no prebuilt wheel for
# this platform, so it needs a compiler to build from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

FROM python:3.10-slim-bookworm AS base
# rasterio's wheel dynamically links libexpat at runtime; it's not bundled
# in the wheel and slim-bookworm doesn't ship it by default.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --create-home --no-log-init app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER app

# Development stage
FROM base AS development
COPY --chown=app:app . .
EXPOSE 8000
# Run with hot-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
COPY --chown=app:app . .
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
