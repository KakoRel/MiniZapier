from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    MAIL_ENABLED=(bool, False),
    POSTGRES_PORT=(int, 5432),
    EMAIL_PORT=(int, 587),
    EMAIL_USE_TLS=(bool, True),
)

# Reads repo-root ".env" (MiniZapier/.env)
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", default="").split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", default="").split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # 3rd-party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_celery_beat",
    # local
    "users.apps.UsersConfig",
    "workflows",
    "executions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="minizapier"),
        "USER": env("POSTGRES_USER", default="minizapier"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="minizapier"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

LOGIN_URL = "/accounts/login/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1
SITE_DOMAIN = env("SITE_DOMAIN", default="localhost")
SITE_NAME = env("SITE_NAME", default="MiniZapier")

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

MAIL_ENABLED = env.bool("MAIL_ENABLED", default=False)
# Вход и регистрация по email + пароль (без username).
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory" if MAIL_ENABLED else "none"
ACCOUNT_FORMS = {
    "login": "users.forms.EmailPasswordLoginForm",
    "signup": "users.forms.EmailPasswordSignupForm",
}

# Почта: MAIL_ENABLED=0 — без SMTP и без подтверждения email (разработка).
# MAIL_ENABLED=1 — обязательное подтверждение и SMTP при заданном EMAIL_HOST.
EMAIL_HOST = env("EMAIL_HOST", default="").strip()
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")

_django_email_backend = env("DJANGO_EMAIL_BACKEND", default="").strip()
if not MAIL_ENABLED:
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
elif _django_email_backend:
    EMAIL_BACKEND = _django_email_backend
elif not EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "users.email_backend.LoggingSMTPEmailBackend"

# Celery / Redis
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
