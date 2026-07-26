"""LAN Deployment Settings for Electric Store.

Extends base settings for local-network deployment:
- DEBUG=False
- HTTP-only (no SSL)
- Local static/media storage
- Allows all LAN hosts
- MySQL database (uses existing server)
"""

import socket
import sys
from pathlib import Path

from .base import *  # noqa: F403
from .base import DATABASES
from .base import env


def _get_lan_ip() -> str:
    """Detect the machine's local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"


LAN_IP = _get_lan_ip()

# ---------- Path detection for frozen (PyInstaller) vs development ----------
if getattr(sys, 'frozen', False):
    # Packaged EXE: writable storage goes next to the executable,
    # base_dir (sys._MEIPASS) is the read-only temp extraction directory
    _WRITABLE_DIR = Path(sys.executable).resolve().parent
else:
    # Development: use project root
    _WRITABLE_DIR = BASE_DIR

# Ensure writable directories exist
for _d in [_WRITABLE_DIR / "media", _WRITABLE_DIR / "deployment" / "logs"]:
    _d.mkdir(parents=True, exist_ok=True)

# GENERAL
SECRET_KEY = env("DJANGO_SECRET_KEY", default="lan-default-insecure-change-in-production")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
DEBUG = False

# ---------- DATABASE: Use MySQL from environment or base.py ----------
# Use DATABASE_URL from .env if set, otherwise fall back to base.py MySQL config.
# This requires READ_DOT_ENV_FILE=True to be set before settings load.
_DATABASE_URL = env("DATABASE_URL", default=None)
if _DATABASE_URL:
    DATABASES = {"default": env.db("DATABASE_URL", default=_DATABASE_URL)}
    DATABASES["default"]["ATOMIC_REQUESTS"] = True
else:
    # Keep base.py MySQL config (DATABASES already imported)
    DATABASES["default"]["ATOMIC_REQUESTS"] = True

# CACHES
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# Add WhiteNoise to serve static files in production (DEBUG=False)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + MIDDLEWARE[1:]

# SECURITY - LAN HTTP mode (no SSL)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_NAME = "lan_sessionid"
CSRF_COOKIE_NAME = "lan_csrftoken"
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[f"http://{LAN_IP}:8000", "http://localhost:8000", "http://127.0.0.1:8000"])

# QR code base URL — use LAN IP so scanned QR codes resolve correctly
QR_CODE_BASE_URL = f"http://{LAN_IP}:8000"

# STATIC & MEDIA - Local storage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATIC_URL = "/static/"
WHITENOISE_USE_FINDERS = True
# Media files stored persistently next to the executable (not in temp dir)
MEDIA_ROOT = str(_WRITABLE_DIR / "media")
MEDIA_URL = "/media/"

# ADMIN
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# EMAIL
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# LOGGING — Full traceback capture for debugging EXE issues
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
        "traceback": {
            "format": "%(levelname)s %(asctime)s\n%(message)s\n",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": env("DJANGO_LOG_FILE", default=str(_WRITABLE_DIR / "deployment" / "logs" / "django.log")),
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_WRITABLE_DIR / "deployment" / "logs" / "django_error.log"),
            "maxBytes": 20971520,
            "backupCount": 10,
            "formatter": "traceback",
        },
    },
    "root": {"level": "INFO", "handlers": ["console", "file", "error_file"]},
    "loggers": {
        "django": {
            "level": "INFO",
            "handlers": ["file", "error_file"],
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["error_file"],
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console", "file", "error_file"],
            "propagate": True,
        },
    },
}

# django-allauth (from base)
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
ACCOUNT_EMAIL_VERIFICATION = env("DJANGO_ACCOUNT_EMAIL_VERIFICATION", default="none")

# Remove MFA — fido2 WebAuthn data file (public_suffix_list.dat) causes
# ImportError in PyInstaller frozen builds. MFA is unnecessary on LAN.
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "allauth.mfa"]
