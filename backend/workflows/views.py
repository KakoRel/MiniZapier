from __future__ import annotations

import json
import secrets

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from executions.tasks import run_workflow_execution

from .models import Trigger, Workflow


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
    if trigger and trigger.type == Trigger.TYPE_WEBHOOK:
        webhook_secret = (trigger.config or {}).get("secret", "")
    editor_payload = {
        "workflowId": wf.pk,
        "workflowName": wf.name,
        "flow_data": wf.flow_data or {},
        "saveUrl": reverse("workflow_save", args=[wf.pk]),
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
    wf.save(update_fields=["flow_data", "updated_at"])
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def workflow_toggle_active(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    wf.is_active = not wf.is_active
    wf.save(update_fields=["is_active", "updated_at"])
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
