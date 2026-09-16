FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system veyra && adduser --system --ingroup veyra veyra
COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY alembic.ini ./
COPY backend ./backend
COPY config ./config
COPY database ./database
COPY migrations ./migrations
COPY quant_engine ./quant_engine
RUN chown -R veyra:veyra /app
USER veyra
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
