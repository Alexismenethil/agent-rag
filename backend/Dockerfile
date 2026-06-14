FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Toolchain + cabeceras para compilar dependencias con extensiones en C cuando no traen wheel:
#   - build-essential: gcc/make
#   - zlib1g-dev:      zlib.h (lo necesita `zlib-state`, dependencia de docling)
#   - libjpeg-dev:     cabeceras JPEG (pillow/docling)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential zlib1g-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# uv para instalar dependencias rápido
RUN pip install --no-cache-dir uv

# V1 necesita los extras "rag" (docling, pymupdf, sentence-transformers/torch).
# Instalamos las dependencias usando un paquete "stub" (solo app/__init__.py) para que cambiar
# el código de app/ NO invalide esta capa cara. El código real se copia después; además en
# desarrollo se monta ./backend sobre /app (ver docker-compose.yml), así que el runtime usa el
# código vivo del repo.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py \
    && uv pip install --system ".[rag,dev]"

# Código real (capa barata: cambiarla no reinstala las dependencias).
COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
