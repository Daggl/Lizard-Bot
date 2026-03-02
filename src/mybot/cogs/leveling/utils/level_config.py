from mybot.utils.config import load_cog_config
from mybot.utils.i18n import resolve_localized_value


def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("leveling", guild_id=guild_id) or {}
    except Exception:
        return {}


def get_message_templates(guild_id: int | None = None):
    """Return (level_up_template, achievement_template) for the guild."""
    cfg = _cfg(guild_id)
    level_up_tpl = resolve_localized_value(cfg.get("LEVEL_UP_MESSAGE_TEMPLATE", ""), guild_id=guild_id)
    achievement_tpl = resolve_localized_value(cfg.get("ACHIEVEMENT_MESSAGE_TEMPLATE", ""), guild_id=guild_id)
    return str(level_up_tpl), str(achievement_tpl)


def get_achievement_channel_id(guild_id: int | str | None = None) -> int:
    try:
        return int(_cfg(guild_id).get("ACHIEVEMENT_CHANNEL_ID", 0) or 0)
    except Exception:
        return 0


def get_levelup_channel_id(guild_id: int | str | None = None) -> int:
    """Return the level-up announcement channel.

    Falls back to ``ACHIEVEMENT_CHANNEL_ID`` when ``LEVEL_UP_CHANNEL_ID``
    is not explicitly configured.
    """
    cfg = _cfg(guild_id)
    try:
        val = cfg.get("LEVEL_UP_CHANNEL_ID")
        if val is not None and val != "" and val != 0:
            return int(val)
    except Exception:
        pass
    return get_achievement_channel_id(guild_id)


def get_xp_per_message(guild_id: int | str | None = None) -> int:
    try:
        val = _cfg(guild_id).get("XP_PER_MESSAGE")
        return int(val) if val is not None and val != "" else 15
    except Exception:
        return 15


def get_voice_xp_per_minute(guild_id: int | str | None = None) -> int:
    try:
        val = _cfg(guild_id).get("VOICE_XP_PER_MINUTE")
        return int(val) if val is not None and val != "" else 5
    except Exception:
        return 5


def get_message_cooldown(guild_id: int | str | None = None) -> int:
    try:
        val = _cfg(guild_id).get("MESSAGE_COOLDOWN")
        return int(val) if val is not None and val != "" else 60
    except Exception:
        return 60


def get_level_base_xp(guild_id: int | str | None = None) -> int:
    """Get XP needed at level 1. Default: 100 (prevents infinite loop)."""
    try:
        val = _cfg(guild_id).get("LEVEL_BASE_XP")
        return int(val) if val is not None and val != "" else 100
    except Exception:
        return 100


def get_level_xp_step(guild_id: int | str | None = None) -> int:
    """XP increase per level. Default: 50 (prevents infinite loop)."""
    try:
        val = _cfg(guild_id).get("LEVEL_XP_STEP")
        return int(val) if val is not None and val != "" else 50
    except Exception:
        return 50

def get_level_rewards(guild_id: int | str | None = None) -> dict:
    """Return ``{int_level: {"name": str, "role_id": int | None}}``.

    Backward-compatible: legacy ``"5": "Bronze"`` entries are normalised to
    ``{"name": "Bronze", "role_id": None}``.
    """
    cfg = _cfg(guild_id)
    raw = cfg.get("LEVEL_REWARDS")
    if not isinstance(raw, dict):
        return {}

    out: dict[int, dict] = {}
    for level_raw, value in raw.items():
        try:
            level = int(level_raw)
        except Exception:
            continue
        if level <= 0:
            continue

        if isinstance(value, dict):
            name = str(value.get("name") or "").strip()
            role_id_raw = value.get("role_id")
            try:
                role_id = int(role_id_raw) if role_id_raw else None
            except (ValueError, TypeError):
                role_id = None
            if name:
                out[level] = {"name": name, "role_id": role_id}
        else:
            # Legacy string format
            name = str(value or "").strip()
            if name:
                out[level] = {"name": name, "role_id": None}
    return out


def get_achievements(guild_id: int | str | None = None) -> dict:
    entries = get_achievement_entries(guild_id)
    return {name: data.get("requirements", {}) for name, data in entries.items()}


def get_achievement_entries(guild_id: int | str | None = None) -> dict:
    cfg = _cfg(guild_id)
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
