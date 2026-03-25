from __future__ import annotations

from django.conf import settings
from django.db import models


class Workflow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workflows")
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=False)
    flow_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} (#{self.pk})"


class Trigger(models.Model):
    TYPE_WEBHOOK = "webhook"
    TYPE_CRON = "cron"
    TYPE_EMAIL = "email"

    TYPE_CHOICES = [
        (TYPE_WEBHOOK, "Webhook"),
        (TYPE_CRON, "Cron"),
        (TYPE_EMAIL, "Email"),
    ]

    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE, related_name="trigger")
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.get_type_display()} for {self.workflow_id}"
