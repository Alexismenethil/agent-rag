FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# uv para instalar dependencias rápido
RUN pip install --no-cache-dir uv

# Instala solo dependencias núcleo (V0/V1). Los extras (rag/voice/eval) se añaden
# cuando se trabaje esa versión: uv pip install --system ".[rag]" etc.
COPY pyproject.toml ./
COPY app ./app
RUN uv pip install --system .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
