from __future__ import annotations

import json
import imaplib
import re
from email import message_from_bytes
from email.header import decode_header
from email.utils import parsedate_to_datetime
from urllib import error, request

import psycopg
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from workflows.models import Trigger, Workflow

from .models import Execution, StepResult


def _index_graph(flow_data: dict) -> tuple[dict[str, dict], dict[str, list[str]], dict[str, list[str]]]:
    nodes = flow_data.get("nodes") or []
    edges = flow_data.get("edges") or []

    node_map = {str(n.get("id")): n for n in nodes if n.get("id")}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_map}
    incoming: dict[str, list[str]] = {node_id: [] for node_id in node_map}
    for e in edges:
        src = str(e.get("source", ""))
        dst = str(e.get("target", ""))
        if src in outgoing and dst in node_map:
            outgoing[src].append(dst)
            incoming[dst].append(src)
    return node_map, outgoing, incoming


def _is_trigger_node(node: dict) -> bool:
    if not node:
        return False
    data = node.get("data") or {}
    return node.get("type") == "input" or data.get("kind") == "trigger"

def _ordered_execution_nodes(
    flow_data: dict,
) -> tuple[list[str], dict[str, dict], dict[str, list[str]], dict[str, list[str]]]:
    node_map, outgoing, incoming = _index_graph(flow_data)
    if not node_map:
        return [], node_map, outgoing, incoming

    trigger_ids: list[str] = []
    for node_id, node in node_map.items():
        if _is_trigger_node(node):
            trigger_ids.append(node_id)
    if not trigger_ids:
        trigger_ids = [next(iter(node_map.keys()))]

    # Reachable nodes from triggers (including trigger nodes themselves).
    reachable: set[str] = set()
    queue = list(trigger_ids)
    seen: set[str] = set(queue)
    while queue:
        current = queue.pop(0)
        for nxt in outgoing.get(current, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            reachable.add(nxt)
            queue.append(nxt)

    # Execution nodes = everything reachable except triggers.
    execution_ids: set[str] = {nid for nid in reachable if not _is_trigger_node(node_map.get(nid))}
    if not execution_ids:
        execution_ids = {nid for nid, n in node_map.items() if not _is_trigger_node(n)}

    # Topological order among execution nodes.
    indegree: dict[str, int] = {nid: 0 for nid in execution_ids}
    for src in execution_ids:
        for dst in outgoing.get(src, []):
            if dst in execution_ids:
                indegree[dst] += 1

    ready = sorted([nid for nid, deg in indegree.items() if deg == 0])
    order: list[str] = []
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        for nxt in outgoing.get(nid, []):
            if nxt not in execution_ids:
                continue
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
        ready.sort()

    # Cycle fallback: append remaining deterministically.
    if len(order) != len(execution_ids):
        remaining = sorted(execution_ids - set(order))
        order.extend(remaining)

    return order, node_map, outgoing, incoming


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


def _safe_json_dumps(value: object) -> str:
    # Django JSONField can serialize datetimes, but we also do our own json.dumps
    # when injecting {payload} into templates. Ensure JSON always succeeds.
    return json.dumps(value, ensure_ascii=False, default=str)


def _to_json_serializable(value: object) -> object:
    # Make arbitrary structures JSON-serializable for Django JSONField.
    # This converts datetime/Decimal/etc. via default=str.
    return json.loads(_safe_json_dumps(value))


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
    result = {"columns": col_names, "rows": rows, "row_count": len(rows), "truncated": len(rows) >= row_limit}
    return _to_json_serializable(result)


def _run_transform_action(config: dict, payload: object) -> dict:
    """
    Safe data transformation without eval:
    - pick_keys: comma-separated top-level keys to keep from payload object
    - constants_json: optional JSON object merged into the result
    """
    base: dict
    if isinstance(payload, dict):
        base = dict(payload)
    else:
        base = {"value": payload}

    pick_keys_raw = str((config or {}).get("pick_keys") or "").strip()
    constants_json_raw = str((config or {}).get("constants_json") or "").strip()

    if pick_keys_raw:
        keys = [k.strip() for k in pick_keys_raw.split(",") if k.strip()]
        out = {k: base.get(k) for k in keys if k in base}
    else:
        out = dict(base)

    if constants_json_raw:
        try:
            constants = json.loads(constants_json_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Transform action: constants_json must be valid JSON object") from exc
        if not isinstance(constants, dict):
            raise ValueError("Transform action: constants_json must be JSON object")
        out.update(constants)

    return _to_json_serializable(out)


def _merge_payloads(payloads: list[object]) -> object:
    ps = [p for p in payloads if p is not None]
    if not ps:
        return {}
    if len(ps) == 1:
        return ps[0]
    if all(isinstance(p, dict) for p in ps):
        merged: dict = {}
        for p in ps:
            merged.update(p)
        return merged
    return ps[-1]


def _decode_mime_words(value: str) -> str:
    if not value:
        return ""
    try:
        parts = decode_header(value)
    except Exception:  # noqa: BLE001
        return value
    out: list[str] = []
    for part, enc in parts:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(part))
    return "".join(out)


def _extract_email_text(msg) -> str:
    """
    Extract best-effort plain text from RFC822 message.
    Falls back to stripped HTML.
    """
    def _decode_part(part) -> str | None:
        payload = part.get_payload(decode=True)
        if payload is None:
            raw = part.get_payload()
            return raw if isinstance(raw, str) else None
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")

    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype == "text/plain" and "attachment" not in disp:
                txt = _decode_part(part)
                if txt:
                    return txt
        # Fallback to html
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if ctype == "text/html" and "attachment" not in disp:
                html_text = _decode_part(part) or ""
                # Remove scripts/styles first.
                html_text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.I | re.S)
                # Strip tags.
                html_text = re.sub(r"<[^>]+>", " ", html_text)
                return re.sub(r"\s+", " ", html_text).strip()
    else:
        ctype = (msg.get_content_type() or "").lower()
        if ctype == "text/plain":
            txt = _decode_part(msg)
            return txt or ""
        if ctype == "text/html":
            html_text = _decode_part(msg) or ""
            html_text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.I | re.S)
            html_text = re.sub(r"<[^>]+>", " ", html_text)
            return re.sub(r"\s+", " ", html_text).strip()
    return ""


