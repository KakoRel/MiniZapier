from __future__ import annotations

from rest_framework import serializers

from executions.models import Execution, StepResult
from users.models import UserVariable
from workflows.models import Trigger, Workflow


class TriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trigger
        fields = ["type", "config", "updated_at"]


class WorkflowSerializer(serializers.ModelSerializer):
    trigger = TriggerSerializer(read_only=True)

    class Meta:
        model = Workflow
        fields = ["id", "name", "is_active", "flow_data", "created_at", "updated_at", "trigger"]


class ExecutionSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source="workflow.name", read_only=True)

    class Meta:
        model = Execution
        fields = ["id", "workflow", "workflow_name", "status", "start_time", "end_time"]


class StepResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepResult
        fields = ["id", "step_name", "input_data", "output_data", "error_traceback", "created_at"]


class ExecutionDetailSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source="workflow.name", read_only=True)
    steps = StepResultSerializer(many=True, read_only=True)

    class Meta:
        model = Execution
        fields = ["id", "workflow", "workflow_name", "status", "start_time", "end_time", "steps"]


class UserVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVariable
        fields = ["id", "key", "value", "is_secret", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Do not leak secret values via API.
        if instance.is_secret:
            data["value"] = ""
        return data

