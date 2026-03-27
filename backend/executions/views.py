from __future__ import annotations

import json
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
    workflows_qs = Execution.objects.filter(workflow__user=request.user).values("workflow_id", "workflow__name").distinct()
    workflows = sorted(
        [{"id": row["workflow_id"], "name": row["workflow__name"]} for row in workflows_qs],
        key=lambda x: (x["name"] or "").lower(),
    )

    workflow_id = (request.GET.get("workflow") or "").strip()
    status = (request.GET.get("status") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()

    qs = (
        Execution.objects.filter(workflow__user=request.user, start_time__gte=since)
        .select_related("workflow")
        .prefetch_related("steps")
        .order_by("-start_time")
    )
    if workflow_id.isdigit():
        qs = qs.filter(workflow_id=int(workflow_id))
    if status in {Execution.STATUS_RUNNING, Execution.STATUS_SUCCESS, Execution.STATUS_FAILED}:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(start_time__date__gte=date_from)
    if date_to:
        qs = qs.filter(start_time__date__lte=date_to)

    stats = qs.values("status").annotate(count=Count("id"))
    stats_map = {row["status"]: row["count"] for row in stats}

    return render(
        request,
        "executions/executions_list.html",
        {
            "executions": qs,
            "days": days,
            "stats_map": stats_map,
            "workflows": workflows,
            "filter_workflow": workflow_id,
            "filter_status": status,
            "filter_date_from": date_from,
            "filter_date_to": date_to,
        },
    )


@login_required
def execution_detail(request, execution_id: int):
    execution = get_object_or_404(
        Execution.objects.select_related("workflow"),
        pk=execution_id,
        workflow__user=request.user,
    )
    raw_steps = list(execution.steps.all().order_by("id"))
    steps = []
    for step in raw_steps:
        step.input_pretty = json.dumps(step.input_data, ensure_ascii=False, indent=2, default=str)
        step.output_pretty = json.dumps(step.output_data, ensure_ascii=False, indent=2, default=str)
        steps.append(step)
    return render(
        request,
        "executions/execution_detail.html",
        {
            "execution": execution,
            "steps": steps,
        },
    )
