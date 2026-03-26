from __future__ import annotations

import json
import secrets

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from django_celery_beat.models import CrontabSchedule, PeriodicTask

from executions.tasks import run_workflow_execution

from .models import Trigger, Workflow


def _extract_trigger_from_flow(flow_data: dict) -> tuple[str, dict]:
    nodes = flow_data.get("nodes") or []
    trigger_node = None
    for n in nodes:
        if n.get("type") == "input":
            trigger_node = n
            break
        if (n.get("data") or {}).get("kind") == "trigger":
            trigger_node = n
            break

    if not trigger_node:
        return Trigger.TYPE_WEBHOOK, {}

    data = trigger_node.get("data") or {}
    trigger_type = (data.get("triggerType") or Trigger.TYPE_WEBHOOK).strip() or Trigger.TYPE_WEBHOOK
    cron_cfg = data.get("cronConfig") or data.get("cron_config") or {}
    return trigger_type, cron_cfg


def _sync_cron_periodic_task(workflow: Workflow) -> None:
    trigger = getattr(workflow, "trigger", None)
    task_name = f"minizapier-workflow-cron-{workflow.pk}"

    if not trigger or trigger.type != Trigger.TYPE_CRON:
        PeriodicTask.objects.filter(name=task_name).update(enabled=False)
        return

    cfg = trigger.config or {}
    schedule, _ = CrontabSchedule.objects.update_or_create(
        minute=str(cfg.get("minute", "*")),
        hour=str(cfg.get("hour", "*")),
        day_of_week=str(cfg.get("day_of_week", "*")),
        day_of_month=str(cfg.get("day_of_month", "*")),
        month_of_year=str(cfg.get("month_of_year", "*")),
        timezone=settings.TIME_ZONE,
    )

    PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            "task": "executions.tasks.run_workflow_execution",
            "crontab": schedule,
            "args": json.dumps([workflow.pk, {"source": "cron"}]),
            "enabled": bool(workflow.is_active),
        },
    )


def home(request):
    return render(request, "home.html")


@login_required
def workflow_list(request):
    workflows = Workflow.objects.filter(user=request.user)
    return render(request, "workflows/workflow_list.html", {"workflows": workflows})


@login_required
@require_http_methods(["GET", "POST"])
def workflow_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip() or "Без названия"
        wf = Workflow.objects.create(user=request.user, name=name, flow_data={})
        Trigger.objects.create(
            workflow=wf,
            type=Trigger.TYPE_WEBHOOK,
            config={"secret": secrets.token_urlsafe(24)},
        )
        return redirect("workflow_edit", pk=wf.pk)
    return render(request, "workflows/workflow_form.html")


@login_required
def workflow_edit(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    trigger = getattr(wf, "trigger", None)
    webhook_secret = ""
    trigger_type = ""
    cron_cfg = {}
    if trigger:
        trigger_type = trigger.type
        cron_cfg = trigger.config or {}
        if trigger.type == Trigger.TYPE_WEBHOOK:
            webhook_secret = (trigger.config or {}).get("secret", "")
    editor_payload = {
        "workflowId": wf.pk,
        "workflowName": wf.name,
        "flow_data": wf.flow_data or {},
        "saveUrl": reverse("workflow_save", args=[wf.pk]),
        "triggerType": trigger_type,
        "cronConfig": cron_cfg,
        "webhookUrl": request.build_absolute_uri(
            reverse("workflow_webhook", args=[wf.pk, webhook_secret or "missing-secret"])
        ),
    }
    return render(
        request,
        "workflows/editor.html",
        {"workflow": wf, "editor_payload": editor_payload},
    )


@login_required
@require_http_methods(["POST"])
def workflow_save(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    try:
        body = json.loads(request.body.decode())
    except json.JSONDecodeError:
        return JsonResponse({"error": "Некорректный JSON"}, status=400)
    fd = body.get("flow_data")
    if fd is None:
        return JsonResponse({"error": "Нужен ключ flow_data"}, status=400)
    wf.flow_data = fd

    trigger_type, cron_cfg = _extract_trigger_from_flow(fd)
    trigger = getattr(wf, "trigger", None)

    if trigger_type == Trigger.TYPE_WEBHOOK:
        current_secret = (trigger.config or {}).get("secret") if trigger and trigger.type == Trigger.TYPE_WEBHOOK else ""
        if not current_secret:
            current_secret = secrets.token_urlsafe(24)
        if not trigger:
            Trigger.objects.create(
                workflow=wf,
                type=Trigger.TYPE_WEBHOOK,
                config={"secret": current_secret},
            )
        else:
            trigger.type = Trigger.TYPE_WEBHOOK
            trigger.config = {"secret": current_secret}
            trigger.save(update_fields=["type", "config", "updated_at"])

    elif trigger_type == Trigger.TYPE_CRON:
        if not trigger:
            Trigger.objects.create(
                workflow=wf,
                type=Trigger.TYPE_CRON,
                config=cron_cfg or {},
            )
        else:
            trigger.type = Trigger.TYPE_CRON
            trigger.config = cron_cfg or {}
            trigger.save(update_fields=["type", "config", "updated_at"])
    else:
        return JsonResponse({"error": f"Unsupported trigger type: {trigger_type}"}, status=400)

    wf.save(update_fields=["flow_data", "updated_at"])
    _sync_cron_periodic_task(wf)
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def workflow_toggle_active(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    wf.is_active = not wf.is_active
    wf.save(update_fields=["is_active", "updated_at"])
    _sync_cron_periodic_task(wf)
    return redirect("workflow_list")


@login_required
@require_http_methods(["POST"])
def workflow_rename(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return redirect("workflow_edit", pk=wf.pk)
    wf.name = new_name[:200]
    wf.save(update_fields=["name", "updated_at"])
    return redirect("workflow_edit", pk=wf.pk)


@login_required
@require_http_methods(["POST"])
def workflow_delete(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    # Disable periodic task (if any) before deletion.
    PeriodicTask.objects.filter(name=f"minizapier-workflow-cron-{wf.pk}").update(enabled=False)
    wf.delete()
    return redirect("workflow_list")


@require_http_methods(["POST"])
def workflow_webhook(request, pk: int, token: str):
    wf = get_object_or_404(Workflow, pk=pk)
    if not wf.is_active:
        return JsonResponse({"error": "Workflow inactive"}, status=409)

    trigger = getattr(wf, "trigger", None)
    if not trigger or trigger.type != Trigger.TYPE_WEBHOOK:
        return JsonResponse({"error": "Webhook trigger is not configured"}, status=400)

    expected = (trigger.config or {}).get("secret", "")
    if not expected or token != expected:
        return JsonResponse({"error": "Invalid token"}, status=403)

    payload = {}
    if request.body:
        try:
            payload = json.loads(request.body.decode())
        except json.JSONDecodeError:
            return JsonResponse({"error": "Некорректный JSON"}, status=400)

    task = run_workflow_execution.delay(wf.pk, payload)
    return JsonResponse({"queued": True, "task_id": task.id})
