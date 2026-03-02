"""Repository path resolution and runtime directory/database bootstrapping."""

import json
import os
import shutil
import sqlite3


def repo_root_candidates(path: str):
    """Yield parent directories from *path* up to the filesystem root."""
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    for i in range(len(parts), 0, -1):
        yield os.sep.join(parts[:i])


def find_repo_root() -> str:
    """Locate the project root by searching for ``data/config.example.json``."""
    env_root = os.environ.get("DC_BOT_REPO_ROOT")
    if env_root:
        try:
            abs_env = os.path.abspath(env_root)
            if os.path.exists(os.path.join(abs_env, "data", "config.example.json")):
                return abs_env
        except Exception:
            pass

    here = os.path.abspath(os.path.dirname(__file__))
    # package path: src/mybot/utils -> climb up 3 levels
    cand = os.path.abspath(os.path.join(here, "..", "..", ".."))
    if os.path.exists(os.path.join(cand, "data", "config.example.json")):
        return cand

    # fallback: climb until we find a strong repo marker
    for c in repo_root_candidates(here):
        if os.path.exists(os.path.join(c, "data", "config.example.json")) or os.path.exists(
            os.path.join(c, "setup.cfg")
        ):
            return c
    return cand


REPO_ROOT = find_repo_root()

DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_DIR = os.path.join(DATA_DIR, "db")
TICKETS_DIR = os.path.join(DATA_DIR, "tickets")
TICKET_TRANSCRIPTS = os.path.join(TICKETS_DIR, "transcripts")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
CONFIG_DIR = os.path.join(REPO_ROOT, "config")
GUILDS_DIR = os.path.join(CONFIG_DIR, "guilds")


def guild_data_path(guild_id: int | str | None, filename: str) -> str:
    """Return the path to a guild-specific data file in config/guilds/{guild_id}/{filename}.
    
    If guild_id is None, returns empty string (no global fallback).
    Creates the guild directory if it doesn't exist.
    """
    if guild_id is None:
        return ""
    gid = str(guild_id)
    guild_dir = os.path.join(GUILDS_DIR, gid)
    os.makedirs(guild_dir, exist_ok=True)
    return os.path.join(guild_dir, filename)


# ---------------------------------------------------------------------------
# Default templates for per-guild JSON files
# ---------------------------------------------------------------------------

