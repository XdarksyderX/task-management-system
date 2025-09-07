"""
Test settings for Task Management System

This module contains Django settings specifically for running tests.
It overrides certain production settings to make testing faster and more reliable.
"""

from .settings import *


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


EVENT_PUBLISHER_TYPE = "memory"


CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


SIMPLE_JWT.update(
    {
        "ALGORITHM": "HS256",
        "SIGNING_KEY": SECRET_KEY,
        "VERIFYING_KEY": None,
        "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
        "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    }
)


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


DEBUG = False


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


TEST = True
TESTING = True

print("[TEST_SETTINGS] Using test configuration - SQLite, HS256 JWT, Memory Cache")
