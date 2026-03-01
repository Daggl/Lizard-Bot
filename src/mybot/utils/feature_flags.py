"""Per-guild feature flag system.

Each guild has a ``features.json`` config file that stores boolean toggles
for individual bot features.  When a feature is not present in the config
it defaults to **enabled** (True) so new guilds get everything active.
"""

from .config import load_cog_config

# Canonical list of toggleable features with their internal key names.
FEATURES = {
    "leveling":     "Leveling / XP / Rank system",
    "achievements": "Achievement system",
    "birthdays":    "Birthday reminders",
    "polls":        "Poll / voting system",
    "counting":     "Counting channel game",
    "welcome":      "Welcome messages & autorole",
    "tickets":      "Ticket / support system",
    "tempvoice":    "Temporary voice channels",
    "music":        "Music playback",
    "logging":      "Server logging (chat, voice, mod, member, server)",
    "memes":        "Meme storage & retrieval",
    "membercount":  "Member count display channel",
}

# Mapping: Cog class name → feature key.
# Used by the global command check to block commands when a feature is disabled.
COG_FEATURE_MAP = {
    # Leveling family
    "Levels":       "leveling",
    "Rank":         "leveling",
    "Rewards":      "leveling",
    "Tracking":     "leveling",
    # Achievements
    "Achievements": "achievements",
    # Community
    "Birthdays":    "birthdays",
    "Poll":         "polls",
    "Count":        "counting",
    "Memes":        "memes",
    # Welcome / Autorole
    "Welcome":      "welcome",
    "AutoRole":     "welcome",
    # Tickets
    "TicketCog":    "tickets",
    # Voice
    "TempVoice":    "tempvoice",
    # Media  (Music cog uses name="music")
    "music":        "music",
    "Music":        "music",
    # Logging
    "ChatLog":      "logging",
    "ModLog":       "logging",
    "MemberLog":    "logging",
    "VoiceLog":     "logging",
    "ServerLog":    "logging",
    # Member count
    "MemberCount":  "membercount",
}


def is_feature_enabled(guild_id, feature_key: str) -> bool:
    """Return whether *feature_key* is enabled for *guild_id*.

    Missing keys default to ``True`` (enabled).
    """
    if guild_id is None:
        return True
    cfg = load_cog_config("features", guild_id=guild_id)
    return bool(cfg.get(feature_key, True))


def get_all_feature_flags(guild_id) -> dict:
    """Return a dict of ``{feature_key: bool}`` for the guild.

    Missing keys are filled with ``True`` (default enabled).
    """
    cfg = load_cog_config("features", guild_id=guild_id) if guild_id else {}
    return {key: bool(cfg.get(key, True)) for key in FEATURES}


def feature_key_for_cog(cog_name: str) -> str | None:
    """Return the feature key for a cog name, or None if not mapped."""
    return COG_FEATURE_MAP.get(cog_name)
