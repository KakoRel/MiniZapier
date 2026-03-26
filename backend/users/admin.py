from __future__ import annotations

from django.contrib import admin

from .models import EmailSendLog, UserProfile


@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "status", "subject", "from_email")
    list_filter = ("status", "created_at")
    search_fields = ("subject", "from_email", "error")
    readonly_fields = ("created_at",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__email", "telegram_default_chat_id")
    readonly_fields = ("updated_at",)

# Register your models here.