# Config files – created from data/config.example.json sections
_CONFIG_DEFAULTS: dict[str, dict] = {
    "welcome.json": {
        "VERIFY_CHANNEL_ID": 0,
        "WELCOME_CHANNEL_ID": 0,
        "RULES_CHANNEL_ID": 0,
        "ABOUTME_CHANNEL_ID": 0,
        "ROLE_ID": 0,
        "BANNER_PATH": "",
        "BG_MODE": "",
        "BG_ZOOM": 0,
        "BG_OFFSET_X": 0,
        "BG_OFFSET_Y": 0,
        "FONT_WELCOME": "",
        "FONT_USERNAME": "",
        "BANNER_TITLE": "",
        "TITLE_FONT_SIZE": 0,
        "USERNAME_FONT_SIZE": 0,
        "TITLE_COLOR": "",
        "USERNAME_COLOR": "",
        "TITLE_OFFSET_X": 0,
        "TITLE_OFFSET_Y": 0,
        "USERNAME_OFFSET_X": 0,
        "USERNAME_OFFSET_Y": 0,
        "TEXT_OFFSET_X": 0,
        "TEXT_OFFSET_Y": 0,
        "OFFSET_X": 0,
        "OFFSET_Y": 0,
        "EXAMPLE_NAME": "",
        "WELCOME_MESSAGE": "",
        "FIT_MODE": "",
        "FONT_FAMILY": "",
        "FONT_SIZE": 0,
        "FONT_COLOR": "",
        "ALIGN": "",
        "OPACITY": 0,
        "OVERLAY_TEXT": False,
    },
    "autorole.json": {
        "VERIFY_CHANNEL_ID": 0,
        "RULES_CHANNEL_ID": 0,
        "STARTER_ROLE_ID": 0,
        "VERIFY_ROLE_ID": 0,
        "DEFAULT_ROLE_ID": 0,
        "VERIFY_MESSAGE_IDS": [],
        "RULES_MESSAGE_IDS": [],
        "EMOJI": "",
        "DB_PATH": "data/db/autorole.db",
    },
    "tempvoice.json": {
        "ENABLED": False,
        "CATEGORY_ID": 0,
        "CREATE_CHANNEL_ID": 0,
        "CONTROL_CHANNEL_ID": 0,
        "CHANNEL_NAME_TEMPLATE": "",
        "DEFAULT_USER_LIMIT": 0,
    },
    "tickets.json": {
        "TICKET_CATEGORY_ID": 0,
        "SUPPORT_ROLE_ID": 0,
        "TICKET_LOG_CHANNEL_ID": 0,
    },
    "log_chat.json": {"CHANNEL_ID": 0},
    "log_mod.json": {"CHANNEL_ID": 0},
    "log_member.json": {"CHANNEL_ID": 0},
    "log_voice.json": {"CHANNEL_ID": 0},
    "log_server.json": {"CHANNEL_ID": 0},
    "leveling.json": {
        "ACHIEVEMENT_CHANNEL_ID": 0,
        "XP_PER_MESSAGE": 0,
        "VOICE_XP_PER_MINUTE": 0,
        "MESSAGE_COOLDOWN": 0,
        "LEVEL_BASE_XP": 0,
        "LEVEL_XP_STEP": 0,
        "LEVEL_UP_MESSAGE_TEMPLATE": "",
        "ACHIEVEMENT_MESSAGE_TEMPLATE": "",
        "LEVEL_REWARDS": {},
        "ACHIEVEMENTS": {},
    },
    "count.json": {
        "COUNT_CHANNEL_ID": 0,
        "MIN_COUNT_FOR_RECORD": 0,
    },
    "birthdays.json": {
        "CHANNEL_ID": 0,
        "ROLE_ID": 0,
        "EMBED_TITLE": "",
        "EMBED_DESCRIPTION": "",
        "EMBED_FOOTER": "",
        "EMBED_COLOR": "",
    },
    "freestuff.json": {
        "CHANNEL_ID": 0,
        "SOURCE_EPIC": True,
        "SOURCE_STEAM": True,
        "SOURCE_GOG": True,
        "SOURCE_HUMBLE": True,
        "SOURCE_MISC": True,
    },
    "social_media.json": {
        "TWITCH": {
            "ENABLED": False,
            "CHANNELS": [],
        },
        "YOUTUBE": {
            "ENABLED": False,
            "CHANNELS": [],
        },
        "TWITTER": {
            "ENABLED": False,
            "CHANNELS": [],
        },
        "TIKTOK": {
            "ENABLED": False,
            "CHANNELS": [],
        },
        "INSTAGRAM": {
            "ENABLED": False,
            "CHANNELS": [],
        },
        "CUSTOM": {
            "ENABLED": False,
            "FEED_URLS": "",
            "CHANNELS": [],
        },
    },
    "rank.json": {
        "BG_PATH": "",
        "EXAMPLE_NAME": "",
        "BG_MODE": "cover",
        "BG_ZOOM": 100,
        "BG_OFFSET_X": 0,
        "BG_OFFSET_Y": 0,
        "AVATAR_X": 75,
        "AVATAR_Y": 125,
        "AVATAR_SIZE": 300,
        "USERNAME_X": 400,
        "USERNAME_Y": 80,
        "USERNAME_FONT": "assets/fonts/Poppins-Bold.ttf",
        "USERNAME_FONT_SIZE": 90,
        "USERNAME_COLOR": "#FFFFFF",
        "LEVEL_X": 400,
        "LEVEL_Y": 200,
        "LEVEL_FONT": "assets/fonts/Poppins-Regular.ttf",
        "LEVEL_FONT_SIZE": 60,
        "LEVEL_COLOR": "#C8C8C8",
        "XP_X": 1065,
        "XP_Y": 270,
        "XP_FONT": "assets/fonts/Poppins-Regular.ttf",
        "XP_FONT_SIZE": 33,
        "XP_COLOR": "#C8C8C8",
        "MESSAGES_X": 400,
        "MESSAGES_Y": 400,
        "MESSAGES_FONT": "assets/fonts/Poppins-Regular.ttf",
        "MESSAGES_FONT_SIZE": 33,
        "MESSAGES_COLOR": "#C8C8C8",
        "VOICE_X": 680,
        "VOICE_Y": 400,
        "VOICE_FONT": "assets/fonts/Poppins-Regular.ttf",
        "VOICE_FONT_SIZE": 33,
        "VOICE_COLOR": "#C8C8C8",
        "ACHIEVEMENTS_X": 980,
        "ACHIEVEMENTS_Y": 400,
        "ACHIEVEMENTS_FONT": "assets/fonts/Poppins-Regular.ttf",
        "ACHIEVEMENTS_FONT_SIZE": 33,
        "ACHIEVEMENTS_COLOR": "#C8C8C8",
        "BAR_X": 400,
        "BAR_Y": 330,
        "BAR_WIDTH": 900,
        "BAR_HEIGHT": 38,
        "BAR_BG_COLOR": "#323232",
        "BAR_FILL_COLOR": "#8C6EFF",
    },
    "language.json": {
        "DEFAULT_LANGUAGE": "",
        "GUILD_LANGUAGES": {},
    },
    "welcome_dm.json": {
        "ENABLED": False,
        "MESSAGE": "",
        "EMBED_TITLE": "",
        "EMBED_DESCRIPTION": "",
        "EMBED_COLOR": "#5865F2",
    },
    "membercount.json": {
        "CHANNEL_ID": 0,
        "TEMPLATE": "{count} \ud83d\udc65 Members",
    },
    "features.json": {
        "leveling": True,
        "achievements": True,
        "birthdays": True,
        "polls": True,
        "counting": True,
        "welcome": True,
        "tickets": True,
        "tempvoice": True,
        "music": True,
        "logging": True,
        "memes": True,
        "membercount": True,
        "freestuff": True,
        "socials": True,
        "welcome_dm": True,
    },
    "local_ui.json": {
        "event_test_channel_id": "",
        "safe_read_only": False,
        "safe_debug_logging": False,
        "safe_auto_reload_off": False,
    },
}

