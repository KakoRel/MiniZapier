from __future__ import annotations

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def _ensure_site(sender, **kwargs):
    if "django.contrib.sites" not in settings.INSTALLED_APPS:
        return

    try:
        from django.contrib.sites.models import Site
    except Exception:
        return

    domain = getattr(settings, "SITE_DOMAIN", None) or "localhost"
    name = getattr(settings, "SITE_NAME", None) or "MiniZapier"

    Site.objects.update_or_create(
        id=settings.SITE_ID,
        defaults={"domain": domain, "name": name},
    )


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        post_migrate.connect(_ensure_site, dispatch_uid="users.ensure_site")

from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'
