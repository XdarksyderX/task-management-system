#!/bin/bash
# Simple test wrapper that uses test settings by default
cd /app
export DJANGO_SETTINGS_MODULE=config.test_settings
python manage.py test "$@"
