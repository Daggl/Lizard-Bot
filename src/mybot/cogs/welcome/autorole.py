import os
import sqlite3

from discord.ext import commands

from mybot.utils.config import load_cog_config

# ==========================================================
# CONFIG (loaded from config/autorole.json with fallbacks)
# ==========================================================


_CFG = load_cog_config("autorole")

VERIFY_CHANNEL_ID = _CFG.get("VERIFY_CHANNEL_ID", 0)
RULES_CHANNEL_ID = _CFG.get("RULES_CHANNEL_ID", 0)

STARTER_ROLE_ID = _CFG.get("STARTER_ROLE_ID", 0)
VERIFY_ROLE_ID = _CFG.get("VERIFY_ROLE_ID", 0)
DEFAULT_ROLE_ID = _CFG.get("DEFAULT_ROLE_ID", 0)

VERIFY_MESSAGE_IDS = _CFG.get("VERIFY_MESSAGE_IDS", [])
RULES_MESSAGE_IDS = _CFG.get("RULES_MESSAGE_IDS", [])

EMOJI = _CFG.get("EMOJI", "✅")

DB_PATH = _CFG.get("DB_PATH", "data/autorole.db")

# ==========================================================
# DATABASE
# ==========================================================


def setup_database():

    db_dir = os.path.dirname(DB_PATH) or "."
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
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
    conn.close()


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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        guild = member.guild

        # Verify Role
        cursor.execute(
            "SELECT user_id FROM verified_users WHERE user_id = ?", (member.id,)
        )

        if cursor.fetchone():

            role = guild.get_role(VERIFY_ROLE_ID)

            if role:
                await member.add_roles(role)
                print(f"[RESTORE] Verify Role → {member}")

        # Default Role
        cursor.execute(
            "SELECT user_id FROM rules_accepted WHERE user_id = ?", (member.id,)
        )

        if cursor.fetchone():

            role = guild.get_role(DEFAULT_ROLE_ID)

            if role:
                await member.add_roles(role)
                print(f"[RESTORE] Default Role → {member}")

        conn.close()

    # ======================================================
    # REACTION ADD
    # ======================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):

        if str(payload.emoji) != EMOJI:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        member = guild.get_member(payload.user_id)

        if not member or member.bot:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # VERIFY ROLE

        if (
            payload.channel_id == VERIFY_CHANNEL_ID
            and payload.message_id in VERIFY_MESSAGE_IDS
        ):

            role = guild.get_role(VERIFY_ROLE_ID)

            if role and role not in member.roles:

                await member.add_roles(role)

                cursor.execute(
                    "INSERT OR IGNORE INTO verified_users VALUES (?)", (member.id,)
                )

                conn.commit()

                print(f"[VERIFY ADD] {member}")

                # REMOVE STARTER ROLE

                starter_role = guild.get_role(STARTER_ROLE_ID)

                if starter_role and starter_role in member.roles:

                    await member.remove_roles(starter_role)

                    print(f"[STARTER REMOVE] {member}")

        # DEFAULT ROLE

        if (
            payload.channel_id == RULES_CHANNEL_ID
            and payload.message_id in RULES_MESSAGE_IDS
        ):

            role = guild.get_role(DEFAULT_ROLE_ID)

            if role and role not in member.roles:

                await member.add_roles(role)

                cursor.execute(
                    "INSERT OR IGNORE INTO rules_accepted VALUES (?)", (member.id,)
                )

                conn.commit()

                print(f"[DEFAULT ADD] {member}")

        conn.close()

    # ======================================================
    # REACTION REMOVE
    # ======================================================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):

        if str(payload.emoji) != EMOJI:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        member = guild.get_member(payload.user_id)

        if not member:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # VERIFY ROLE REMOVE

        if (
            payload.channel_id == VERIFY_CHANNEL_ID
            and payload.message_id in VERIFY_MESSAGE_IDS
        ):

            role = guild.get_role(VERIFY_ROLE_ID)

            if role and role in member.roles:

                await member.remove_roles(role)

                cursor.execute(
                    "DELETE FROM verified_users WHERE user_id = ?", (member.id,)
                )

                conn.commit()

                print(f"[VERIFY REMOVE] {member}")

        # DEFAULT ROLE REMOVE

        if (
            payload.channel_id == RULES_CHANNEL_ID
            and payload.message_id in RULES_MESSAGE_IDS
        ):

            role = guild.get_role(DEFAULT_ROLE_ID)

            if role and role in member.roles:

                await member.remove_roles(role)

                cursor.execute(
                    "DELETE FROM rules_accepted WHERE user_id = ?", (member.id,)
                )

                conn.commit()

                print(f"[DEFAULT REMOVE] {member}")

        conn.close()


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):

    await bot.add_cog(AutoRole(bot))