def _imap_fetch_unseen(email_cfg: dict) -> tuple[list[tuple[str, dict]], str]:
    """
    Connect to IMAP, fetch up to max_messages unseen emails from mailbox,
    and return list of (seq_id, trigger_payload).
    """
    imap_host = str(email_cfg.get("imap_host") or "").strip()
    username = str(email_cfg.get("username") or "").strip()
    password = str(email_cfg.get("password") or "")
    mailbox = str(email_cfg.get("mailbox") or "INBOX").strip() or "INBOX"
    port = int(email_cfg.get("imap_port") or 993)
    max_messages = int(email_cfg.get("max_messages") or 5)
    max_messages = max(1, min(max_messages, 50))

    if not imap_host or not username or not password:
        raise ValueError("IMAP trigger requires imap_host, username and password")

    imap = imaplib.IMAP4_SSL(imap_host, port)
    try:
        imap.login(username, password)
        imap.select(mailbox)

        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK":
            return [], mailbox

        ids = []
        if data and data[0]:
            ids = data[0].split()

        results: list[tuple[str, dict]] = []
        for seq in ids[:max_messages]:
            typ, msg_data = imap.fetch(seq, "(RFC822)")
            if typ != "OK" or not msg_data:
                continue
            raw_bytes = None
            # msg_data is like [(b'1 (RFC822 {size}', b'...raw...'), b')']
            if isinstance(msg_data[0], tuple) and len(msg_data[0]) >= 2:
                raw_bytes = msg_data[0][1]
            if not raw_bytes:
                continue

            msg = message_from_bytes(raw_bytes)

            from_ = _decode_mime_words(msg.get("From") or "")
            subject = _decode_mime_words(msg.get("Subject") or "")
            date_hdr = msg.get("Date") or ""
            msg_id = msg.get("Message-ID") or ""
            dt = None
            try:
                dt = parsedate_to_datetime(date_hdr) if date_hdr else None
            except Exception:  # noqa: BLE001
                dt = None

            text = _extract_email_text(msg)

            payload = {
                "source": "imap",
                "email": {
                    "from": from_,
                    "subject": subject,
                    "date": dt.isoformat() if dt else date_hdr,
                    "message_id": msg_id,
                    "text": text[:20000],
                },
            }
            results.append((str(seq), payload))

        return results, mailbox
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass


