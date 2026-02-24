FROM python:3.12-slim

LABEL org.opencontainers.image.title="ListingAI Backend"
LABEL org.opencontainers.image.description="FastAPI backend for ListingAI - AI-powered real estate content engine"
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

EXPOSE 8000

ENTRYPOINT ["tini", "--"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Test stage: includes dev dependencies, still runs as appuser ---
FROM python:3.12-slim AS test

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY backend/ .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app

USER appuser

ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["tini", "--"]
CMD ["pytest", "-v", "--tb=short"]
