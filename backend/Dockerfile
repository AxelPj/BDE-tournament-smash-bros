# --- Base commune : dépendances Python installées depuis uv.lock ---
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock /app/

RUN uv sync --frozen --no-install-project --no-dev

COPY . /app

EXPOSE 8000

# --- Dev : code monté en volume, rechargement automatique ---
FROM base AS development

# Ajoute les dépendances de dev (pytest) pour `make test`
RUN uv sync --frozen --no-install-project

# Applique les migrations SQLite, initialise la boutique si vide, puis lance uvicorn
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli seed-shop && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

# --- Prod : code figé dans l'image, utilisateur non-root ---
FROM base AS production

RUN useradd --system --uid 10001 app \
    && mkdir -p /data \
    && chown app /data

USER app

CMD ["sh", "-c", "alembic upgrade head && python -m app.cli seed-shop && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
