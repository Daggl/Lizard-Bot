# ==========================================================
# IMPORTS
# ==========================================================

import asyncio
import wavelink
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import datetime
import json

# custom database for logs
from data.logs import database


# ==========================================================
# LOAD ENVIRONMENT / TOKEN
# ==========================================================

# loads variables from .env file
load_dotenv()

# Discord bot token from .env
token = os.getenv("DISCORD_TOKEN")


# ==========================================================
# LOGGING SETUP
# ==========================================================

# create log file for Discord events / errors
handler = logging.FileHandler(
    filename="discord.log",
    encoding="utf-8",
    mode="w"
)


# ==========================================================
# BOT SETUP
# ==========================================================

# enable all intents (members, messages, etc.)
intents = discord.Intents.all()

# create bot instance with prefix *
bot = commands.Bot(
    command_prefix="*",
    intents=intents
)


# ==========================================================
# READY EVENT
# ==========================================================

@bot.event
async def on_ready():

    # initialize database
    database.setup()

    # show that bot is online
    print(f"{bot.user.name} is online!")


# ==========================================================
# TEST COMMAND
# ==========================================================

@bot.command()
async def ping(ctx):

    # simple test command to check if bot responds
    await ctx.send("🏓 Pong! all is good in the hood!")


# ==========================================================
# MESSAGE EVENT
# ==========================================================

@bot.event
async def on_message(message):

    # prevent bot from responding to itself
    if message.author == bot.user:
        return

    # required so commands still work
    await bot.process_commands(message)


# ==========================================================
# MAIN FUNCTION
# ==========================================================

async def main():

    # check if token exists
    if not token:

        print(
            "DISCORD_TOKEN not set. "
            "Create a .env file with DISCORD_TOKEN=..."
        )

        return

    # start bot context
    async with bot:

        # ==================================================
        # LOAD COGS
        # ==================================================

        try:
            await bot.load_extension("cogs.birthdays")
        except Exception as e:
            print(f"Error loading cogs.birthdays: {e}")

        try:
            await bot.load_extension("cogs.welcome.welcome")
        except Exception as e:
            print(f"Error loading cogs.welcome.welcome: {e}")

        try:
            await bot.load_extension("cogs.poll")
        except Exception as e:
            print(f"Error loading cogs.poll: {e}")

        try:
            await bot.load_extension("cogs.leveling.levels")
        except Exception as e:
            print(f"Error loading cogs.leveling.levels: {e}")

        try:
            await bot.load_extension("cogs.leveling.rank")
        except Exception as e:
            print(f"Error loading cogs.leveling.rank: {e}")

        try:
            await bot.load_extension("cogs.leveling.achievements")
        except Exception as e:
            print(f"Error loading cogs.leveling.achievements: {e}")

        try:
            await bot.load_extension("cogs.leveling.rewards")
        except Exception as e:
            print(f"Error loading cogs.leveling.rewards: {e}")

        try:
            await bot.load_extension("cogs.leveling.tracking")
        except Exception as e:
            print(f"Error loading cogs.leveling.tracking: {e}")

        try:
            await bot.load_extension("cogs.help_tutorial")
        except Exception as e:
            print(f"Error loading cogs.help_tutorial: {e}")

        try:
            await bot.load_extension("cogs.admin.admin_panel")
        except Exception as e:
            print(f"Error loading cogs.admin.admin_panel: {e}")

        try:
            await bot.load_extension("cogs.admin.admin_tools")
        except Exception as e:
            print(f"Error loading cogs.admin.admin_tools: {e}")

        try:
            await bot.load_extension("cogs.admin.admin_tutorial")
        except Exception as e:
            print(f"Error loading cogs.admin.admin_tutorial: {e}")

        try:
            await bot.load_extension("cogs.count")
        except Exception as e:
            print(f"Error loading cogs.count: {e}")

        try:
            await bot.load_extension("cogs.log.chat_log")
        except Exception as e:
            print(f"Error loading cogs.log.chat_log: {e}")

        try:
            await bot.load_extension("cogs.log.mod_log")
        except Exception as e:
            print(f"Error loading cogs.log.mod_log: {e}")

        try:
            await bot.load_extension("cogs.log.member_log")
        except Exception as e:
            print(f"Error loading cogs.log.member_log: {e}")

        try:
            await bot.load_extension("cogs.log.voice_log")
        except Exception as e:
            print(f"Error loading cogs.log.voice_log: {e}")

        try:
            await bot.load_extension("cogs.log.server_log")
        except Exception as e:
            print(f"Error loading cogs.log.server_log: {e}")

        try:
            await bot.load_extension("cogs.welcome.autorole")
        except Exception as e:
            print(f"Error loading cogs.welcome.autorole: {e}")

        try:
            await bot.load_extension("cogs.say")
        except Exception as e:
            print(f"Error loading cogs.say: {e}")

        try:
            await bot.load_extension("cogs.tickets.ticket")
        except Exception as e:
            print(f"Error loading cogs.tickets.ticket: {e}")

        # ==================================================
        # START BOT
        # ==================================================

        try:

            # connect bot to Discord
            await bot.start(token)

        except asyncio.CancelledError:

            print("Cancelled")
            raise

        except Exception:

            import traceback

            # print full error
            traceback.print_exc()

            # close bot cleanly
            await bot.close()

            raise


# ==========================================================
# SCRIPT START
# ==========================================================

if __name__ == "__main__":

    asyncio.run(main())

    # ======================================================
    # AUTO RESTART PROTECTION
    # ======================================================

    while True:

        try:

            asyncio.run(main())

        except Exception as e:

            print(f"Crash: {e}")

            import time

            time.sleep(5)
