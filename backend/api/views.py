from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from executions.models import Execution
from users.models import UserProfile, UserVariable
from workflows.models import Workflow

from .serializers import (
    ExecutionDetailSerializer,
    ExecutionSerializer,
    UserVariableSerializer,
    WorkflowSerializer,
)
from executions.tasks import resume_execution


class WorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workflow.objects.filter(user=self.request.user).select_related("trigger").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Execution.objects.filter(workflow__user=self.request.user)
            .select_related("workflow")
            .prefetch_related("steps")
            .order_by("-start_time")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ExecutionDetailSerializer
        return ExecutionSerializer

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        execution = self.get_queryset().filter(pk=pk).first()
        if not execution:
            return Response({"error": "not_found"}, status=404)
        if execution.status != Execution.STATUS_PAUSED:
            return Response({"ok": False, "status": execution.status})
        resume_execution.delay(execution.pk)
        return Response({"ok": True})


class UserVariableViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserVariableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return UserVariable.objects.filter(profile=profile).order_by("key")

    def perform_create(self, serializer):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)

