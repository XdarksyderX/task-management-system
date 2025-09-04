#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput

python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
django.setup()
from django.contrib.auth import get_user_model
U = get_user_model()
u,e,p = os.getenv("DJANGO_SUPERUSER_USERNAME"), os.getenv("DJANGO_SUPERUSER_EMAIL"), os.getenv("DJANGO_SUPERUSER_PASSWORD")
if u and p and not U.objects.filter(username=u).exists():
    U.objects.create_superuser(username=u, email=e or "", password=p)
PY

case "${1:-web}" in
  web)    python manage.py runserver 0.0.0.0:8000 ;;
  worker) celery -A config worker -l info ;;
  beat)   celery -A config beat -l info ;;
  *)      exec "$@" ;;
esac
