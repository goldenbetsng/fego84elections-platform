"""FEGO '84 Election Voting Platform - Django settings.

Starter implementation for Sprint A/B/C:
- Dockerised Django + Postgres
- Server-rendered UI: Landing, About, Login, Voter Dashboard, Vote Pages
- Django Admin for setup (Sprint D expands to a custom Admin Portal)

Resolved rule:
- Voters cannot edit votes. One vote per voter per post.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    """
    Retrieve an environment variable by name.

    Args:
        name (str): The name of the environment variable.
        default (str | None): Fallback value if the variable is not set.

    Returns:
        str | None: The environment variable value or the default.
    """
    return os.getenv(name, default)


# --- Core ---
SECRET_KEY = env("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = env("DEBUG", "0") == "1"

# development | staging | production
ENVIRONMENT = env("ENVIRONMENT", "development")
IS_PROD = ENVIRONMENT.lower() == "production"

ALLOWED_HOSTS = [h.strip()
                 for h in env("ALLOWED_HOSTS", "*").split(",") if h.strip()]


# --- Apps ---
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "axes",
    "csp",

    # Local
    "accounts",
    "content_blocks",
    "elections",
    "auditlog",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Content Security Policy (Sprint F hardening)
    "csp.middleware.CSPMiddleware",

    # Security
    "axes.middleware.AxesMiddleware",

    # 30-min inactivity logout (VA-08/VA-09)
    "accounts.middleware.InactivityLogoutMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --- Database ---
"""
Railway provides:
- DATABASE_URL (public endpoint – may incur egress fees)
- DATABASE_PRIVATE_URL (internal, no egress)

We always prefer DATABASE_PRIVATE_URL when available.
Fallback:
- DATABASE_URL
- SQLite for local development
"""

DATABASE_URL = env("DATABASE_PRIVATE_URL") or env("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=IS_PROD,
        )
    }
else:
    # Local dev fallback
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# --- Auth ---
AUTH_USER_MODEL = "accounts.User"

# Argon2 preferred (SR-08). Requires argon2-cffi.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "voter_dashboard"
LOGOUT_REDIRECT_URL = "home"


# --- Sessions / inactivity ---
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if IS_PROD:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --- Axes (basic lockout protection) ---
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_TEMPLATE = "registration/locked_out.html"
AXES_LOCKOUT_PARAMETERS = ["ip_address", "user_agent"]


# --- Internationalisation ---
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True


# --- Static files (WhiteNoise + Railway) ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# --- Security headers ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", "same-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Railway / proxy TLS termination
if env("SECURE_PROXY_SSL_HEADER", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if IS_PROD:
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT", "1") == "1"
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", "1") == "1"
    SECURE_HSTS_PRELOAD = env("SECURE_HSTS_PRELOAD", "1") == "1"


# --- Content Security Policy ---
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "base-uri": ("'self'",),
        "default-src": ("'self'",),
        "font-src": ("'self'", "data:"),
        "frame-ancestors": ("'none'",),
        "img-src": ("'self'", "data:"),
        "object-src": ("'none'",),
        "script-src": ("'self'",),
        "style-src": ("'self'", "'unsafe-inline'"),
    }
}


# --- Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"}
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if IS_PROD else "DEBUG",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- REST framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
