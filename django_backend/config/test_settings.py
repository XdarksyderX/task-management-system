"""
Test settings for Task Management System

This module provides test-specific Django settings that override
the main settings for faster and more isolated test execution.
"""

from .settings import *
import os

# Test database configuration - use SQLite for speed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # In-memory database for faster tests
    }
}

# Disable migrations for faster test setup
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
DEBUG = False
TESTING = True

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Disable caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Test media settings
MEDIA_ROOT = '/tmp/test_media'

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Celery settings for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Test specific JWT settings
SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # Longer for tests
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),     # Shorter for tests
}

print("Using test settings - SQLite in-memory database")
print("Migrations disabled for faster test execution")
