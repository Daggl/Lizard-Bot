from mybot.utils.config import load_cog_config
from mybot.utils.i18n import resolve_localized_value


def _cfg() -> dict:
    try:
        return load_cog_config("leveling") or {}
    except Exception:
        return {}


def _normalize_emoji_input(raw_value, fallback_name: str) -> str:
    s = str(raw_value or "").strip()
    if not s:
        return ""
    if s.startswith("<:") or s.startswith("<a:"):
        return s
    if s.isdigit():
        return f"<:{fallback_name}:{s}>"
    if s.lower().startswith("a:") and s[2:].isdigit():
        return f"<a:{fallback_name}:{s[2:]}>"
    return s


def get_message_templates(guild_id: int | None = None):
    cfg = _cfg()
    level_up_tpl = resolve_localized_value(cfg.get("LEVEL_UP_MESSAGE_TEMPLATE", ""), guild_id=guild_id)
    achievement_tpl = resolve_localized_value(cfg.get("ACHIEVEMENT_MESSAGE_TEMPLATE", ""), guild_id=guild_id)
    win_emoji = _normalize_emoji_input(cfg.get("EMOJI_WIN", ""), "win")
    heart_emoji = _normalize_emoji_input(cfg.get("EMOJI_HEART", ""), "heart")
    return str(level_up_tpl), str(achievement_tpl), win_emoji, heart_emoji


def get_achievement_channel_id() -> int:
    try:
        return int(_cfg().get("ACHIEVEMENT_CHANNEL_ID", 0) or 0)
    except Exception:
        return 0


def get_xp_per_message() -> int:
    try:
        return int(_cfg().get("XP_PER_MESSAGE") or 0)
    except Exception:
        return 0


def get_voice_xp_per_minute() -> int:
    try:
        return int(_cfg().get("VOICE_XP_PER_MINUTE") or 0)
    except Exception:
        return 0


def get_message_cooldown() -> int:
    try:
        return int(_cfg().get("MESSAGE_COOLDOWN") or 0)
    except Exception:
        return 0


def get_level_base_xp() -> int:
    try:
        return int(_cfg().get("LEVEL_BASE_XP") or 0)
    except Exception:
        return 0


def get_level_xp_step() -> int:
    try:
        return int(_cfg().get("LEVEL_XP_STEP") or 0)
    except Exception:
        return 0

def get_level_rewards() -> dict:
    cfg = _cfg()
    raw = cfg.get("LEVEL_REWARDS")
    if not isinstance(raw, dict):
        return {}

    out = {}
    for level_raw, role_name in raw.items():
        try:
            level = int(level_raw)
        except Exception:
            continue
        role = str(role_name or "").strip()
        if level > 0 and role:
            out[level] = role
    return out


def get_achievements() -> dict:
    entries = get_achievement_entries()
    return {name: data.get("requirements", {}) for name, data in entries.items()}


def get_achievement_entries() -> dict:
    cfg = _cfg()
    raw = cfg.get("ACHIEVEMENTS")
    if not isinstance(raw, dict):
        return {}

    allowed_keys = {"messages", "voice_time", "level", "xp"}
    out = {}
    for ach_name, requirements in raw.items():
        name = str(ach_name or "").strip()
        if not name or not isinstance(requirements, dict):
            continue

        image_value = ""
        req_source = requirements
        if "requirements" in requirements and isinstance(requirements.get("requirements"), dict):
            req_source = requirements.get("requirements") or {}
            image_value = str(requirements.get("image", "") or "").strip()

        req_out = {}
        for key, value in req_source.items():
            key_s = str(key or "").strip()
            if key_s not in allowed_keys:
                continue
            try:
                ivalue = int(value)
            except Exception:
                continue
            if ivalue > 0:
                req_out[key_s] = ivalue
        if req_out:
            out[name] = {"requirements": req_out, "image": image_value}
    return out
