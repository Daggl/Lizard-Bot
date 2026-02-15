import discord
from discord.ext import commands
import sqlite3

# ==========================================================
# CONFIG
# ==========================================================

VERIFY_CHANNEL_ID = 1472473174313799803
RULES_CHANNEL_ID = 1266609104005103617

STARTER_ROLE_ID = 1472417667670347817
VERIFY_ROLE_ID = 1472489108969492654
DEFAULT_ROLE_ID = 1269213126356897885

VERIFY_MESSAGE_IDS = [
    1472508232105853054,  # Deutsch
    1472513629550153729   # Englisch
]

RULES_MESSAGE_IDS = [
    1472625130286088244,  # Deutsch
    1472627338587017421   # Englisch
]

EMOJI = "✅"

DB_PATH = "data/autorole.db"

# ==========================================================
# DATABASE
# ==========================================================


def setup_database():

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
            "SELECT user_id FROM verified_users WHERE user_id = ?",
            (member.id,)
        )

        if cursor.fetchone():

            role = guild.get_role(VERIFY_ROLE_ID)

            if role:
                await member.add_roles(role)
                print(f"[RESTORE] Verify Role → {member}")

        
        # Default Role
        cursor.execute(
            "SELECT user_id FROM rules_accepted WHERE user_id = ?",
            (member.id,)
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
                    "INSERT OR IGNORE INTO verified_users VALUES (?)",
                    (member.id,)
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
                    "INSERT OR IGNORE INTO rules_accepted VALUES (?)",
                    (member.id,)
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
                    "DELETE FROM verified_users WHERE user_id = ?",
                    (member.id,)
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
                    "DELETE FROM rules_accepted WHERE user_id = ?",
                    (member.id,)
                )

                conn.commit()

                print(f"[DEFAULT REMOVE] {member}")

        conn.close()


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):

    await bot.add_cog(AutoRole(bot))
