from __future__ import annotations

import json
import re
from urllib import error, request

import psycopg
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
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


def _run_telegram_action(token: str, chat_id: str, text: str, timeout_sec: int = 20) -> dict:
    if not token:
        raise ValueError("Telegram bot token is not configured")
    if not chat_id:
        raise ValueError("Telegram chat_id is not configured")
    if text is None:
        text = ""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = request.Request(url=url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            return {"status_code": resp.getcode(), "response": data}
    except error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {e.code}: {raw[:1000]}") from e


def _split_emails(raw: str) -> list[str]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]


def _run_sql_action(dsn: str, query: str, max_rows: int = 100, timeout_sec: int = 20) -> dict:
    if not dsn:
        raise ValueError("SQL action requires DSN (profile postgres_dsn or config.dsn_override)")
    if not query:
        raise ValueError("SQL action requires query")

    normalized = query.strip()
    # Minimal safety policy for MVP: allow only single SELECT query.
    if ";" in normalized.rstrip(";"):
        raise ValueError("Only single SELECT query is allowed")
    if not re.match(r"^\s*select\b", normalized, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")

    row_limit = max(1, min(int(max_rows or 100), 1000))

    with psycopg.connect(dsn, connect_timeout=timeout_sec) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {int(timeout_sec * 1000)}")
            cur.execute(normalized)
            col_names = [d.name for d in cur.description] if cur.description else []
            rows = cur.fetchmany(row_limit) if col_names else []
    return {"columns": col_names, "rows": rows, "row_count": len(rows), "truncated": len(rows) >= row_limit}


@shared_task(
    bind=True,
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
            retry_max_attempts = int((data.get("config") or {}).get("retry_max_attempts", 1) or 1)

            last_exc: Exception | None = None
            step_output: dict | None = None

            for attempt in range(1, retry_max_attempts + 1):
                try:
                    if kind == "http":
                        step_output = _run_http_action(data.get("config") or {}, step_input)
                    elif kind == "telegram":
                        cfg = data.get("config") or {}
                        profile = getattr(workflow.user, "profile", None)
                        token = (getattr(profile, "telegram_bot_token", "") or "").strip()
                        chat_id = (cfg.get("chat_id") or getattr(profile, "telegram_default_chat_id", "") or "").strip()
                        text_tmpl = str(cfg.get("text") or "")
                        text = text_tmpl.replace("{payload}", json.dumps(step_input, ensure_ascii=False))
                        step_output = _run_telegram_action(token=token, chat_id=chat_id, text=text)
                    elif kind == "email":
                        cfg = data.get("config") or {}
                        to_raw = str(cfg.get("to") or "").strip()
                        subject_tmpl = str(cfg.get("subject") or "")
                        body_tmpl = str(cfg.get("body") or "")
                        payload_str = json.dumps(step_input, ensure_ascii=False)
                        subject = subject_tmpl.replace("{payload}", payload_str)
                        body = body_tmpl.replace("{payload}", payload_str)
                        to_list = _split_emails(to_raw)
                        if not to_list:
                            raise ValueError("Email action requires `config.to`")

                        msg = EmailMessage(
                            subject=subject,
                            body=body,
                            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
                            to=to_list,
                        )
                        sent = msg.send(fail_silently=False)
                        step_output = {"sent": sent, "to": to_list}
                    elif kind == "sql":
                        cfg = data.get("config") or {}
                        profile = getattr(workflow.user, "profile", None)
                        dsn = (cfg.get("dsn_override") or getattr(profile, "postgres_dsn", "") or "").strip()
                        query_tmpl = str(cfg.get("query") or "")
                        query = query_tmpl.replace("{payload}", json.dumps(step_input, ensure_ascii=False))
                        max_rows = int(cfg.get("max_rows") or 100)
                        step_output = _run_sql_action(dsn=dsn, query=query, max_rows=max_rows)
                    else:
                        # Default action: passthrough payload for early-stage workflows.
                        step_output = step_input
                    last_exc = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt >= retry_max_attempts:
                        break

            if last_exc is not None and step_output is None:
                StepResult.objects.create(
                    execution=execution,
                    step_name=label[:200],
                    input_data=step_input,
                    output_data={},
                    error_traceback=str(last_exc),
                )
                execution.status = Execution.STATUS_FAILED
                execution.end_time = timezone.now()
                execution.save(update_fields=["status", "end_time"])
                return execution.pk

            StepResult.objects.create(
                execution=execution,
                step_name=label[:200],
                input_data=step_input,
                output_data=step_output or {},
            )
            context_payload = step_output or {}

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
