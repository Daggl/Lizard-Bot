"""Minimal JSON-over-TCP control API for local UI.

Protocol: each request is a single JSON object followed by a newline.
Responses are single-line JSON objects.

Usage: set environment variable `LOCAL_UI_ENABLE=1` before starting the bot
and the API will listen on 127.0.0.1:8765 by default.
"""

import asyncio
import json
import os
import importlib
import sys
from typing import Dict
import inspect
from discord.ext import commands as _commands

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

# simple auth token read from env
CONTROL_API_TOKEN = os.getenv("CONTROL_API_TOKEN")


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, bot):
    peer = writer.get_extra_info("peername")
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
        if CONTROL_API_TOKEN:
            if req.get("token") != CONTROL_API_TOKEN:
                resp = {"ok": False, "error": "unauthorized"}
                writer.write((json.dumps(resp) + "\n").encode())
                await writer.drain()
                return

        action = req.get("action")
        if action == "ping":
            resp = {"ok": True, "msg": "pong"}

        elif action == "status":
            resp = {
                "ok": True,
                "ready": getattr(bot, "is_ready", lambda: False)(),
                "user": getattr(bot.user, "name", None),
                "cogs": list(getattr(bot, "cogs", {}).keys()),
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

            # Prefer to reload the explicit extensions list from the main runner
            extensions = None
            try:
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
            name = req.get("name") or "NewMember"
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

        else:
            resp = {"ok": False, "error": "unknown action"}

        # Rank card preview: generate rank image for a dummy member using Rank cog
        if action == "rank_preview":
            name = req.get("name") or "NewMember"
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
                    try:
                        # pass bg_path through to rank cog (bot and UI typically run on same host)
                        card_file = await rank_cog.generate_rankcard(dummy, bg_path=bg_path)
                    except Exception as e:
                        resp = {"ok": False, "error": f"rank generation failed: {e}"}
                    else:
                        fp = getattr(card_file, "fp", None)
                        if fp is None:
                            resp = {"ok": False, "error": "no file buffer returned"}
                        else:
                            try:
                                fp.seek(0)
                            except Exception:
                                pass
                            import base64

                            data = fp.read()
                            b64 = base64.b64encode(data).decode()
                            resp = {"ok": True, "png_base64": b64}
            except Exception as e:
                resp = {"ok": False, "error": str(e)}

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
