"""Minimal JSON-over-TCP control API for local UI.

Protocol: each request is a single JSON object followed by a newline.
Responses are single-line JSON objects.

Usage: set environment variable `LOCAL_UI_ENABLE=1` before starting the bot
and the API will listen on 127.0.0.1:8765 by default.
"""

import asyncio
import importlib
import inspect
import json
import os
import sys
import time
from types import SimpleNamespace
from typing import Dict

from discord.ext import commands as _commands

from mybot.utils.env_store import ensure_env_file
from mybot.utils.i18n import (
    available_languages as _available_languages,
    describe_language as _describe_language,
    get_all_guild_languages as _get_all_guild_languages,
    get_default_language as _get_default_language,
    set_language_for_guild as _set_language_for_guild,
)
from mybot.utils.paths import REPO_ROOT, ensure_runtime_storage

try:
    import psutil  # type: ignore
except Exception:
    psutil = None

_PROC_HANDLE = None
_CPU_PRIMED = False
if psutil is not None:
    try:
        _PROC_HANDLE = psutil.Process(os.getpid())
    except Exception:
        _PROC_HANDLE = None

# helper: clear config cache when reloading so UI edits take effect
def _clear_config_cache():
    try:
        try:
            from mybot.utils import config as _cfg
        except Exception:
            from src.mybot.utils import config as _cfg
        _cfg.clear_cog_config_cache()
    except Exception:
        pass

CONTROL_API_STARTED_AT = time.time()

ADMIN_TEST_COMMANDS = {
    "testping",
    "testrank",
    "testcount",
    "testbirthday",
    "testpoll",
    "testticketpanel",
    "testmusic",
    "testsay",
    "testlevel",
    "testlevelup",
    "testachievement",
    "testlog",
    "testwelcome",
    "testall",
}


def _repo_root() -> str:
    try:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    except Exception:
        return os.getcwd()


def _current_control_api_token() -> str:
    try:
        try:
            from mybot.utils.env_store import env_file_path, load_env_dict
        except Exception:
            from src.mybot.utils.env_store import env_file_path, load_env_dict

        path = env_file_path(_repo_root())
        data = load_env_dict(path)
        token = str(data.get("CONTROL_API_TOKEN", "") or "").strip()
        if token:
            return token
    except Exception:
        pass
    return str(os.getenv("CONTROL_API_TOKEN", "") or "").strip()


def _build_guild_snapshot(bot):
    guilds_payload = []
    try:
        guilds = list(getattr(bot, "guilds", []) or [])
    except Exception:
        guilds = []

    for guild in guilds:
        try:
            channels = []
            for channel in list(getattr(guild, "channels", []) or []):
                channels.append(
                    {
                        "id": getattr(channel, "id", None),
                        "name": getattr(channel, "name", "unknown"),
                        "type": str(getattr(channel, "type", "unknown")),
                    }
                )
            channels.sort(key=lambda ch: (str(ch.get("type") or ""), str(ch.get("name") or "")))

            roles = []
            for role in list(getattr(guild, "roles", []) or []):
                rid = getattr(role, "id", None)
                if rid == getattr(guild, "id", None):
                    continue
                roles.append(
                    {
                        "id": rid,
                        "name": getattr(role, "name", "unknown"),
                        "position": int(getattr(role, "position", 0) or 0),
                    }
                )
            roles.sort(key=lambda r: (-int(r.get("position") or 0), str(r.get("name") or "")))

            emojis = []
            for emoji in list(getattr(guild, "emojis", []) or []):
                emojis.append(
                    {
                        "id": getattr(emoji, "id", None),
                        "name": getattr(emoji, "name", "unknown"),
                        "animated": bool(getattr(emoji, "animated", False)),
                    }
                )
            emojis.sort(key=lambda e: str(e.get("name") or "").lower())

            guilds_payload.append(
                {
                    "id": getattr(guild, "id", None),
                    "name": getattr(guild, "name", "unknown"),
                    "channels": channels,
                    "roles": roles,
                    "emojis": emojis,
                }
            )
        except Exception:
            continue

    return {"ok": True, "guilds": guilds_payload}


