from __future__ import annotations

from django.contrib import admin

from .models import Execution, StepResult


class StepResultInline(admin.TabularInline):
    model = StepResult
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "workflow", "status", "start_time", "end_time")
    list_filter = ("status", "start_time")
    inlines = [StepResultInline]


@admin.register(StepResult)
class StepResultAdmin(admin.ModelAdmin):
    list_display = ("id", "execution", "step_name", "created_at")
    search_fields = ("step_name", "error_traceback")

from django.contrib import admin

# Register your models here.
