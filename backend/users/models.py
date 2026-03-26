from __future__ import annotations

from django.conf import settings
from django.db import models


class EmailSendLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=998, blank=True, default="")
    from_email = models.CharField(max_length=254, blank=True, default="")
    to_emails = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=32, blank=True, default="")
    error = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.status or 'unknown'}: {self.subject[:60]}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    telegram_bot_token = models.CharField(max_length=128, blank=True, default="")
    telegram_default_chat_id = models.CharField(max_length=64, blank=True, default="")
    postgres_dsn = models.CharField(max_length=512, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile for {self.user_id}"
