# Built from the repo root so the shared packages/ are in context:
#   docker build -f services/gateway/Dockerfile .
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Shared packages first - they change less often than service code.
COPY packages/ /app/packages/
RUN pip install ./packages/gn_scoring ./packages/gn_schemas

COPY services/gateway/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY services/gateway/app/ /app/app/

RUN useradd --create-home --uid 10001 guardia
USER guardia

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
