FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache

WORKDIR /app
RUN addgroup --system veyra && adduser --system --ingroup veyra veyra
COPY requirements.txt pyproject.toml ./
RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get purge --yes --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY alembic.ini ./
COPY backend ./backend
COPY config ./config
COPY database ./database
COPY execution ./execution
COPY migrations ./migrations
COPY quant_engine ./quant_engine
RUN chown -R veyra:veyra /app
USER veyra
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=3)"
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
