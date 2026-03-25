from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Workflow


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
        return redirect("workflow_edit", pk=wf.pk)
    return render(request, "workflows/workflow_form.html")


@login_required
def workflow_edit(request, pk: int):
    wf = get_object_or_404(Workflow, pk=pk, user=request.user)
    editor_payload = {
        "workflowId": wf.pk,
        "workflowName": wf.name,
        "flow_data": wf.flow_data or {},
        "saveUrl": reverse("workflow_save", args=[wf.pk]),
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
