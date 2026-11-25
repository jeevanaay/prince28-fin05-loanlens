
# -----------------------------------------------
# Stage 1: Build dependencies and install LoanLens
# -----------------------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency metadata first for better layer caching.
COPY pyproject.toml uv.lock README.md ./

# Copy application source.
COPY src ./src

# Install the application and production dependencies.
RUN uv sync --frozen --no-dev --no-editable


# -----------------------------------------------
# Stage 2: Minimal runtime image
# -----------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create a non-root application user.
RUN groupadd --system app && \
    useradd --system --gid app --create-home app

# Copy the installed virtual environment.
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy runtime application assets.
COPY --chown=app:app data ./data
COPY --chown=app:app prompts ./prompts
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app alembic.ini ./

# Run as an unprivileged user.
USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn loanlens.api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