def _pick_test_guild(bot):
    try:
        guilds = list(getattr(bot, "guilds", []) or [])
    except Exception:
        guilds = []
    return guilds[0] if guilds else None


async def _pick_test_channel(guild, requested_channel_id=None, bot=None):
    if guild is None:
        return None
    me = getattr(guild, "me", None)
    channels = list(getattr(guild, "text_channels", []) or [])
    if requested_channel_id not in (None, ""):
        try:
            chan_id = int(requested_channel_id)
        except Exception:
            return None
        # 1) Try guild.get_channel
        requested = None
        try:
            requested = guild.get_channel(chan_id)
        except Exception:
            pass
        # 2) Try bot.get_channel (handles channels in other guilds or cache)
        if requested is None and bot is not None:
            try:
                requested = bot.get_channel(chan_id)
            except Exception:
                pass
        # 3) Try bot.fetch_channel as last resort (API call)
        if requested is None and bot is not None:
            try:
                requested = await bot.fetch_channel(chan_id)
            except Exception:
                pass
        if requested is None:
            return None
        # Use the channel's own guild for permission checks
        chan_guild = getattr(requested, "guild", guild)
        chan_me = getattr(chan_guild, "me", me)
        try:
            perms = requested.permissions_for(chan_me) if chan_me is not None else None
            if perms is None or getattr(perms, "send_messages", False):
                return requested
        except Exception:
            # Permission check failed — still return the channel (best effort)
            return requested
        return None
    for channel in channels:
        try:
            perms = channel.permissions_for(me) if me is not None else None
            if perms is None or getattr(perms, "send_messages", False):
                return channel
        except Exception:
            continue
    return channels[0] if channels else None


def _pick_test_voice_channel(guild):
    if guild is None:
        return None
    me = getattr(guild, "me", None)
    channels = list(getattr(guild, "voice_channels", []) or [])
    for channel in channels:
        try:
            perms = channel.permissions_for(me) if me is not None else None
            if perms is None:
                continue
            if getattr(perms, "connect", False) and getattr(perms, "speak", False):
                return channel
        except Exception:
            continue
    return channels[0] if channels else None


def _pick_test_member(guild):
    if guild is None:
        return None
    try:
        members = list(getattr(guild, "members", []) or [])
    except Exception:
        members = []

    preferred_name = str(os.getenv("UI_TEST_MEMBER_NAME", "leutnantbrause") or "").strip().lower()
    if preferred_name:
        for member in members:
            try:
                if getattr(member, "bot", False):
                    continue
                name = str(getattr(member, "name", "") or "").strip().lower()
                display_name = str(getattr(member, "display_name", "") or "").strip().lower()
                if name == preferred_name or display_name == preferred_name:
                    return member
            except Exception:
                continue

    for member in members:
        try:
            if not getattr(member, "bot", False):
                return member
        except Exception:
            continue
    if members:
        return members[0]
    return getattr(guild, "me", None)


class _UiTestContext:
    def __init__(self, bot, guild, channel, author):
        self.bot = bot
        self.guild = guild
        self.channel = channel
        self.author = author
        self.is_ui_event_test = True
        self.sent_messages = []
        self.message = _UiTestMessage(author=author, channel=channel, guild=guild)

    @property
    def voice_client(self):
        try:
            return getattr(self.guild, "voice_client", None)
        except Exception:
            return None

    async def trigger_typing(self):
        try:
            if self.channel is not None:
                await self.channel.trigger_typing()
        except Exception:
            pass

    async def send(self, content=None, **kwargs):
        text = ""
        if content is not None:
            try:
                text = str(content)
            except Exception:
                text = ""
        self.sent_messages.append(text)
        if self.channel is None:
            raise RuntimeError("No channel available for ctx.send")
        try:
            return await self.channel.send(content=content, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"ctx.send failed: {exc}") from exc

    async def invoke(self, command, *args, **kwargs):
        if command is None:
            raise RuntimeError("Command not found")
        callback = getattr(command, "callback", None)
        if callback is None:
            raise RuntimeError("Command callback missing")
        cog = getattr(command, "cog", None)
        if cog is not None:
            return await callback(cog, self, *args, **kwargs)
        return await callback(self, *args, **kwargs)


