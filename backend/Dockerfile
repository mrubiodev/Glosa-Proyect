# syntax=docker/dockerfile:1
#
# Imagen de Glosa (backend). Se construye con el contexto en `backend/`:
#
#   docker build -t glosa:dev --target runtime .
#   docker build -t glosa:test --target test .
#
# Etapas:
#   builder  instala los paquetes en un entorno virtual
#   runtime  imagen final: sin herramientas de compilación, usuario sin privilegios
#   test     builder + pytest + el código fuente, para ejecutar los tests

ARG PYTHON_VERSION=3.12

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /src
# Solo lo necesario para instalar. El orden de copia no importa: pip resuelve los
# paquetes locales entre sí al instalarlos todos en la misma orden.
COPY packages/ packages/
COPY adapters/ adapters/
COPY app/ app/

RUN pip install \
      ./packages/core ./packages/ingest ./packages/retrieval ./packages/storage \
      ./packages/explain ./packages/templates \
      ./adapters/http-api ./adapters/mcp-server ./adapters/worker \
      ./app

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    GLOSA_TEMPLATE=didactico \
    GLOSA_TEMPLATE_DIRS=/app/templates \
    GLOSA_DATA_DIR=/data

# Usuario sin privilegios. /data y /app/templates existen en la imagen para que los
# volúmenes con nombre hereden el propietario correcto.
RUN useradd --create-home --uid 10001 glosa \
 && mkdir -p /data /app/templates \
 && chown -R glosa:glosa /data /app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER glosa
VOLUME ["/data"]

LABEL org.opencontainers.image.title="Glosa" \
      org.opencontainers.image.description="RAG y MCP con permisos, cola de trabajos y trazabilidad" \
      org.opencontainers.image.licenses="PolyForm-Small-Business-1.0.0"

# Hasta que existan los adaptadores, la orden útil es validar la plantilla.
CMD ["python", "-m", "glosa_app", "check"]

# ---------------------------------------------------------------------------
FROM builder AS test

RUN pip install pytest
COPY . /src/backend
WORKDIR /src/backend

CMD ["sh", "-c", "pytest packages/core/tests packages/ingest/tests packages/storage/tests packages/templates/tests app/tests tests -q && GLOSA_TEST_ADAPTERS=glosa_storage.testing:make_adapters pytest packages/core/tests -q"]
