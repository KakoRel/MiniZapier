from __future__ import annotations

from django.contrib import admin

from .models import Trigger, Workflow


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "user__email")


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    list_display = ("id", "workflow", "type", "created_at", "updated_at")
    list_filter = ("type", "created_at")

from django.contrib import admin

# Register your models here.
