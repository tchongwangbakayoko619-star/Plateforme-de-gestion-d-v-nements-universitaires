"""
With these settings, tests run faster.
"""

import os

# Set DATABASE_URL for SQLite before importing base settings
# to avoid requiring the DATABASE_URL environment variable
os.environ.setdefault("DATABASE_URL", "sqlite:///test_db")
os.environ.setdefault(
    "DJANGO_SECRET_KEY",
    "ClYsDwAwn30K787Z4xdNZwP07ZMKWihYOsyasvYiJ0LDKIcLeiAF76CjEmLlJwUd",
)
os.environ.setdefault("DB_ENGINE", "django.db.backends.sqlite3")
os.environ.setdefault("DB_NAME", ":memory:")
os.environ.setdefault("DB_USER", "")
os.environ.setdefault("DB_PASSWORD", "")
os.environ.setdefault("DB_HOST", "")
os.environ.setdefault("DB_PORT", "")

from .base import *  # noqa: F403
from .base import TEMPLATES
from .base import env

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
# Use SQLite for tests to avoid needing DATABASE_URL environment variable
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test_db",
    },
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="ClYsDwAwn30K787Z4xdNZwP07ZMKWihYOsyasvYiJ0LDKIcLeiAF76CjEmLlJwUd",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "http://media.testserver/"
# Your stuff...
# ------------------------------------------------------------------------------
