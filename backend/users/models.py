from __future__ import annotations

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
