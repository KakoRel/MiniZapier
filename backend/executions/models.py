from __future__ import annotations

from django.db import models


class Execution(models.Model):
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    workflow = models.ForeignKey("workflows.Workflow", on_delete=models.CASCADE, related_name="executions")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Execution #{self.pk} for WF #{self.workflow_id} ({self.status})"


class StepResult(models.Model):
    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name="steps")
    step_name = models.CharField(max_length=200)
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_traceback = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.step_name} (exec #{self.execution_id})"
