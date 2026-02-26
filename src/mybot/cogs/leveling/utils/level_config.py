from mybot.utils.config import load_cog_config

_CFG = load_cog_config("leveling")

ACHIEVEMENT_CHANNEL_ID = _CFG.get("ACHIEVEMENT_CHANNEL_ID", 0)
EMOJI_WIN = _CFG.get("EMOJI_WIN", "")
EMOJI_HEART = _CFG.get("EMOJI_HEART", "")
LEVEL_UP_MESSAGE_TEMPLATE = _CFG.get(
    "LEVEL_UP_MESSAGE_TEMPLATE",
    "{emoji_win} {member_mention}\nyou just reached level {level}!\nkeep it up, cutie! {emoji_heart}",
)
ACHIEVEMENT_MESSAGE_TEMPLATE = _CFG.get(
    "ACHIEVEMENT_MESSAGE_TEMPLATE",
    "🏆 {member_mention} got Achievement **{achievement_name}**",
)


def get_message_templates():
    cfg = load_cog_config("leveling")
    level_up_tpl = cfg.get(
        "LEVEL_UP_MESSAGE_TEMPLATE",
        "{emoji_win} {member_mention}\nyou just reached level {level}!\nkeep it up, cutie! {emoji_heart}",
    )
    achievement_tpl = cfg.get(
        "ACHIEVEMENT_MESSAGE_TEMPLATE",
        "🏆 {member_mention} got Achievement **{achievement_name}**",
    )
    return str(level_up_tpl), str(achievement_tpl)

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
