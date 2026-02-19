from mybot.utils.config import load_cog_config

_CFG = load_cog_config("leveling")

ACHIEVEMENT_CHANNEL_ID = _CFG.get("ACHIEVEMENT_CHANNEL_ID", 1471988884761088130)

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