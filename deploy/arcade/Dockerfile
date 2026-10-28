FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PLAYWRIGHT_BROWSERS_PATH=/opt/browsers \
    PLAYWRIGHT_AUTO_INSTALL=false \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock server.py /app/

RUN uv sync --locked --no-dev \
    && uv run --no-sync playwright install --with-deps chromium \
    && uv cache clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home worker

USER worker
CMD ["python", "server.py"]
