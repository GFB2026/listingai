FROM python:3.12-slim

LABEL org.opencontainers.image.title="ListingAI Worker"
LABEL org.opencontainers.image.description="Celery worker for ListingAI - handles MLS sync, content generation, and media processing"
LABEL org.opencontainers.image.source="https://github.com/galt-ocean-realty/listingai"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app

USER appuser

ENTRYPOINT ["tini", "--"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A app.workers.celery_app inspect ping --timeout 5

CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]
