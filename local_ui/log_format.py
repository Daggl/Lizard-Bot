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

    msg_priority = ("message", "msg", "text", "content", "body", "payload", "data")
    ts_priority = ("created_at", "timestamp", "ts", "time", "date", "created")

    def _extract_message(d):
        for k in msg_priority:
            if k in d and d.get(k) is not None:
                return d.get(k)
        for k in d.keys():
            lk = k.lower()
            if any(x in lk for x in ("message", "text", "content", "body", "payload")):
                return d.get(k)
        return None

    def _extract_timestamp(d):
        for k in ts_priority:
            if k in d and d.get(k) is not None:
                return d.get(k)
        for k in d.keys():
            lk = k.lower()
            if "time" in lk or "date" in lk or lk in ("ts", "timestamp", "created_at", "created"):
                return d.get(k)
        return None

    msg_val = _extract_message(data)
    ts_val = _extract_timestamp(data)

    if msg_val is None:
        try:
            category = str(data.get("category") or "").strip()
            log_type = str(data.get("type") or "").strip()
            user_name = str(data.get("user_name") or "").strip()
            moderator_name = str(data.get("moderator_name") or "").strip()
            channel_name = str(data.get("channel_name") or "").strip()
            parts = []
            if category:
                parts.append(category)
            if log_type:
                parts.append(log_type)
            if user_name:
                parts.append(f"user={user_name}")
            if moderator_name:
                parts.append(f"mod={moderator_name}")
            if channel_name:
                parts.append(f"channel={channel_name}")
            if parts:
                msg_val = " | ".join(parts)
        except Exception:
            pass

    if isinstance(msg_val, str):
        s = msg_val.strip()
        if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
            try:
                inner = json.loads(s)
                if isinstance(inner, dict):
                    m2 = _extract_message(inner)
                    if m2 is not None:
                        msg_val = m2
                    else:
                        msg_val = inner
            except Exception:
                pass

    ts_str = None
    if ts_val is not None:
        try:
            if isinstance(ts_val, (int, float)):
                v = float(ts_val)
                if v > 1e12:
                    v = v / 1000.0
                ts_str = datetime.fromtimestamp(v).isoformat(sep=' ')
            else:
                s = str(ts_val).strip()
                if s.isdigit():
                    v = float(s)
                    if v > 1e12:
                        v = v / 1000.0
                    ts_str = datetime.fromtimestamp(v).isoformat(sep=' ')
                else:
                    try:
                        s2 = s.replace('Z', '+00:00') if s.endswith('Z') else s
                        ts_str = datetime.fromisoformat(s2).isoformat(sep=' ')
                    except Exception:
                        ts_str = s
        except Exception:
            try:
                ts_str = str(ts_val)
            except Exception:
                ts_str = None

    if msg_val is not None:
        try:
            if isinstance(msg_val, (dict, list)):
                m = json.dumps(msg_val, ensure_ascii=False)
            else:
                m = str(msg_val)
            m = m.replace('\n', ' ').strip()
        except Exception:
            m = str(msg_val)
        if ts_str:
            return f"[{ts_str}] {m}"
        return m

    if ts_str:
        try:
            return f"[{ts_str}] {json.dumps(data, ensure_ascii=False)}"
        except Exception:
            return f"[{ts_str}] {str(data)}"

    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return str(data)
