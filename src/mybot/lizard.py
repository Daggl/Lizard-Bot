# ==========================================================
# IMPORTS
# ==========================================================

import asyncio
import logging
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ensure project root's `src` is importable (when running as module)
_root = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_src = os.path.join(_project_root, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

# custom database for logs
from data.logs import database  # noqa: E402
# ensure per-cog config files exist before loading cogs
from mybot.utils import sync_cog_configs_from_example  # noqa: E402

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
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")


# ==========================================================
# BOT SETUP
# ==========================================================

# enable all intents (members, messages, etc.)
intents = discord.Intents.all()

# create bot instance with prefix *
bot = commands.Bot(command_prefix="*", intents=intents)


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
        print("DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=...")
        return

    # start bot context
    server_task = None

    # Optionally start local control API
    if os.getenv("LOCAL_UI_ENABLE") == "1":
        control_api_module = None
        try:
            from mybot import control_api as control_api_module
        except Exception:
            try:
                from src.mybot import control_api as control_api_module
            except Exception as e:
                print("Failed to import local UI control API:", e)
                control_api_module = None

        if control_api_module is not None:
            try:
                server_task = asyncio.create_task(control_api_module.serve(bot))
            except Exception as e:
                print("Failed to start local UI control API:", e)

    try:
        async with bot:

            # Ensure per-cog config files exist and missing keys are backfilled
            # from data/config.example.json without overwriting existing values.
            try:
                sync_result = sync_cog_configs_from_example()
                created = sync_result.get("created", [])
                updated = sync_result.get("updated", [])
                if created:
                    print("Created missing config files:", ", ".join(created))
                if updated:
                    print("Backfilled missing config keys:", ", ".join(updated))
            except Exception:
                pass

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

            import importlib
            import traceback

            # track which cogs each extension adds so reloads can remove them precisely
            loaded_extensions = {}

            for ext in extensions:
                try:
                    before = set(bot.cogs.keys())
                    module = importlib.import_module(ext)
                    if hasattr(module, "setup"):
                        try:
                            result = module.setup(bot)
                            if asyncio.iscoroutine(result):
                                await result
                            # record any new cogs added by this extension
                            after = set(bot.cogs.keys())
                            added = sorted(list(after - before))
                            if added:
                                loaded_extensions[ext] = added
                        except Exception:
                            print(f"[COG][ERROR] setup() failed for {ext}:")
                            traceback.print_exc()
                except Exception:
                    print(f"[COG][FAILED] Could not import {ext}:")
                    traceback.print_exc()

            # expose mapping for runtime reload operations
            try:
                # attach to module so control_api can import it
                import types
                setattr(sys.modules.get(__name__), "loaded_extensions", loaded_extensions)
            except Exception:
                pass

            # ==================================================
            # START BOT
            # ==================================================

            try:
                await bot.start(token)
            except asyncio.CancelledError:
                print("Cancelled")
                raise
            except Exception:
                traceback.print_exc()
                await bot.close()
                raise
    finally:
        # ensure control API task is cancelled when bot exits
        if server_task is not None:
            try:
                server_task.cancel()
            except Exception:
                pass


# ==========================================================
# SCRIPT START
# ==========================================================


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
