from __future__ import annotations

import json
from urllib import error, request

from celery import shared_task
from django.utils import timezone

from workflows.models import Workflow

from .models import Execution, StepResult


def _index_graph(flow_data: dict) -> tuple[dict[str, dict], dict[str, list[str]]]:
    nodes = flow_data.get("nodes") or []
    edges = flow_data.get("edges") or []

    node_map = {str(n.get("id")): n for n in nodes if n.get("id")}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_map}
    for e in edges:
        src = str(e.get("source", ""))
        dst = str(e.get("target", ""))
        if src in outgoing and dst in node_map:
            outgoing[src].append(dst)
    return node_map, outgoing


def _ordered_action_nodes(flow_data: dict) -> list[dict]:
    node_map, outgoing = _index_graph(flow_data)
    if not node_map:
        return []

    trigger_ids = []
    for node_id, node in node_map.items():
        data = node.get("data") or {}
        if node.get("type") == "input" or data.get("kind") == "trigger":
            trigger_ids.append(node_id)
    if not trigger_ids:
        trigger_ids = [next(iter(node_map.keys()))]

    ordered_ids: list[str] = []
    queue = list(trigger_ids)
    seen: set[str] = set()
    while queue:
        current = queue.pop(0)
        for nxt in outgoing.get(current, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            ordered_ids.append(nxt)
            queue.append(nxt)
    return [node_map[node_id] for node_id in ordered_ids]


def _run_http_action(config: dict, payload: dict, timeout_sec: int = 20) -> dict:
    url = (config or {}).get("url", "").strip()
    method = ((config or {}).get("method", "POST") or "POST").upper()
    if not url:
        raise ValueError("HTTP action requires `config.url`")

    req_data = json.dumps(payload).encode()
    req = request.Request(
        url=url,
        data=req_data if method in {"POST", "PUT", "PATCH"} else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "status_code": resp.getcode(),
                "body": body[:5000],
            }
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {raw[:1000]}") from e


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    retry_jitter=True,
)
def run_workflow_execution(self, workflow_id: int, trigger_payload: dict | None = None) -> int:
    workflow = Workflow.objects.get(pk=workflow_id, is_active=True)
    execution = Execution.objects.create(workflow=workflow, status=Execution.STATUS_RUNNING)

    context_payload = trigger_payload or {}
    flow_data = workflow.flow_data or {}
    actions = _ordered_action_nodes(flow_data)

    try:
        if not actions:
            StepResult.objects.create(
                execution=execution,
                step_name="noop",
                input_data=context_payload,
                output_data={"message": "No action nodes found"},
            )
        for idx, node in enumerate(actions, start=1):
            data = node.get("data") or {}
            label = data.get("label") or f"step-{idx}"
            kind = (data.get("actionType") or "").strip().lower()
            step_input = context_payload

            if kind == "http":
                step_output = _run_http_action(data.get("config") or {}, step_input)
            else:
                # Default action: passthrough payload for early-stage workflows.
                step_output = {"passthrough": True, "label": label, "payload": step_input}

            StepResult.objects.create(
                execution=execution,
                step_name=label[:200],
                input_data=step_input,
                output_data=step_output,
            )
            context_payload = step_output

        execution.status = Execution.STATUS_SUCCESS
        execution.end_time = timezone.now()
        execution.save(update_fields=["status", "end_time"])
        return execution.pk
    except Exception as exc:  # noqa: BLE001
        StepResult.objects.create(
            execution=execution,
            step_name="execution-error",
            input_data=context_payload,
            output_data={},
            error_traceback=str(exc),
        )
        execution.status = Execution.STATUS_FAILED
        execution.end_time = timezone.now()
        execution.save(update_fields=["status", "end_time"])
        raise