class _UiTestMessage:
    def __init__(self, author=None, channel=None, guild=None):
        self.author = author
        self.channel = channel
        self.guild = guild
        try:
            self.id = int(time.time() * 1000)
        except Exception:
            self.id = 0

    async def delete(self):
        return None


def _test_command_kwargs(command_name: str, member):
    if command_name == "testachievement":
        return {"member": member, "name": "UI Test Achievement"}
    if command_name == "testpoll":
        return {"duration": 45, "question": "System test poll"}
    if command_name == "testsay":
        return {"text": "✅ Test message from UI Event Tester"}
    if command_name == "testlevel":
        return {"member": member, "xp": 50}
    if command_name == "testlevelup":
        return {"member": member, "bonus_xp": 0}
    if command_name == "testlog":
        return {"category": "system", "message": "Manual log test from UI Event Tester"}
    return {}


async def _run_admin_test(bot, command_name: str, requested_channel_id=None):
    admin_cog = bot.get_cog("AdminTools") or bot.cogs.get("AdminTools")
    if admin_cog is None:
        return {"ok": False, "error": "AdminTools cog not loaded"}

    command = bot.get_command(command_name)
    if command is None:
        return {"ok": False, "error": f"Command not found: {command_name}"}

    guild = _pick_test_guild(bot)
    if guild is None:
        return {"ok": False, "error": "Bot is in no guild; cannot run admin test"}

    channel = await _pick_test_channel(guild, requested_channel_id=requested_channel_id, bot=bot)
    if channel is None:
        if requested_channel_id not in (None, ""):
            return {"ok": False, "error": f"Requested channel not available: {requested_channel_id}"}
        return {"ok": False, "error": "No text channel available for admin test"}

    member = _pick_test_member(guild)
    if member is None:
        return {"ok": False, "error": "No member available for member-based admin tests"}

    bot_member = getattr(guild, "me", None)
    ctx_author = bot_member if command_name == "testrank" and bot_member is not None else member

    if command_name == "testmusic":
        voice_channel = _pick_test_voice_channel(guild)
        if voice_channel is None:
            return {"ok": False, "error": "No voice channel available for testmusic"}
        ctx_author = SimpleNamespace(
            id=getattr(member, "id", 0),
            name=getattr(member, "name", "UI Test User"),
            display_name=getattr(member, "display_name", "UI Test User"),
            mention=getattr(member, "mention", "@UI-Test"),
            voice=SimpleNamespace(channel=voice_channel),
        )

    ctx = _UiTestContext(bot, guild, channel, ctx_author)
    kwargs = _test_command_kwargs(command_name, member)

    try:
        await ctx.invoke(command, **kwargs)
    except TypeError as exc:
        return {"ok": False, "error": f"{command_name} invalid args: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"{command_name} failed: {exc}"}

    lines = [
        f"Executed: {command_name}",
        f"Guild: {getattr(guild, 'name', 'unknown')}",
        f"Channel: {getattr(channel, 'name', 'unknown')} ({getattr(channel, 'id', 'n/a')})",
    ]
    if ctx.sent_messages:
        preview = "\n".join(m for m in ctx.sent_messages[-5:] if m)
        if preview:
            lines.append("")
            lines.append("Output:")
            lines.append(preview)
    return {"ok": True, "details": "\n".join(lines)}


# The ordered list of tests to run for ``testall``.
_TESTALL_SEQUENCE = [
    "testping",
    "testrank",
    "testcount",
    "testbirthday",
    "testpoll",
    "testsay",
    "testlevel",
    "testlevelup",
    "testachievement",
    "testlog",
    "testwelcome",
    "testticketpanel",
]


async def _run_admin_test_all(bot, requested_channel_id=None):
    """Run every admin test command sequentially.

    When *requested_channel_id* is given, ``bot._ui_test_channel_override``
    is set for the duration so that cogs that normally send to a configured
    channel (level-up, achievements, …) will instead send to the
    requested channel.
    """
    if not requested_channel_id:
        return {"ok": False, "error": "testall requires a channel_id"}

    guild = _pick_test_guild(bot)
    if guild is None:
        return {"ok": False, "error": "Bot is in no guild; cannot run admin test"}

    channel = await _pick_test_channel(guild, requested_channel_id=requested_channel_id, bot=bot)
    if channel is None:
        return {"ok": False, "error": f"Requested channel not available: {requested_channel_id}"}

    # Set channel override so cogs route ALL messages here
    bot._ui_test_channel_override = channel

    results = []
    passed = 0
    failed_list = []

    try:
        for test_name in _TESTALL_SEQUENCE:
            try:
                r = await _run_admin_test(bot, test_name, requested_channel_id=requested_channel_id)
                if r.get("ok"):
                    passed += 1
                    results.append(f"✅ {test_name}")
                else:
                    failed_list.append(test_name)
                    error = r.get("error", "unknown")
                    results.append(f"❌ {test_name}: {error}")
            except Exception as exc:
                failed_list.append(test_name)
                results.append(f"❌ {test_name}: {exc}")
    finally:
        # Always clear the override
        bot._ui_test_channel_override = None

    summary = f"Test All: {passed}/{len(_TESTALL_SEQUENCE)} passed"
    if failed_list:
        summary += f" | Failed: {', '.join(failed_list)}"

    details = summary + "\n\n" + "\n".join(results)
    return {"ok": True, "details": details}


async def _handle_purge(bot, req: dict) -> dict:
    """Handle the 'purge' control-API action.

    Starts the purge as a **background task** so the API responds immediately.
    The UI can then poll ``purge_status`` for progress.

    Expected keys:
        guild_id   – target guild (str or int)
        user_id    – user whose messages to delete (str or int)
        hours      – time window in hours (int, default 24)
        channel_id – (optional) single channel; omit for all text channels
    """
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz

    guild_id = req.get("guild_id")
    user_id = req.get("user_id")
    hours = int(req.get("hours") or 24)

    if not guild_id:
        return {"ok": False, "error": "guild_id required"}
    if not user_id:
        return {"ok": False, "error": "user_id required"}

    try:
        guild_id = int(guild_id)
        user_id = int(user_id)
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": f"invalid id: {e}"}

    guild = bot.get_guild(guild_id)
    if guild is None:
        return {"ok": False, "error": f"guild {guild_id} not found"}

    hours = max(1, min(hours, 8760))
    now = _dt.now(_tz.utc)
    after = now - _td(hours=hours)

    channel_id = req.get("channel_id")

    channels: list = []
    if channel_id:
        try:
            ch = guild.get_channel(int(channel_id))
        except Exception:
            ch = None
        if ch is None:
            return {"ok": False, "error": f"channel {channel_id} not found"}
        channels = [ch]
    else:
        channels = list(guild.text_channels)

    purge_cog = bot.get_cog("Purge") or bot.cogs.get("Purge")
    if purge_cog is None:
        return {"ok": False, "error": "Purge cog not loaded — restart the bot"}

    if purge_cog._purge_running:
        return {"ok": False, "error": "A purge is already running. Wait for it to finish or check purge_status."}

    reason = f"Purge via UI (user_id={user_id})"

    # Launch as background task — respond immediately
    asyncio.create_task(
        purge_cog.run_background_purge(channels, user_id, after, now, reason=reason)
    )

    return {"ok": True, "msg": "Purge started in background. Poll 'purge_status' for progress."}


def _handle_purge_status(bot) -> dict:
    """Return current purge progress."""
    purge_cog = bot.get_cog("Purge") or bot.cogs.get("Purge")
    if purge_cog is None:
        return {"ok": False, "error": "Purge cog not loaded"}
    status = purge_cog.get_purge_status()
    return {"ok": True, **status}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, bot):
    try:
        data = await reader.readline()
        if not data:
            return
        try:
            req = json.loads(data.decode().strip())
        except Exception:
            resp = {"ok": False, "error": "invalid json"}
            writer.write((json.dumps(resp) + "\n").encode())
            await writer.drain()
            return

        # simple token auth: require matching token when CONTROL_API_TOKEN is set
        control_api_token = _current_control_api_token()
        if control_api_token:
            if req.get("token") != control_api_token:
                resp = {"ok": False, "error": "unauthorized"}
                writer.write((json.dumps(resp) + "\n").encode())
                await writer.drain()
                return

        action = req.get("action")
        if action == "ping":
            resp = {"ok": True, "msg": "pong"}

        elif action == "status":
            uptime_seconds = int(max(0, time.time() - CONTROL_API_STARTED_AT))
            gateway_ping_ms = None
            try:
                latency = getattr(bot, "latency", None)
                if isinstance(latency, (int, float)):
                    gateway_ping_ms = int(max(0, latency * 1000.0))
            except Exception:
                gateway_ping_ms = None

            cpu_percent = None
            system_cpu_percent = None
            memory_rss_mb = None
            try:
                global _CPU_PRIMED
                if _PROC_HANDLE is not None:
                    if not _CPU_PRIMED:
                        try:
                            _PROC_HANDLE.cpu_percent(interval=None)
                        except Exception:
                            pass
                        _CPU_PRIMED = True
                    cpu_percent = float(_PROC_HANDLE.cpu_percent(interval=0.05))
                    memory_rss_mb = float(_PROC_HANDLE.memory_info().rss) / (1024.0 * 1024.0)
                if psutil is not None:
                    try:
                        system_cpu_percent = float(psutil.cpu_percent(interval=None))
                    except Exception:
                        system_cpu_percent = None
            except Exception:
                cpu_percent = None
                system_cpu_percent = None
                memory_rss_mb = None

            resp = {
                "ok": True,
                "ready": getattr(bot, "is_ready", lambda: False)(),
                "user": getattr(bot.user, "name", None),
                "user_id": getattr(bot.user, "id", None),
                "avatar_url": getattr(getattr(bot.user, "display_avatar", None), "url", None),
                "cogs": list(getattr(bot, "cogs", {}).keys()),
                "uptime_seconds": uptime_seconds,
                "gateway_ping_ms": gateway_ping_ms,
                "cpu_percent": cpu_percent,
                "system_cpu_percent": system_cpu_percent,
                "memory_rss_mb": memory_rss_mb,
            }

        elif action == "shutdown":
            # polite shutdown request
            resp = {"ok": True, "msg": "shutting down"}
            writer.write((json.dumps(resp) + "\n").encode())
            await writer.drain()
            # schedule bot close on the loop
            try:
                coro = bot.close()
                asyncio.create_task(coro)
            except Exception:
                pass
            return

        elif action in ("reload", "reload_cogs"):
            # ensure any updated JSON configs are re-read by clearing cache
            _clear_config_cache()
            # Unload existing cogs first to avoid "Cog already loaded" errors
            reloaded = []
            failed = {}
            unloaded = []

            try:
                existing = list(bot.cogs.keys())
                for cog_name in existing:
                    try:
                        res = bot.remove_cog(cog_name)
                        if asyncio.iscoroutine(res):
                            await res
                        unloaded.append(cog_name)
                    except Exception as e:
                        failed[f"unload:{cog_name}"] = str(e)
            except Exception as e:
                # non-fatal, record and continue
                failed["unload_all"] = str(e)

            # Prefer to reload the explicit extensions list from the runtime runner
            extensions = None
            try:
                try:
                    import mybot.runtime.lizard as lizard
                except Exception:
                    try:
                        import src.mybot.runtime.lizard as lizard
                    except Exception:
                        try:
                            import mybot.lizard as lizard
                        except Exception:
                            import src.mybot.lizard as lizard
                extensions = getattr(lizard, "extensions", None)
                loaded_exts_map = getattr(lizard, "loaded_extensions", {})
            except Exception:
                # not fatal, fallback to scanning sys.modules
                extensions = None
                loaded_exts_map = {}

            targets = []
            if extensions and isinstance(extensions, (list, tuple)):
                targets = list(extensions)
            else:
                # fallback: reload any module under mybot.cogs
                for name in list(sys.modules.keys()):
                    if name.startswith("mybot.cogs"):
                        targets.append(name)

            for name in targets:
                try:
                    # Try to get module if already imported, else import it
                    module = sys.modules.get(name)
                    if module is None:
                        module = importlib.import_module(name)

                    # If we have a recorded list of cogs added by this extension, remove them first
                    try:
                        cogs_to_remove = loaded_exts_map.get(name) or loaded_exts_map.get(name.replace("src.", "")) or []
                        for cog_name in list(cogs_to_remove):
                            if cog_name in bot.cogs:
                                try:
                                    res = bot.remove_cog(cog_name)
                                    if asyncio.iscoroutine(res):
                                        await res
                                    unloaded.append(cog_name)
                                except Exception as e:
                                    failed[f"pre_unload:{cog_name}"] = str(e)
                    except Exception:
                        pass

                    # Reload the module (so code changes are picked up)
                    try:
                        module = importlib.reload(module)
                    except Exception as e:
                        # If reload fails, record and continue
                        failed[name] = str(e)
                        continue

                    # Call setup() if present
                    if hasattr(module, "setup"):
                        try:
                            res = module.setup(bot)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as e:
                            failed[name] = str(e)
                            continue

                    reloaded.append(name)
                except Exception as e:
                    failed[name] = str(e)

            resp = {"ok": True, "reloaded": reloaded, "failed": failed, "unloaded": unloaded}
        elif action == "banner_preview":
            # Request the welcome cog to render a banner for a dummy member and
            # return the PNG as base64 so the UI can show exactly what the bot
            # would send.
            name = req.get("name") or getattr(getattr(bot, "user", None), "name", None) or "NewMember"
            avatar_url = req.get("avatar_url")
            overrides = req.get("overrides") if isinstance(req.get("overrides"), dict) else None

            try:
                # find welcome cog
                welcome_cog = None
                try:
                    welcome_cog = bot.get_cog("Welcome")
                except Exception:
                    welcome_cog = None

                if welcome_cog is None:
                    # try to search cogs dict manually
                    welcome_cog = bot.cogs.get("Welcome")

                if welcome_cog is None:
                    resp = {"ok": False, "error": "welcome cog not loaded"}
                else:
                    # construct a minimal dummy member object with required attributes
                    class _Avatar:
                        def __init__(self, url):
                            self.url = url

                    class _DummyMember:
                        def __init__(self, name, avatar_url):
                            self.display_name = name
                            self.name = name
                            self.mention = f"@{name}"
                            self.display_avatar = _Avatar(avatar_url)

                    # default avatar: use bot user avatar if available
                    if not avatar_url:
                        try:
                            avatar_url = getattr(bot.user, "display_avatar", None)
                            if avatar_url is not None:
                                avatar_url = getattr(avatar_url, "url", None)
                        except Exception:
                            avatar_url = None

                    if not avatar_url:
                        # fallback to a simple 1x1 png served externally; create_banner will handle failures
                        avatar_url = "https://httpbin.org/image/png"

                    dummy = _DummyMember(name, avatar_url)
                    # call create_banner (coroutine) on the cog
                    try:
                        sig = inspect.signature(welcome_cog.create_banner)
                        if "overrides" in sig.parameters:
                            banner_file = await welcome_cog.create_banner(dummy, overrides=overrides)
                        else:
                            banner_file = await welcome_cog.create_banner(dummy)
                    except Exception as e:
                        resp = {"ok": False, "error": f"banner generation failed: {e}"}
                    else:
                        try:
                            # discord.File stores a .fp file-like object
                            fp = getattr(banner_file, "fp", None)
                            if fp is None:
                                resp = {"ok": False, "error": "no file buffer returned"}
                            else:
                                try:
                                    fp.seek(0)
                                except Exception:
                                    pass
                                data = fp.read()
                                import base64

                                b64 = base64.b64encode(data).decode()
                                resp = {"ok": True, "png_base64": b64}
                        except Exception as e:
                            resp = {"ok": False, "error": str(e)}
            except Exception as e:
                resp = {"ok": False, "error": str(e)}

        elif action == "event_test":
            test_name = str(req.get("test") or "").strip().lower()
            channel_id = req.get("channel_id")
            if not test_name:
                resp = {"ok": False, "error": "missing test command"}
            elif test_name not in ADMIN_TEST_COMMANDS:
                resp = {
                    "ok": False,
                    "error": f"unsupported test command: {test_name}",
                    "available": sorted(ADMIN_TEST_COMMANDS),
                }
            elif test_name == "testall":
                resp = await _run_admin_test_all(bot, requested_channel_id=channel_id)
            else:
                resp = await _run_admin_test(bot, test_name, requested_channel_id=channel_id)

        elif action == "guild_snapshot":
            resp = _build_guild_snapshot(bot)

        elif action == "languages_get":
            guild_details = []
            try:
                for guild in getattr(bot, "guilds", []) or []:
                    guild_details.append(
                        {
                            "id": str(getattr(guild, "id", "")),
                            "name": getattr(guild, "name", "unknown"),
                        }
                    )
            except Exception:
                guild_details = []
            resp = {
                "ok": True,
                "languages": [
                    {"code": code, "label": _describe_language(code)} for code in _available_languages()
                ],
                "default": _get_default_language(),
                "guilds": _get_all_guild_languages(),
                "guild_details": guild_details,
            }

        elif action == "languages_set":
            guild_id = req.get("guild_id")
            language = str(req.get("language") or "").lower()
            if guild_id in (None, ""):
                resp = {"ok": False, "error": "guild_id required"}
            elif not language:
                resp = {"ok": False, "error": "language required"}
            else:
                try:
                    _set_language_for_guild(int(guild_id), language)
                except ValueError as exc:
                    resp = {"ok": False, "error": str(exc)}
                else:
                    resp = {
                        "ok": True,
                        "guild_id": str(guild_id),
                        "language": language,
                        "guilds": _get_all_guild_languages(),
                    }

        elif action == "purge":
            resp = await _handle_purge(bot, req)

        elif action == "purge_status":
            resp = _handle_purge_status(bot)

        elif action == "sync_guild_commands":
            # Re-sync slash commands for a guild after feature toggles change
            gid = req.get("guild_id")
            if not gid:
                resp = {"ok": False, "error": "guild_id required"}
            else:
                try:
                    from mybot.runtime.lizard import sync_guild_commands
                    await sync_guild_commands(int(gid))
                    resp = {"ok": True, "guild_id": str(gid)}
                except Exception as e:
                    resp = {"ok": False, "error": f"sync failed: {e}"}

        elif action == "rank_preview":
            name = req.get("name") or getattr(getattr(bot, "user", None), "name", None) or "NewMember"
            avatar_url = req.get("avatar_url")
            try:
                rank_cog = bot.get_cog("Rank") or bot.cogs.get("Rank")
                if rank_cog is None:
                    resp = {"ok": False, "error": "rank cog not loaded"}
                else:
                    class _Avatar:
                        def __init__(self, url):
                            self.url = url

                    class _DummyMember:
                        def __init__(self, uid, name, avatar_url):
                            self.id = uid
                            self.display_name = name
                            self.name = name
                            self.mention = f"@{name}"
                            self.display_avatar = _Avatar(avatar_url)

                    if not avatar_url:
                        try:
                            avatar_url = getattr(bot.user, "display_avatar", None)
                            if avatar_url is not None:
                                avatar_url = getattr(avatar_url, "url", None)
                        except Exception:
                            avatar_url = None

                    if not avatar_url:
                        avatar_url = "https://httpbin.org/image/png"

                    dummy = _DummyMember(123456789, name, avatar_url)
                    bg_path = req.get("bg_path")
                    bg_mode = req.get("bg_mode")
                    bg_zoom = req.get("bg_zoom")
                    bg_offset_x = req.get("bg_offset_x")
                    bg_offset_y = req.get("bg_offset_y")
                    name_font = req.get("name_font")
                    info_font = req.get("info_font")
                    name_font_size = req.get("name_font_size")
                    info_font_size = req.get("info_font_size")
                    name_color = req.get("name_color")
                    info_color = req.get("info_color")
                    text_offset_x = int(req.get("text_offset_x") or 0)
                    text_offset_y = int(req.get("text_offset_y") or 0)
                    try:
                        from mybot.cogs.leveling.rank import render_rankcard

                        png_bytes = render_rankcard(
                            bg_path=bg_path or "assets/rankcard.png",
                            bg_mode=bg_mode or "cover",
                            bg_zoom=bg_zoom if bg_zoom is not None else 100,
                            bg_offset_x=bg_offset_x if bg_offset_x is not None else 0,
                            bg_offset_y=bg_offset_y if bg_offset_y is not None else 0,
                            username=name,
                            level=5,
                            xp=350,
                            xp_needed=500,
                            messages=128,
                            voice_minutes=45,
                            achievements_count=3,
                            avatar_bytes=None,
                            username_font=name_font or "assets/fonts/Poppins-Bold.ttf",
                            username_font_size=name_font_size if name_font_size is not None else 90,
                            username_color=name_color or "#FFFFFF",
                            level_font=info_font or "assets/fonts/Poppins-Regular.ttf",
                            level_font_size=info_font_size if info_font_size is not None else 60,
                            level_color=info_color or "#C8C8C8",
                            xp_font=info_font or "assets/fonts/Poppins-Regular.ttf",
                            xp_font_size=33,
                            xp_color=info_color or "#C8C8C8",
                            messages_font=info_font or "assets/fonts/Poppins-Regular.ttf",
                            messages_font_size=33,
                            messages_color=info_color or "#C8C8C8",
                            voice_font=info_font or "assets/fonts/Poppins-Regular.ttf",
                            voice_font_size=33,
                            voice_color=info_color or "#C8C8C8",
                            achievements_font=info_font or "assets/fonts/Poppins-Regular.ttf",
                            achievements_font_size=33,
                            achievements_color=info_color or "#C8C8C8",
                            username_x=400 + text_offset_x,
                            username_y=80 + text_offset_y,
                            level_x=400 + text_offset_x,
                            level_y=200 + text_offset_y,
                            xp_x=1065 + text_offset_x,
                            xp_y=270 + text_offset_y,
                            messages_x=400 + text_offset_x,
                            messages_y=400 + text_offset_y,
                            voice_x=680 + text_offset_x,
                            voice_y=400 + text_offset_y,
                            achievements_x=980 + text_offset_x,
                            achievements_y=400 + text_offset_y,
                        )
                    except Exception as e:
                        resp = {"ok": False, "error": f"rank generation failed: {e}"}
                    else:
                        import base64

                        b64 = base64.b64encode(png_bytes).decode()
                        resp = {"ok": True, "png_base64": b64}
            except Exception as e:
                resp = {"ok": False, "error": str(e)}

        else:
            resp = {"ok": False, "error": "unknown action"}

        writer.write((json.dumps(resp) + "\n").encode())
        await writer.drain()

    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def serve(bot, host: str = "127.0.0.1", port: int = 8765):
    server = await asyncio.start_server(lambda r, w: handle_client(r, w, bot), host, port)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Local UI control API listening on {addrs}")
    async with server:
        await server.serve_forever()
