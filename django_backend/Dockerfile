FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
	build-essential \
	libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r /app/requirements.txt


FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
	curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r app && useradd --no-log-init -r -g app app

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt /app/requirements.txt
RUN pip install --no-cache /wheels/*

COPY . /app

ENV CELERY_BEAT_DIR=/app/celery_beat_data

RUN mkdir -p "$CELERY_BEAT_DIR" && \
	chown -R app:app /app && \
	chown -R app:app "$CELERY_BEAT_DIR" && \
	chmod +x /app/scripts/entrypoint.sh && \
	chmod +x /app/scripts/run_tests.sh

USER app

EXPOSE 8000