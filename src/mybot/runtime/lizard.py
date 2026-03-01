# ==========================================================
# IMPORTS
# ==========================================================

import asyncio
import importlib
import logging
import os
import sys
import traceback
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Route discord.py library logs to stdout so interaction errors are visible
logging.basicConfig(
    level=logging.WARNING,
    format="[%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logging.getLogger("discord").setLevel(logging.WARNING)

from mybot.utils.env_store import ensure_env_file
from mybot.utils.feature_flags import (
    feature_key_for_cog,
    is_feature_enabled,
    get_all_feature_flags,
    COG_FEATURE_MAP,
)
from mybot.utils.paths import REPO_ROOT, ensure_guild_configs, ensure_runtime_storage

# ensure project root's `src` is importable (when running as module)
_src = os.path.join(REPO_ROOT, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

os.environ.setdefault("DC_BOT_REPO_ROOT", REPO_ROOT)

# custom database for logs
from data.logs.storage import database  # noqa: E402
# ensure per-cog config files exist before loading cogs
from mybot.utils import sync_cog_configs_from_example  # noqa: E402

DEFAULT_EXTENSIONS = [
    "mybot.cogs.community.birthdays",
    "mybot.cogs.welcome.welcome",
    "mybot.cogs.community.poll",
    "mybot.cogs.leveling.levels",
    "mybot.cogs.leveling.rank",
    "mybot.cogs.leveling.achievements",
    "mybot.cogs.leveling.rewards",
    "mybot.cogs.leveling.tracking",
    "mybot.cogs.general.help_tutorial",
    "mybot.cogs.admin.admin_panel",
    "mybot.cogs.admin.admin_tools",
    "mybot.cogs.admin.admin_tutorial",
    "mybot.cogs.admin.purge",
    "mybot.cogs.community.count",
    "mybot.cogs.log.chat_log",
    "mybot.cogs.log.mod_log",
    "mybot.cogs.log.member_log",
    "mybot.cogs.log.voice_log",
    "mybot.cogs.log.server_log",
    "mybot.cogs.welcome.autorole",
    "mybot.cogs.voice.tempvoice",
    "mybot.cogs.community.say",
    "mybot.cogs.tickets.ticket",
    "mybot.cogs.media.music",
    "mybot.cogs.community.meme",
    "mybot.cogs.community.membercount",
    "mybot.cogs.community.freestuff",
    "mybot.cogs.community.socials",
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
_slash_synced = False


# ==========================================================
# GLOBAL FEATURE-FLAG CHECKS
# ==========================================================


def _check_feature_for_command(ctx: commands.Context) -> bool:
    """Global prefix-command check: block if the feature is disabled for the guild."""
    cog = ctx.command.cog
    if cog is None:
        return True  # built-in commands always pass
    cog_name = cog.qualified_name
    fkey = feature_key_for_cog(cog_name)
    if fkey is None:
        return True  # cog not mapped → always allowed
    guild_id = getattr(getattr(ctx, "guild", None), "id", None)
    return is_feature_enabled(guild_id, fkey)


bot.add_check(_check_feature_for_command)


_original_tree_interaction_check = getattr(bot.tree, "interaction_check", None)


async def _tree_feature_check(interaction: discord.Interaction) -> bool:
    """Global app-command check: block if the feature is disabled for the guild."""
    try:
        cmd = interaction.command
        cog = None
        if cmd is not None:
            # For group commands, walk up to find the cog
            binding = getattr(cmd, "binding", None)
            if binding is not None and isinstance(binding, commands.Cog):
                cog = binding
            elif hasattr(cmd, "parent") and cmd.parent is not None:
                binding = getattr(cmd.parent, "binding", None)
                if binding is not None and isinstance(binding, commands.Cog):
                    cog = binding
            # Try module-based lookup as fallback
            if cog is None:
                module = getattr(cmd, "module", None) or ""
                for registered_cog in bot.cogs.values():
                    if getattr(type(registered_cog), "__module__", "") == module:
                        cog = registered_cog
                        break
        if cog is None:
            return True
        cog_name = cog.qualified_name
        fkey = feature_key_for_cog(cog_name)
        if fkey is None:
            return True
        guild_id = getattr(getattr(interaction, "guild", None), "id", None)
        if not is_feature_enabled(guild_id, fkey):
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ This feature is currently disabled on this server.",
                        ephemeral=True,
                    )
            except Exception:
                pass
            return False
        return True
    except Exception as exc:
        print(f"[INTERACTION CHECK ERROR] {exc}")
        traceback.print_exc()
        return True  # allow command through on check error


bot.tree.interaction_check = _tree_feature_check


# ==========================================================
# PER-GUILD COMMAND SYNC (feature-flag aware)
# ==========================================================


async def sync_guild_commands(guild_id: int):
    """Sync slash commands for a single guild, hiding disabled features.

    1. Copies all globally-registered commands into the guild-specific tree.
    2. Removes commands whose cog maps to a disabled feature for this guild.
    3. Syncs the guild-specific tree to Discord.
    """
    guild_obj = discord.Object(id=guild_id)

    # Copy the global command set into this guild's tree
    bot.tree.copy_global_to(guild=guild_obj)

    flags = get_all_feature_flags(guild_id)
    disabled_features = {fkey for fkey, enabled in flags.items() if not enabled}

    if disabled_features:
        # Determine which cog names are disabled
        disabled_cog_names = set()
        for cog_name, fkey in COG_FEATURE_MAP.items():
            if fkey in disabled_features:
                disabled_cog_names.add(cog_name)

        # Remove commands belonging to disabled cogs
        guild_commands = bot.tree.get_commands(guild=guild_obj)
        for cmd in list(guild_commands):
            binding = getattr(cmd, "binding", None)
            if binding is not None and isinstance(binding, commands.Cog):
                if binding.qualified_name in disabled_cog_names:
                    bot.tree.remove_command(cmd.name, guild=guild_obj)

    await bot.tree.sync(guild=guild_obj)


# ==========================================================
# READY EVENT
# ==========================================================


@bot.event
async def on_ready():
    global _slash_synced

    # initialize database
    database.setup()

    # ensure all per-guild config/data JSON files exist
    for guild in bot.guilds:
        try:
            ensure_guild_configs(guild.id)
        except Exception as e:
            print(f"[WARN] Could not ensure configs for guild {guild.id}: {e}")

    # show that bot is online
    print(f"{bot.user.name} is online!")

    if not _slash_synced:
        try:
            # Per-guild sync FIRST — copy global commands into each guild
            # tree while the global set is still populated, then filter by
            # feature flags and sync each guild.
            for guild in getattr(bot, "guilds", []):
                try:
                    await sync_guild_commands(guild.id)
                except Exception as guild_sync_error:
                    print(f"Failed guild slash sync for guild ID {guild.id}: {guild_sync_error}")

            # Now clear stale global commands (we use per-guild sync)
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()

            guild_count = len(getattr(bot, "guilds", []))
            print(f"Synced slash commands for {guild_count} guild(s) (feature-aware).")
            _slash_synced = True
        except Exception as e:
            print("Failed to sync slash commands:", e)


# ==========================================================
# TEST COMMAND
# ==========================================================


@bot.hybrid_command(description="Ping command.")
async def ping(ctx):

    # simple test command to check if bot responds
    await ctx.send("🏓 Pong! all is good in the hood!")


@bot.event
async def on_guild_join(guild):
    """Ensure all config/data files exist when the bot joins a new guild."""
    try:
        ensure_guild_configs(guild.id)
        print(f"[GUILD JOIN] Created configs for guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"[WARN] Could not ensure configs for new guild {guild.id}: {e}")

    # Sync slash commands for the new guild (feature-aware)
    try:
        await sync_guild_commands(guild.id)
        print(f"[GUILD JOIN] Synced commands for guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"[WARN] Could not sync commands for new guild {guild.id}: {e}")


@bot.event
async def on_command_error(ctx, error):
    print(f"[CMD ERROR] Error running command {getattr(ctx, 'command', None)}: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    cmd_name = getattr(getattr(interaction, "command", None), "qualified_name", "unknown")
    print(f"[APP CMD ERROR] Error running slash command {cmd_name}: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)
    try:
        if interaction.response.is_done():
            await interaction.followup.send("❌ Command failed. Check logs for details.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Command failed. Check logs for details.", ephemeral=True)
    except Exception:
        pass


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
    # Prefer runtime package path, then keep legacy wrapper paths for compatibility.
    for module_name in (
        "mybot.runtime.control_api",
        "src.mybot.runtime.control_api",
        "mybot.control_api",
        "src.mybot.control_api",
    ):
        try:
            return importlib.import_module(module_name)
        except Exception:
            continue

    print("Failed to import local UI control API (runtime and legacy paths)")
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
