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

import sys

# make `src/` importable so `mybot` package works when present
_root = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(_root, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

# custom database for logs
from data.logs import database

# ensure per-cog config files exist before loading cogs
from utils.config import ensure_configs_from_example


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

@bot.event
async def on_command_error(ctx, error):
    import traceback
    print(f"[CMD ERROR] Error running command {getattr(ctx, 'command', None)}: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)


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

        # Ensure per-cog config files exist (created from config.example.json)
        created = ensure_configs_from_example()
        if created:
            print("Created missing config files:", ", ".join(created))

        # ==================================================
        # LOAD COGS
        # ==================================================

        extensions = [
            "mybot.cogs.birthdays",
            "mybot.cogs.welcome.welcome",
            "mybot.cogs.poll",
            "mybot.cogs.leveling.levels",
            "mybot.cogs.leveling.rank",
            "mybot.cogs.leveling.achievements",
            "mybot.cogs.leveling.rewards",
            "mybot.cogs.leveling.tracking",
            "mybot.cogs.help_tutorial",
            "mybot.cogs.admin.admin_panel",
            "mybot.cogs.admin.admin_tools",
            "mybot.cogs.admin.admin_tutorial",
            "mybot.cogs.count",
            "mybot.cogs.log.chat_log",
            "mybot.cogs.log.mod_log",
            "mybot.cogs.log.member_log",
            "mybot.cogs.log.voice_log",
            "mybot.cogs.log.server_log",
            "mybot.cogs.welcome.autorole",
            "mybot.cogs.say",
            "mybot.cogs.tickets.ticket",
            "mybot.cogs.music",
        ]

        import traceback
        import importlib

        for ext in extensions:

            try:

                # Import the module directly so we can call its setup()
                module = importlib.import_module(ext)

                # If module provides setup(), call it (await if coroutine)
                if hasattr(module, "setup"):

                    try:

                        result = module.setup(bot)

                        if asyncio.iscoroutine(result):
                            await result

                    except Exception:

                        print(f"[COG][ERROR] setup() failed for {ext}:")
                        traceback.print_exc()

                # If there's no setup(), do nothing (silent success)

            except Exception:

                print(f"[COG][FAILED] Could not import {ext}:")
                traceback.print_exc()

        # ==================================================
        # START BOT
        # ==================================================

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
