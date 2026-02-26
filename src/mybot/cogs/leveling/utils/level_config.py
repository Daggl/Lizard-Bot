from mybot.utils.config import load_cog_config

_CFG = load_cog_config("leveling")

ACHIEVEMENT_CHANNEL_ID = _CFG.get("ACHIEVEMENT_CHANNEL_ID", 0)
EMOJI_WIN = _CFG.get("EMOJI_WIN", "")
EMOJI_HEART = _CFG.get("EMOJI_HEART", "")
LEVEL_UP_MESSAGE_TEMPLATE = _CFG.get(
    "LEVEL_UP_MESSAGE_TEMPLATE",
    "{member_mention}\nyou just reached level {level}!\nkeep it up, cutie!",
)
ACHIEVEMENT_MESSAGE_TEMPLATE = _CFG.get(
    "ACHIEVEMENT_MESSAGE_TEMPLATE",
    "🏆 {member_mention} got Achievement **{achievement_name}**",
)


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
    cfg = load_cog_config("leveling")
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

XP_PER_MESSAGE = _CFG.get("XP_PER_MESSAGE", 15)
VOICE_XP_PER_MINUTE = _CFG.get("VOICE_XP_PER_MINUTE", 10)
MESSAGE_COOLDOWN = _CFG.get("MESSAGE_COOLDOWN", 30)

LEVEL_REWARDS = {
    5: "Bronze",
    10: "Silber",
    20: "Gold",
    30: "Diamond",
    40: "Platinum",
    50: "Master",
    60: "Grandmaster",
    70: "Karl-Heinz",
}

ACHIEVEMENTS = {
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
