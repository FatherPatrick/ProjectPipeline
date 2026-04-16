# ── build stage ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry (no virtualenv — we install directly into the image)
RUN pip install --no-cache-dir poetry==2.3.4

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app
ENV PYTHONPATH=/app/src

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

RUN mkdir -p logs

# Railway injects PORT; we expose 8000 as documentation only
EXPOSE 8000

# Default: run API + embedded scheduler (override CMD in Railway for dashboard)
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
