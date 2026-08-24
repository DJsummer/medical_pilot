FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEDICAL_PORT=8900

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY data/schemas ./data/schemas
COPY data/gold_dataset ./data/gold_dataset
COPY data/templates ./data/templates
COPY data/validation_rules ./data/validation_rules
COPY data/expression_mappings ./data/expression_mappings

RUN mkdir -p data/reports data/logs

EXPOSE 8900

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8900/api/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8900", "--workers", "1"]
