FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

FROM python:3.10-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*
ARG USER_ID=57439
ARG GROUP_ID=57439
RUN groupadd --gid "${GROUP_ID}" app && \
    useradd --uid "${USER_ID}" --gid app --create-home --no-log-init app
WORKDIR /app
RUN chown app:app /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER app
COPY --chown=app:app . .

CMD ["python", "register.py", "--help"]
