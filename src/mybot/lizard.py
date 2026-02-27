# ==========================================================
# IMPORTS
# ==========================================================

import asyncio
import importlib
import os
import sys
import traceback
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from mybot.utils.paths import REPO_ROOT, ensure_runtime_storage
from mybot.utils.env_store import ensure_env_file

# ensure project root's `src` is importable (when running as module)
_src = os.path.join(REPO_ROOT, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

os.environ.setdefault("DC_BOT_REPO_ROOT", REPO_ROOT)

# custom database for logs
from data.logs import database  # noqa: E402
# ensure per-cog config files exist before loading cogs
from mybot.utils import sync_cog_configs_from_example  # noqa: E402


DEFAULT_EXTENSIONS = [
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
    "mybot.cogs.tempvoice",
    "mybot.cogs.say",
    "mybot.cogs.tickets.ticket",
    "mybot.cogs.music",
]

# ==========================================================
# LOAD ENVIRONMENT / TOKEN
# ==========================================================

try:
    ensure_env_file(REPO_ROOT)
except Exception:
    pass

try:
    ensure_runtime_storage()
except Exception:
    pass

# loads variables from .env file
load_dotenv()

# Discord bot token from .env
token = os.getenv("DISCORD_TOKEN")


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


def _import_control_api_module():
    try:
        from mybot import control_api as control_api_module
        return control_api_module
    except Exception:
        try:
            from src.mybot import control_api as control_api_module
            return control_api_module
        except Exception as e:
            print("Failed to import local UI control API:", e)
            return None


def _start_control_api_task(bot_instance: commands.Bot) -> Optional[asyncio.Task]:
    control_api_module = _import_control_api_module()
    if control_api_module is None:
        return None

    try:
        return asyncio.create_task(control_api_module.serve(bot_instance))
    except Exception as e:
        print("Failed to start local UI control API:", e)
        return None


def _sync_configs_from_example() -> None:
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


async def _load_extensions(bot_instance: commands.Bot, extensions: list[str]) -> dict:
    loaded_extensions = {}
    for ext in extensions:
        try:
            before = set(bot_instance.cogs.keys())
            module = importlib.import_module(ext)
            if hasattr(module, "setup"):
                try:
                    result = module.setup(bot_instance)
                    if asyncio.iscoroutine(result):
                        await result
                    after = set(bot_instance.cogs.keys())
                    added = sorted(list(after - before))
                    if added:
                        loaded_extensions[ext] = added
                except Exception:
                    print(f"[COG][ERROR] setup() failed for {ext}:")
                    traceback.print_exc()
        except Exception:
            print(f"[COG][FAILED] Could not import {ext}:")
            traceback.print_exc()
    return loaded_extensions


def _expose_loaded_extensions(mapping: dict) -> None:
    try:
        setattr(sys.modules.get(__name__), "loaded_extensions", mapping)
    except Exception:
        pass


async def _run_bot(bot_instance: commands.Bot, bot_token: str) -> None:
    _sync_configs_from_example()
    loaded_extensions = await _load_extensions(bot_instance, DEFAULT_EXTENSIONS)
    _expose_loaded_extensions(loaded_extensions)

    try:
        await bot_instance.start(bot_token)
    except asyncio.CancelledError:
        print("Cancelled")
        raise
    except Exception:
        traceback.print_exc()
        await bot_instance.close()
        raise


async def main():
    # check if token exists
    if not token:
        print("DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=...")
        return

    server_task = _start_control_api_task(bot)

    try:
        async with bot:
            await _run_bot(bot, token)
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
