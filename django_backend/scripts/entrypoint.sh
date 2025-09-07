#!/usr/bin/env bash
set -euo pipefail

# Function to check or generate RSA keys
ensure_keys() {
    local keys_dir="/app/config/keys"
    local private_key="$keys_dir/jwt_private_key.pem"
    local public_key="$keys_dir/jwt_public_key.pem"
    
    # Create keys directory if it doesn't exist
    mkdir -p "$keys_dir"
    
    if [ ! -f "$private_key" ] || [ ! -f "$public_key" ]; then
        echo "🔑 RSA keys not found, generating them..."
        
        # Generate private key
        openssl genpkey -algorithm RSA -out "$private_key" -pkcs8 -pkeyopt rsa_keygen_bits:2048
        
        # Generate public key from private key
        openssl pkey -in "$private_key" -pubout -out "$public_key"
        
        # Set proper permissions
        chmod 600 "$private_key"
        chmod 644 "$public_key"        echo "✅ RSA keys generated successfully"
    else
        echo "✅ RSA keys found"
        # Ensure proper permissions
        chmod 600 "$private_key" 2>/dev/null || echo "⚠️  Could not set private key permissions"
        chmod 644 "$public_key" 2>/dev/null || echo "⚠️  Could not set public key permissions"
    fi
}
# Function to create Django superuser
create_superuser() {
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.contrib.auth import get_user_model
U = get_user_model()
u,e,p = os.getenv('DJANGO_SUPERUSER_USERNAME'), os.getenv('DJANGO_SUPERUSER_EMAIL'), os.getenv('DJANGO_SUPERUSER_PASSWORD')
if u and p and not U.objects.filter(username=u).exists():
    U.objects.create_superuser(username=u, email=e or '', password=p)
"
}

# All services ensure keys exist (generate if needed)
ensure_keys

# Create celery beat directory if needed
CELERY_BEAT_DIR="${CELERY_BEAT_DIR:-/app/celery_beat_data}"
mkdir -p "$CELERY_BEAT_DIR"

# Setup based on service type
case "${1:-web}" in
    web|asgi)
        # Web service: run migrations, create superuser
        python manage.py migrate --noinput
        create_superuser
        ;;
    worker|beat)
        # Other services: keys already checked
        echo "✅ Service ready to start"
        ;;
    test)
        # For tests: run migrations
        python manage.py migrate --noinput
        ;;
esac

# Start the appropriate service
case "${1:-web}" in
  web|asgi)
    daphne -b 0.0.0.0 -p 8000 config.asgi:application
    ;;
  worker)
    celery -A config worker -l info -E --hostname ${CELERY_WORKER_NAME:-tms-worker@%h} \
      -Q ${CELERY_QUEUES:-default} --concurrency ${CELERY_CONCURRENCY:-2} \
      --prefetch-multiplier ${CELERY_PREFETCH:-1}
    ;;
  beat)
    celery -A config beat -l info --schedule "$CELERY_BEAT_DIR/celerybeat-schedule"
    ;;
  test)
    export DJANGO_SETTINGS_MODULE=config.test_settings
    export DATABASE_URL=sqlite:///test.db
    scripts/run_tests.sh "${2:-all}"
    ;;
  *)
    exec "$@"
    ;;
esac