@shared_task(
    bind=True,
)
def run_workflow_execution(self, workflow_id: int, trigger_payload: dict | None = None) -> int:
    workflow = Workflow.objects.get(pk=workflow_id, is_active=True)
    trigger = getattr(workflow, "trigger", None)

    flow_data = workflow.flow_data or {}
    execution_order, node_map, outgoing, incoming = _ordered_execution_nodes(flow_data)

    def _execute_dag_for_payload(one_trigger_payload: dict) -> int:
        execution = Execution.objects.create(workflow=workflow, status=Execution.STATUS_RUNNING)
        outputs: dict[str, object] = {}
        trigger_payload_local = one_trigger_payload or {}
        try:
            if not execution_order:
                StepResult.objects.create(
                    execution=execution,
                    step_name="noop",
                    input_data=trigger_payload_local,
                    output_data={"message": "No action nodes found"},
                )
            for idx, node_id in enumerate(execution_order, start=1):
                node = node_map.get(node_id) or {}
                data = node.get("data") or {}
                label = data.get("label") or f"step-{idx}"
                kind = (data.get("actionType") or "").strip().lower()
                cfg = data.get("config") or {}
                predecessors = incoming.get(node_id, [])
                pred_payloads: list[object] = []
                for pred_id in predecessors:
                    pred_node = node_map.get(pred_id) or {}
                    if _is_trigger_node(pred_node):
                        pred_payloads.append(trigger_payload_local)
                    else:
                        pred_payloads.append(outputs.get(pred_id))
                step_input = _merge_payloads(pred_payloads) if pred_payloads else trigger_payload_local
                retry_max_attempts = int(cfg.get("retry_max_attempts", 1) or 1)
                continue_on_error = bool(cfg.get("continue_on_error", False))

                last_exc: Exception | None = None
                step_output: dict | None = None

                for attempt in range(1, retry_max_attempts + 1):
                    try:
                        if kind == "http":
                            step_output = _run_http_action(cfg, step_input)
                        elif kind == "telegram":
                            profile = getattr(workflow.user, "profile", None)
                            token = (getattr(profile, "telegram_bot_token", "") or "").strip()
                            chat_id = (cfg.get("chat_id") or getattr(profile, "telegram_default_chat_id", "") or "").strip()
                            text_tmpl = str(cfg.get("text") or "")
                            text = text_tmpl.replace("{payload}", _safe_json_dumps(step_input))
                            step_output = _run_telegram_action(token=token, chat_id=chat_id, text=text)
                        elif kind == "email":
                            to_raw = str(cfg.get("to") or "").strip()
                            subject_tmpl = str(cfg.get("subject") or "")
                            body_tmpl = str(cfg.get("body") or "")
                            payload_str = _safe_json_dumps(step_input)
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
                            profile = getattr(workflow.user, "profile", None)
                            dsn = (cfg.get("dsn_override") or getattr(profile, "postgres_dsn", "") or "").strip()
                            query_tmpl = str(cfg.get("query") or "")
                            query = query_tmpl.replace("{payload}", _safe_json_dumps(step_input))
                            max_rows = int(cfg.get("max_rows") or 100)
                            step_output = _run_sql_action(dsn=dsn, query=query, max_rows=max_rows)
                        elif kind == "transform":
                            step_output = _run_transform_action(cfg, step_input)
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
                    if continue_on_error:
                        continued_output = {
                            "continued_on_error": True,
                            "error": str(last_exc),
                            "input": _to_json_serializable(step_input),
                        }
                        StepResult.objects.create(
                            execution=execution,
                            step_name=label[:200],
                            input_data=step_input,
                            output_data=continued_output,
                            error_traceback=str(last_exc),
                        )
                        outputs[node_id] = continued_output
                        continue

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
                outputs[node_id] = step_output or {}

            execution.status = Execution.STATUS_SUCCESS
            execution.end_time = timezone.now()
            execution.save(update_fields=["status", "end_time"])
            return execution.pk
        except Exception as exc:  # noqa: BLE001
            StepResult.objects.create(
                execution=execution,
                step_name="execution-error",
                input_data=trigger_payload_local,
                output_data={},
                error_traceback=str(exc),
            )
            execution.status = Execution.STATUS_FAILED
            execution.end_time = timezone.now()
            execution.save(update_fields=["status", "end_time"])
            raise

    if trigger and trigger.type == Trigger.TYPE_EMAIL:
        # For email trigger, ignore provided trigger_payload and fetch UNSEEN emails instead.
        fetched, _mailbox = _imap_fetch_unseen(trigger.config or {})
        last_pk = 0
        if not fetched:
            return 0

        # Reconnect just to mark seen after successful executions (simple approach for MVP).
        imap_cfg = trigger.config or {}
        imap_host = str(imap_cfg.get("imap_host") or "").strip()
        username = str(imap_cfg.get("username") or "").strip()
        password = str(imap_cfg.get("password") or "")
        mailbox = str(imap_cfg.get("mailbox") or "INBOX").strip() or "INBOX"
        port = int(imap_cfg.get("imap_port") or 993)

        imap = imaplib.IMAP4_SSL(imap_host, port)
        try:
            imap.login(username, password)
            imap.select(mailbox)

            for seq_id, payload in fetched:
                try:
                    execution_pk = _execute_dag_for_payload(payload)
                except Exception:  # noqa: BLE001
                    continue
                last_pk = execution_pk
                if Execution.objects.filter(pk=execution_pk, status=Execution.STATUS_SUCCESS).exists():
                    imap.store(seq_id, "+FLAGS", "\\Seen")
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass

        return last_pk

    trigger_payload_final = trigger_payload or {}
    return _execute_dag_for_payload(trigger_payload_final)
