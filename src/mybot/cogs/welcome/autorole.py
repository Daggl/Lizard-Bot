"""Auto-role cog — assigns and restores roles on member join and reaction events."""

import logging
import os
import shutil
import sqlite3

from discord.ext import commands

from mybot.utils.config import load_cog_config
from mybot.utils.paths import get_db_path

log = logging.getLogger(__name__)


def _cfg() -> dict:
    try:
        return load_cog_config("autorole") or {}
    except Exception:
        return {}


def _cfg_int(name: str, default: int = 0) -> int:
    try:
        return int(_cfg().get(name, default) or default)
    except Exception:
        return int(default)


def _cfg_list_int(name: str) -> list[int]:
    out = []
    try:
        values = _cfg().get(name, []) or []
        for value in values:
            try:
                out.append(int(value))
            except Exception:
                pass
    except Exception:
        pass
    return out


def _cfg_str(name: str, default: str = "") -> str:
    try:
        return str(_cfg().get(name, default) or default)
    except Exception:
        return default


def _db_path() -> str:
    return _cfg_str("DB_PATH", get_db_path("autorole"))

# ==========================================================
# DATABASE
# ==========================================================


def setup_database():

    db_path = _db_path()
    try:
        default_db = str(get_db_path("autorole") or "")
        legacy_db = os.path.join("data", "autorole.db")
        if default_db and db_path == default_db and os.path.exists(legacy_db) and not os.path.exists(default_db):
            os.makedirs(os.path.dirname(default_db) or ".", exist_ok=True)
            shutil.move(legacy_db, default_db)
    except Exception:
        pass
    db_dir = os.path.dirname(db_path) or "."
    os.makedirs(db_dir, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verified_users (
                user_id INTEGER PRIMARY KEY
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules_accepted (
                user_id INTEGER PRIMARY KEY
            )
        """)

        conn.commit()


# ==========================================================
# COG
# ==========================================================


class AutoRole(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        setup_database()

    # ======================================================
    # MEMBER JOIN → RESTORE ROLES
    # ======================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        db_path = _db_path()
        verify_role_id = _cfg_int("VERIFY_ROLE_ID", 0)
        default_role_id = _cfg_int("DEFAULT_ROLE_ID", 0)

        guild = member.guild

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Verify Role
            cursor.execute(
                "SELECT user_id FROM verified_users WHERE user_id = ?", (member.id,)
            )

            if cursor.fetchone():
                role = guild.get_role(verify_role_id)
                if role:
                    await member.add_roles(role)
                    log.info("Restored verify role for %s", member)

            # Default Role
            cursor.execute(
                "SELECT user_id FROM rules_accepted WHERE user_id = ?", (member.id,)
            )

            if cursor.fetchone():
                role = guild.get_role(default_role_id)
                if role:
                    await member.add_roles(role)
                    log.info("Restored default role for %s", member)

    # ======================================================
    # REACTION ADD
    # ======================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):

        emoji = _cfg_str("EMOJI", "✅")
        verify_channel_id = _cfg_int("VERIFY_CHANNEL_ID", 0)
        rules_channel_id = _cfg_int("RULES_CHANNEL_ID", 0)
        verify_role_id = _cfg_int("VERIFY_ROLE_ID", 0)
        default_role_id = _cfg_int("DEFAULT_ROLE_ID", 0)
        starter_role_id = _cfg_int("STARTER_ROLE_ID", 0)
        verify_message_ids = _cfg_list_int("VERIFY_MESSAGE_IDS")
        rules_message_ids = _cfg_list_int("RULES_MESSAGE_IDS")
        db_path = _db_path()

        if str(payload.emoji) != emoji:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        member = guild.get_member(payload.user_id)

        if not member or member.bot:
            return

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # VERIFY ROLE
            if (
                payload.channel_id == verify_channel_id
                and payload.message_id in verify_message_ids
            ):
                role = guild.get_role(verify_role_id)
                if role and role not in member.roles:
                    await member.add_roles(role)
                    cursor.execute(
                        "INSERT OR IGNORE INTO verified_users VALUES (?)", (member.id,)
                    )
                    conn.commit()
                    log.info("Verify role added for %s", member)

                    # Remove starter role
                    starter_role = guild.get_role(starter_role_id)
                    if starter_role and starter_role in member.roles:
                        await member.remove_roles(starter_role)
                        log.info("Starter role removed for %s", member)

            # DEFAULT ROLE
            if (
                payload.channel_id == rules_channel_id
                and payload.message_id in rules_message_ids
            ):
                role = guild.get_role(default_role_id)
                if role and role not in member.roles:
                    await member.add_roles(role)
                    cursor.execute(
                        "INSERT OR IGNORE INTO rules_accepted VALUES (?)", (member.id,)
                    )
                    conn.commit()
                    log.info("Default role added for %s", member)

    # ======================================================
    # REACTION REMOVE
    # ======================================================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):

        emoji = _cfg_str("EMOJI", "✅")
        verify_channel_id = _cfg_int("VERIFY_CHANNEL_ID", 0)
        rules_channel_id = _cfg_int("RULES_CHANNEL_ID", 0)
        verify_role_id = _cfg_int("VERIFY_ROLE_ID", 0)
        default_role_id = _cfg_int("DEFAULT_ROLE_ID", 0)
        verify_message_ids = _cfg_list_int("VERIFY_MESSAGE_IDS")
        rules_message_ids = _cfg_list_int("RULES_MESSAGE_IDS")
        db_path = _db_path()

        if str(payload.emoji) != emoji:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        member = guild.get_member(payload.user_id)

        if not member:
            return

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # VERIFY ROLE REMOVE
            if (
                payload.channel_id == verify_channel_id
                and payload.message_id in verify_message_ids
            ):
                role = guild.get_role(verify_role_id)
                if role and role in member.roles:
                    await member.remove_roles(role)
                    cursor.execute(
                        "DELETE FROM verified_users WHERE user_id = ?", (member.id,)
                    )
                    conn.commit()
                    log.info("Verify role removed for %s", member)

            # DEFAULT ROLE REMOVE
            if (
                payload.channel_id == rules_channel_id
                and payload.message_id in rules_message_ids
            ):
                role = guild.get_role(default_role_id)
                if role and role in member.roles:
                    await member.remove_roles(role)
                    cursor.execute(
                        "DELETE FROM rules_accepted WHERE user_id = ?", (member.id,)
                    )
                    conn.commit()
                    log.info("Default role removed for %s", member)


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):

    await bot.add_cog(AutoRole(bot))
