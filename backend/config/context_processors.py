from __future__ import annotations

from django.conf import settings


def static_version(_request):
    return {"STATIC_VERSION": getattr(settings, "STATIC_VERSION", "1")}

