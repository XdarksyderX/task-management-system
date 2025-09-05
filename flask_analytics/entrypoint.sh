#!/usr/bin/env sh
set -Eeuo pipefail

: "${APP_MODULE:=app:create_app()}"
: "${GUNICORN_BIND:=0.0.0.0:5000}"
: "${GUNICORN_WORKERS:=2}"
: "${GUNICORN_THREADS:=4}"
: "${GUNICORN_TIMEOUT:=30}"

: "${RQ_QUEUES:=reports}"
: "${ANALYTICS_REDIS_URL:=redis://redis:6379/2}"
: "${ANALYTICS_DATABASE_URL:?ANALYTICS_DATABASE_URL is required}"
: "${REPORTS_DIR:=/reports}"

# WAIT_FOR: "redis,db" | "redis" | "db" | "" (none)
: "${WAIT_FOR:=}"

echo "[entrypoint] APP_MODULE=${APP_MODULE}"
echo "[entrypoint] REDIS=${ANALYTICS_REDIS_URL}  DB=${ANALYTICS_DATABASE_URL}"
echo "[entrypoint] REPORTS_DIR=${REPORTS_DIR}"

wait_redis() {
  echo "[wait] Redis..."
  i=0; until python - <<'PY' 2>/dev/null
import os, redis
r = redis.Redis.from_url(os.environ["ANALYTICS_REDIS_URL"])
r.ping()
PY
  do
    i=$((i+1)); [ $i -ge 120 ] && { echo "[wait] Redis timeout"; exit 1; }
    sleep 1
  done
  echo "[wait] Redis OK"
}

wait_db() {
  echo "[wait] DB..."
  i=0; until python - <<'PY' 2>/dev/null
import os
from sqlalchemy import create_engine, text
e = create_engine(os.environ["ANALYTICS_DATABASE_URL"], pool_pre_ping=True)
with e.connect() as c:
    c.execute(text("SELECT 1"))
PY
  do
    i=$((i+1)); [ $i -ge 120 ] && { echo "[wait] DB timeout"; exit 1; }
    sleep 1
  done
  echo "[wait] DB OK"
}

do_waits() {
  case "${WAIT_FOR}" in *redis*) wait_redis ;; esac
  case "${WAIT_FOR}" in *db*)    wait_db    ;; esac
}

start_backend() {
  do_waits
  mkdir -p "${REPORTS_DIR}"
  echo "[start] Gunicorn ${GUNICORN_BIND} workers=${GUNICORN_WORKERS} threads=${GUNICORN_THREADS} timeout=${GUNICORN_TIMEOUT}"
  exec gunicorn \
    -w "${GUNICORN_WORKERS}" \
    -k gthread \
    --threads "${GUNICORN_THREADS}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    -b "${GUNICORN_BIND}" \
    "${APP_MODULE}"
}

start_worker() {
  do_waits
  mkdir -p "${REPORTS_DIR}"
  : "${PYTHONPATH:=/app}"  # ensure tasks module is importable
  export PYTHONPATH
  echo "[start] RQ queues=${RQ_QUEUES}"
  exec rq worker -u "${ANALYTICS_REDIS_URL}" ${RQ_QUEUES}
}

case "${1:-backend}" in
  backend|api|web)  start_backend ;;
  worker|rq)        start_worker  ;;
  shell)            exec /bin/sh  ;;
  *)
    echo "Usage: entrypoint.sh [backend|worker|shell]"
    exit 2
    ;;
esac
