FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./pyproject.toml /app/pyproject.toml

RUN uv sync --no-install-project --no-dev

COPY . /app

EXPOSE 8000

# Applique les migrations SQLite, initialise la boutique si vide, puis lance uvicorn
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli seed-shop && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
