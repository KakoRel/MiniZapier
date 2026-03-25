from __future__ import annotations

from django.contrib import admin

from .models import EmailSendLog


@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "status", "subject", "from_email")
    list_filter = ("status", "created_at")
    search_fields = ("subject", "from_email", "error")
    readonly_fields = ("created_at",)

from django.contrib import admin

# Register your models here.
