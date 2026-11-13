FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd --gid 10001 ims \
 && useradd --uid 10001 --gid 10001 --no-create-home ims \
 && mkdir -p /app/media \
 && chown 10001:10001 /app/media
COPY --from=builder /app/.venv ./.venv
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY scripts ./scripts
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
