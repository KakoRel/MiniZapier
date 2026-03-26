from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Execution


@login_required
def executions_list(request):
    days = 30
    since = timezone.now() - timedelta(days=days)

    qs = (
        Execution.objects.filter(workflow__user=request.user, start_time__gte=since)
        .select_related("workflow")
        .prefetch_related("steps")
        .order_by("-start_time")
    )

    stats = qs.values("status").annotate(count=Count("id"))
    stats_map = {row["status"]: row["count"] for row in stats}

    return render(
        request,
        "executions/executions_list.html",
        {
            "executions": qs,
            "days": days,
            "stats_map": stats_map,
        },
    )


@login_required
def execution_detail(request, execution_id: int):
    execution = get_object_or_404(
        Execution.objects.select_related("workflow"),
        pk=execution_id,
        workflow__user=request.user,
    )
    steps = list(execution.steps.all().order_by("id"))
    return render(
        request,
        "executions/execution_detail.html",
        {
            "execution": execution,
            "steps": steps,
        },
    )
