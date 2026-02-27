import json
from datetime import datetime


def format_db_row(row) -> str:
    try:
        data = dict(row)
    except Exception:
        try:
            return str(tuple(row))
        except Exception:
            return str(row)

    def _pick(*keys):
        for key in keys:
            try:
                val = data.get(key)
                if val is not None and str(val).strip() != "":
                    return val
            except Exception:
                continue
        return None

    def _format_ts(value):
        if value is None:
            return "-"
        try:
            if isinstance(value, (int, float)):
                v = float(value)
                if v > 1e12:
                    v = v / 1000.0
                return datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
            s = str(value).strip()
            if not s:
                return "-"
            if s.isdigit():
                v = float(s)
                if v > 1e12:
                    v = v / 1000.0
                return datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
            s2 = s.replace("Z", "+00:00") if s.endswith("Z") else s
            try:
                return datetime.fromisoformat(s2).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return s
        except Exception:
            return "-"

    def _to_text(value):
        if value is None:
            return "-"
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value).replace("\n", " ").strip() or "-"
        except Exception:
            return "-"

    def _truncate(text: str, max_len: int = 180) -> str:
        value = (text or "-").strip()
        if len(value) <= max_len:
            return value
        return value[: max_len - 1].rstrip() + "…"

    def _marker_for(action_text: str, category_text: str, content_value: str) -> str:
        hay = " ".join([action_text or "", category_text or "", content_value or ""]).lower()
        if any(x in hay for x in ("error", "failed", "exception", "traceback", "denied", "forbidden")):
            return "🔴"
        if any(x in hay for x in ("ban", "kick", "timeout", "mute", "warn", "unban", "mod", "admin")):
            return "🟥"
        if any(x in hay for x in ("ticket", "transcript", "support")):
            return "🟧"
        if any(x in hay for x in ("voice", "tempvoice", "join", "leave", "move")):
            return "🟪"
        if any(x in hay for x in ("message", "chat", "say", "poll", "edit")):
            return "🟦"
        if any(x in hay for x in ("create", "created", "success", "enabled", "start", "open")):
            return "🟩"
        if any(x in hay for x in ("delete", "remove", "close", "disabled", "stop")):
            return "🟨"
        return "⚪"

    def _detect_status(action_text: str, content_value: str):
        hay = " ".join([action_text or "", content_value or ""]).lower()
        if any(x in hay for x in ("error", "failed", "exception", "traceback", "denied", "forbidden", "timeout")):
            return "failed"
        if any(x in hay for x in ("ok", "success", "created", "enabled", "started", "updated", "done")):
            return "ok"
        return "-"

    ts_val = _pick("timestamp", "created_at", "ts", "time", "date", "created")
    user_name = _pick("user_name", "username", "member_name", "moderator_name", "by_name")
    user_id = _pick("user_id", "user", "member_id", "moderator_id", "by")
    moderator_name = _pick("moderator_name", "mod_name", "admin_name", "actor_name", "by_name")
    moderator_id = _pick("moderator_id", "mod_id", "admin_id", "actor_id", "by")

    log_type = _pick("type", "event", "action")
    category = _pick("category")
    action = _to_text(log_type)
    if action == "-" and category is not None:
        action = _to_text(category)
    elif category is not None and str(category).strip():
        action = f"{_to_text(category)}:{action}"

    channel_name = _pick("channel_name", "to_name", "from_name")
    channel_id = _pick("channel_id", "channel", "to", "from")
    if channel_name is not None and channel_id is not None:
        channel = f"{_to_text(channel_name)} ({_to_text(channel_id)})"
    elif channel_name is not None:
        channel = _to_text(channel_name)
    elif channel_id is not None:
        channel = _to_text(channel_id)
    else:
        channel = "-"

    content = _pick("message", "msg", "text", "content", "body", "payload", "data", "extra")
    content_text = _to_text(content)
    if content_text == "-":
        reason = _pick("reason", "details", "detail")
        if reason is not None:
            content_text = _to_text(reason)
    explicit_status = _pick("status", "result", "outcome", "success")

    user_name_text = _to_text(user_name)
    user_id_text = _to_text(user_id)
    action_text = _truncate(action)
    channel_text = _truncate(channel)
    content_text = _truncate(content_text)
    marker = _marker_for(action_text, _to_text(category), content_text)
    action_text = f"{marker} {action_text}"

    mod_name_text = _to_text(moderator_name)
    mod_id_text = _to_text(moderator_id)
    if mod_name_text != "-" and mod_id_text != "-":
        moderator_text = f"{mod_name_text} ({mod_id_text})"
    elif mod_name_text != "-":
        moderator_text = mod_name_text
    elif mod_id_text != "-":
        moderator_text = mod_id_text
    else:
        moderator_text = "-"

    status_text = _to_text(explicit_status)
    if status_text == "-":
        status_text = _detect_status(action_text, content_text)

    fields = [
        ("Time", _format_ts(ts_val)),
        ("Username", user_name_text),
        ("UserID", user_id_text),
        ("Action", action_text),
        ("Channel", channel_text),
        ("Content", content_text),
        ("Moderator", moderator_text),
        ("Status", status_text),
    ]

    key_width = max(len(key) for key, _ in fields)
    lines = [f"{key.ljust(key_width)} | {value}" for key, value in fields]
    separator = "-" * 96
    return "\n".join(lines + [separator])
