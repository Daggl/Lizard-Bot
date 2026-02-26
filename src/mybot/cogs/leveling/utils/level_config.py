from mybot.utils.config import load_cog_config


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


def get_message_templates():
    cfg = _cfg()
    level_up_tpl = cfg.get(
        "LEVEL_UP_MESSAGE_TEMPLATE",
        "{member_mention}\nyou just reached level {level}!\nkeep it up, cutie!",
    )
    achievement_tpl = cfg.get(
        "ACHIEVEMENT_MESSAGE_TEMPLATE",
        "🏆 {member_mention} got Achievement **{achievement_name}**",
    )
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
        return int(_cfg().get("XP_PER_MESSAGE", 15) or 15)
    except Exception:
        return 15


def get_voice_xp_per_minute() -> int:
    try:
        return int(_cfg().get("VOICE_XP_PER_MINUTE", 10) or 10)
    except Exception:
        return 10


def get_message_cooldown() -> int:
    try:
        return int(_cfg().get("MESSAGE_COOLDOWN", 30) or 30)
    except Exception:
        return 30

DEFAULT_LEVEL_REWARDS = {
    5: "Bronze",
    10: "Silber",
    20: "Gold",
    30: "Diamond",
    40: "Platinum",
    50: "Master",
    60: "Grandmaster",
    70: "Karl-Heinz",
}

DEFAULT_ACHIEVEMENTS = {
    "Chatter I": {"messages": 100},
    "Chatter II": {"messages": 500},
    "Chatter III": {"messages": 1000},
    "Chatter IV": {"messages": 5000},
    "Voice Starter": {"voice_time": 3600},
    "Voice Pro": {"voice_time": 18000},
    "Voice Master": {"voice_time": 36000},
    "Level 5": {"level": 5},
    "Level 10": {"level": 10},
    "Level 25": {"level": 25},
    "Level 50": {"level": 50},
}


def get_level_rewards() -> dict:
    cfg = _cfg()
    raw = cfg.get("LEVEL_REWARDS")
    if not isinstance(raw, dict):
        return dict(DEFAULT_LEVEL_REWARDS)

    out = {}
    for level_raw, role_name in raw.items():
        try:
            level = int(level_raw)
        except Exception:
            continue
        role = str(role_name or "").strip()
        if level > 0 and role:
            out[level] = role
    return out or dict(DEFAULT_LEVEL_REWARDS)


def get_achievements() -> dict:
    cfg = _cfg()
    raw = cfg.get("ACHIEVEMENTS")
    if not isinstance(raw, dict):
        return dict(DEFAULT_ACHIEVEMENTS)

    allowed_keys = {"messages", "voice_time", "level", "xp"}
    out = {}
    for ach_name, requirements in raw.items():
        name = str(ach_name or "").strip()
        if not name or not isinstance(requirements, dict):
            continue
        req_out = {}
        for key, value in requirements.items():
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
            out[name] = req_out
    return out or dict(DEFAULT_ACHIEVEMENTS)


LEVEL_REWARDS = DEFAULT_LEVEL_REWARDS
ACHIEVEMENTS = DEFAULT_ACHIEVEMENTS