# Runtime data files – empty defaults
_DATA_DEFAULTS: dict[str, dict] = {
    "levels_data.json": {},
    "polls_data.json": {},
    "count_data.json": {
        "current": 0,
        "last_user": None,
        "record": 0,
        "record_holder": None,
        "total_counts": {},
        "fails": 0,
    },
    "birthdays_data.json": {},
    "birthdays_sent.json": {},
    "freestuff_data.json": {"posted": []},
    "social_media_data.json": {"twitch": [], "youtube": [], "twitter": [], "tiktok": [], "custom": []},
}

# Combined for convenience
_ALL_GUILD_FILES: dict[str, dict] = {**_CONFIG_DEFAULTS, **_DATA_DEFAULTS}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge *base* defaults into *overlay* without overwriting.

    Only keys missing from *overlay* (at any nesting level) are filled in
    from *base*.  Existing values in *overlay* are never changed.
    """
    merged = dict(overlay)
    for key, default_val in base.items():
        if key not in merged:
            merged[key] = default_val
        elif isinstance(default_val, dict) and isinstance(merged[key], dict):
            merged[key] = _deep_merge(default_val, merged[key])
    return merged


def ensure_guild_configs(guild_id: int | str) -> None:
    """Create or update all expected JSON files for a guild.

    * Missing files are created with full defaults.
    * Existing files are checked for missing top-level (and nested) keys;
      any absent keys are filled in from the template without touching
      values the user has already set.
    """
    gid = str(guild_id)
    guild_dir = os.path.join(GUILDS_DIR, gid)
    os.makedirs(guild_dir, exist_ok=True)

    for filename, default in _ALL_GUILD_FILES.items():
        filepath = os.path.join(guild_dir, filename)
        if not os.path.exists(filepath):
            # File missing — create with full defaults
            try:
                with open(filepath, "w", encoding="utf-8") as fh:
                    json.dump(default, fh, indent=2, ensure_ascii=False)
            except Exception:
                pass
            continue

        # File exists — merge missing keys
        if not isinstance(default, dict) or not default:
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
            if not isinstance(existing, dict):
                existing = {}
            merged = _deep_merge(default, existing)
            if merged != existing:
                with open(filepath, "w", encoding="utf-8") as fh:
                    json.dump(merged, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass


def repo_path(*parts: str) -> str:
    """Join *parts* relative to the repository root."""
    return os.path.join(REPO_ROOT, *parts)


def ensure_dirs() -> None:
    """Create all required runtime directories."""
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(TICKETS_DIR, exist_ok=True)
    os.makedirs(TICKET_TRANSCRIPTS, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def get_db_path(name: str) -> str:
    """Return the path to ``data/db/<name>.db``, ensuring the directory exists."""
    ensure_dirs()
    return os.path.join(DB_DIR, f"{name}.db")


def ensure_runtime_storage() -> None:
    """Create directories and empty database files for logs, tickets and autorole."""
    ensure_dirs()
    for db_name in ("logs", "tickets", "autorole"):
        db_path = get_db_path(db_name)
        if os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            conn.close()
        except Exception:
            pass


def get_ticket_transcript_path(channel_id: int) -> str:
    """Return the file path for a ticket transcript by channel ID."""
    ensure_dirs()
    return os.path.join(TICKET_TRANSCRIPTS, f"{channel_id}.txt")


def migrate_old_paths() -> None:
    """Move legacy database files from old locations to the current layout."""
    ensure_dirs()
    old_logs = os.path.join(REPO_ROOT, "data", "logs", "logs.db")
    new_logs = get_db_path("logs")
    if os.path.exists(old_logs) and not os.path.exists(new_logs):
        try:
            shutil.move(old_logs, new_logs)
        except Exception:
            pass

    old_tickets = os.path.join(REPO_ROOT, "data", "logs", "tickets", "tickets.db")
    new_tickets = get_db_path("tickets")
    if os.path.exists(old_tickets) and not os.path.exists(new_tickets):
        try:
            shutil.move(old_tickets, new_tickets)
        except Exception:
            pass
