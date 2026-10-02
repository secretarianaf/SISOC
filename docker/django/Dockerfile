FROM python:3.11.15-slim-bookworm AS base

WORKDIR /sisoc

# Variables de entorno generales para Python y el sistema
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV LANG=es_AR.UTF-8
ENV LC_ALL=es_AR.UTF-8

# Instalación de dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      default-libmysqlclient-dev \
      gcc \
      libc-dev \
      bash \
      mariadb-client \
      locales \
      libpango-1.0-0 \
      libharfbuzz0b \
      libpangoft2-1.0-0 \
      libfontconfig1 \
      libcairo2 \
      tesseract-ocr \
      tesseract-ocr-spa \
      poppler-utils \
      libreoffice-writer \
      libreoffice-calc \
      fonts-liberation \
      wget \
      ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Modelo Tesseract de máxima precisión (tessdata_best, español). Queda
# disponible pero NO activo: el OCR usa el modelo del sistema por defecto. Para
# activarlo, definir OCR_TESSDATA_DIR=/usr/share/tessdata-best (ver docs/ocr.md;
# en pruebas sobre escaneos sellados el modelo best degradó el recall).
RUN mkdir -p /usr/share/tessdata-best && \
    wget -q -O /usr/share/tessdata-best/spa.traineddata \
      https://github.com/tesseract-ocr/tessdata_best/raw/main/spa.traineddata

# Configuración de locales
RUN echo "es_AR.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    echo "LANG=es_AR.UTF-8" > /etc/default/locale && \
    echo "LC_ALL=es_AR.UTF-8" >> /etc/default/locale

# Instalación de dependencias de la aplicación
COPY ./requirements.txt .
COPY ./requirements ./requirements
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

# El código vive en src/backends/: así gunicorn, celery y manage.py encuentran
# `config`, que a su vez agrega el kernel y los verticales al sys.path.
ENV PYTHONPATH=/sisoc/src/backends

# Agrega el script de entrypoint y hazlo ejecutable
COPY ./docker/django/entrypoint.py ./docker/django/entrypoint.py

# Comando de inicio de la aplicación
CMD ["python", "./docker/django/entrypoint.py"]


# --- Imágenes de deploy: el código va adentro, construido desde el SHA. ---
# Ver docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md.

FROM base AS source
COPY . /repo
RUN rm -rf /repo/src/frontends

# SISOC core: config, kernel y su cluster (sisoc_core), sin los backends por vertical.
FROM source AS core_source
RUN find /repo/src/backends -mindepth 1 -maxdepth 1 ! -name config ! -name kernel ! -name sisoc_core -exec rm -rf {} +

FROM base AS core
COPY --from=core_source /repo /sisoc
CMD ["python", "./docker/django/entrypoint.py"]

# Backend de un vertical: kernel (con templates y static compartidos),
# configuración compartida y su carpeta.
FROM source AS backend_source
ARG BACKEND
RUN test -n "$BACKEND" && test -d "/repo/src/backends/$BACKEND" \
    && test "$BACKEND" != config && test "$BACKEND" != kernel \
    && mkdir -p /out/src/backends \
    && cp -a /repo/docker /repo/manage.py /repo/CHANGELOG.md /out/ \
    && cp -a /repo/src/backends/config /repo/src/backends/kernel "/repo/src/backends/$BACKEND" /out/src/backends/

FROM base AS backend
COPY --from=backend_source /out /sisoc
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000"]

# Migrador único: composición completa (config.settings_all). No sirve tráfico.
# También corre collectstatic: es la única imagen con los estáticos de todos
# los verticales (ver docker/django/entrypoint.py).
FROM base AS migrator
COPY --from=source /repo /sisoc
ENV DJANGO_SETTINGS_MODULE=config.settings_all
ENV DJANGO_SERVICE_ROLE=migrator
CMD ["python", "./docker/django/entrypoint.py"]

# Desarrollo y CI: el código se monta con bind mount (docker-compose.yml). Es
# el último stage para que `docker compose build` sin target siga igual.
FROM base AS dev
