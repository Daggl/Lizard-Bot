"""One-time migration: convert old rank.json keys to new per-element keys.

Old keys  →  New keys mapping:
  NAME_FONT       → USERNAME_FONT
  NAME_FONT_SIZE  → USERNAME_FONT_SIZE
  NAME_COLOR      → USERNAME_COLOR
  INFO_FONT       → LEVEL_FONT, XP_FONT, MESSAGES_FONT, VOICE_FONT, ACHIEVEMENTS_FONT
  INFO_FONT_SIZE  → LEVEL_FONT_SIZE  (XP/MESSAGES/VOICE/ACHIEVEMENTS default to 33)
  INFO_COLOR      → LEVEL_COLOR, XP_COLOR, MESSAGES_COLOR, VOICE_COLOR, ACHIEVEMENTS_COLOR
  TEXT_OFFSET_X/Y → applied to all element X/Y positions
  AVATAR_OFFSET_X/Y → applied to AVATAR_X/Y
  BAR_COLOR       → BAR_FILL_COLOR

Preserved as-is: BG_PATH, BG_MODE, BG_ZOOM, BG_OFFSET_X, BG_OFFSET_Y, EXAMPLE_NAME
"""

import json
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
GUILDS_DIR = os.path.join(REPO_ROOT, "config", "guilds")

# Default positions (must match rank.py DEFAULT_POS)
DEFAULT_POS = {
    "avatar_x": 75,
    "avatar_y": 125,
    "username_x": 400,
    "username_y": 80,
    "level_x": 400,
    "level_y": 200,
    "xp_x": 1065,
    "xp_y": 270,
    "bar_x": 400,
    "bar_y": 330,
    "messages_x": 400,
    "messages_y": 400,
    "voice_x": 680,
    "voice_y": 400,
    "achievements_x": 980,
    "achievements_y": 400,
}

AVATAR_SIZE = 300
BAR_WIDTH = 900
BAR_HEIGHT = 38

FONT_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_REGULAR = "assets/fonts/Poppins-Regular.ttf"


def migrate(cfg: dict) -> dict:
    """Return a new dict with old keys converted to new per-element keys."""
    new = {}

    # ── pass-through keys ──
    for key in ("BG_PATH", "BG_MODE", "BG_ZOOM", "BG_OFFSET_X", "BG_OFFSET_Y", "EXAMPLE_NAME"):
        if key in cfg:
            new[key] = cfg[key]

    # ── legacy offsets ──
    text_off_x = int(cfg.get("TEXT_OFFSET_X", 0) or 0)
    text_off_y = int(cfg.get("TEXT_OFFSET_Y", 0) or 0)
    avatar_off_x = int(cfg.get("AVATAR_OFFSET_X", 0) or 0)
    avatar_off_y = int(cfg.get("AVATAR_OFFSET_Y", 0) or 0)

    # ── legacy font / color values ──
    name_font = cfg.get("NAME_FONT", FONT_BOLD)
    name_size = cfg.get("NAME_FONT_SIZE", 90)
    name_color = cfg.get("NAME_COLOR", "#FFFFFF")
    info_font = cfg.get("INFO_FONT", FONT_REGULAR)
    info_size = cfg.get("INFO_FONT_SIZE", 60)
    info_color = cfg.get("INFO_COLOR", "#C8C8C8")

    # ── Avatar ──
    new["AVATAR_X"] = cfg.get("AVATAR_X", DEFAULT_POS["avatar_x"] + avatar_off_x)
    new["AVATAR_Y"] = cfg.get("AVATAR_Y", DEFAULT_POS["avatar_y"] + avatar_off_y)
    new["AVATAR_SIZE"] = cfg.get("AVATAR_SIZE", AVATAR_SIZE)

    # ── Username ──
    new["USERNAME_FONT"] = cfg.get("USERNAME_FONT", name_font)
    new["USERNAME_FONT_SIZE"] = cfg.get("USERNAME_FONT_SIZE", name_size)
    new["USERNAME_COLOR"] = cfg.get("USERNAME_COLOR", name_color)
    new["USERNAME_X"] = cfg.get("USERNAME_X", DEFAULT_POS["username_x"] + text_off_x)
    new["USERNAME_Y"] = cfg.get("USERNAME_Y", DEFAULT_POS["username_y"] + text_off_y)

    # ── Level ──
    new["LEVEL_FONT"] = cfg.get("LEVEL_FONT", info_font)
    new["LEVEL_FONT_SIZE"] = cfg.get("LEVEL_FONT_SIZE", info_size)
    new["LEVEL_COLOR"] = cfg.get("LEVEL_COLOR", info_color)
    new["LEVEL_X"] = cfg.get("LEVEL_X", DEFAULT_POS["level_x"] + text_off_x)
    new["LEVEL_Y"] = cfg.get("LEVEL_Y", DEFAULT_POS["level_y"] + text_off_y)

    # ── XP ──
    new["XP_FONT"] = cfg.get("XP_FONT", info_font)
    new["XP_FONT_SIZE"] = cfg.get("XP_FONT_SIZE", 33)
    new["XP_COLOR"] = cfg.get("XP_COLOR", info_color)
    new["XP_X"] = cfg.get("XP_X", DEFAULT_POS["xp_x"] + text_off_x)
    new["XP_Y"] = cfg.get("XP_Y", DEFAULT_POS["xp_y"] + text_off_y)

    # ── Progress Bar ──
    new["BAR_X"] = cfg.get("BAR_X", DEFAULT_POS["bar_x"])
    new["BAR_Y"] = cfg.get("BAR_Y", DEFAULT_POS["bar_y"])
    new["BAR_WIDTH"] = cfg.get("BAR_WIDTH", BAR_WIDTH)
    new["BAR_HEIGHT"] = cfg.get("BAR_HEIGHT", BAR_HEIGHT)
    new["BAR_BG_COLOR"] = cfg.get("BAR_BG_COLOR", "#323232")
    new["BAR_FILL_COLOR"] = cfg.get("BAR_FILL_COLOR", cfg.get("BAR_COLOR", "#8C6EFF"))

    # ── Messages ──
    new["MESSAGES_FONT"] = cfg.get("MESSAGES_FONT", info_font)
    new["MESSAGES_FONT_SIZE"] = cfg.get("MESSAGES_FONT_SIZE", 33)
    new["MESSAGES_COLOR"] = cfg.get("MESSAGES_COLOR", info_color)
    new["MESSAGES_X"] = cfg.get("MESSAGES_X", DEFAULT_POS["messages_x"] + text_off_x)
    new["MESSAGES_Y"] = cfg.get("MESSAGES_Y", DEFAULT_POS["messages_y"] + text_off_y)

    # ── Voice ──
    new["VOICE_FONT"] = cfg.get("VOICE_FONT", info_font)
    new["VOICE_FONT_SIZE"] = cfg.get("VOICE_FONT_SIZE", 33)
    new["VOICE_COLOR"] = cfg.get("VOICE_COLOR", info_color)
    new["VOICE_X"] = cfg.get("VOICE_X", DEFAULT_POS["voice_x"] + text_off_x)
    new["VOICE_Y"] = cfg.get("VOICE_Y", DEFAULT_POS["voice_y"] + text_off_y)

    # ── Achievements ──
    new["ACHIEVEMENTS_FONT"] = cfg.get("ACHIEVEMENTS_FONT", info_font)
    new["ACHIEVEMENTS_FONT_SIZE"] = cfg.get("ACHIEVEMENTS_FONT_SIZE", 33)
    new["ACHIEVEMENTS_COLOR"] = cfg.get("ACHIEVEMENTS_COLOR", info_color)
    new["ACHIEVEMENTS_X"] = cfg.get("ACHIEVEMENTS_X", DEFAULT_POS["achievements_x"] + text_off_x)
    new["ACHIEVEMENTS_Y"] = cfg.get("ACHIEVEMENTS_Y", DEFAULT_POS["achievements_y"] + text_off_y)

    return new


def has_old_keys(cfg: dict) -> bool:
    """Check if config still contains legacy keys."""
    return any(k in cfg for k in (
        "NAME_FONT", "INFO_FONT", "NAME_FONT_SIZE", "INFO_FONT_SIZE",
        "NAME_COLOR", "INFO_COLOR", "TEXT_OFFSET_X", "TEXT_OFFSET_Y",
        "AVATAR_OFFSET_X", "AVATAR_OFFSET_Y", "BAR_COLOR",
    ))


def main():
    if not os.path.isdir(GUILDS_DIR):
        print(f"No guilds directory found at {GUILDS_DIR}")
        return

    guild_dirs = [
        d for d in os.listdir(GUILDS_DIR)
        if os.path.isdir(os.path.join(GUILDS_DIR, d)) and d != ".gitkeep"
    ]

    migrated = 0
    skipped = 0

    for guild_id in sorted(guild_dirs):
        rank_path = os.path.join(GUILDS_DIR, guild_id, "rank.json")
        if not os.path.isfile(rank_path):
            continue

        with open(rank_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)

        if not has_old_keys(cfg):
            print(f"  [{guild_id}] Already migrated – skipping")
            skipped += 1
            continue

        # Create backup
        backup_path = rank_path + ".bak"
        shutil.copy2(rank_path, backup_path)
        print(f"  [{guild_id}] Backup → {backup_path}")

        new_cfg = migrate(cfg)

        with open(rank_path, "w", encoding="utf-8") as fh:
            json.dump(new_cfg, fh, indent=2, ensure_ascii=False)
        print(f"  [{guild_id}] Migrated ({len(cfg)} old keys → {len(new_cfg)} new keys)")
        migrated += 1

    # Also handle global config/rank.json if present
    global_rank = os.path.join(REPO_ROOT, "config", "rank.json")
    if os.path.isfile(global_rank):
        with open(global_rank, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        if has_old_keys(cfg):
            shutil.copy2(global_rank, global_rank + ".bak")
            new_cfg = migrate(cfg)
            with open(global_rank, "w", encoding="utf-8") as fh:
                json.dump(new_cfg, fh, indent=2, ensure_ascii=False)
            print(f"  [global] Migrated config/rank.json")
            migrated += 1
        else:
            print(f"  [global] Already migrated – skipping")
            skipped += 1

    print(f"\nDone. Migrated: {migrated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
