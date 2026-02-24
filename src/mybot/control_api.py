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
                            # Debug: show current cogs before setup
                            try:
                                print(f"[CONTROL_API] before setup for {name}, current cogs: {list(bot.cogs.keys())}")
                            except Exception:
                                pass

                            res = module.setup(bot)
                            if asyncio.iscoroutine(res):
                                await res
                            # Debug: show current cogs after setup
                            try:
                                print(f"[CONTROL_API] after setup for {name}, current cogs: {list(bot.cogs.keys())}")
                            except Exception:
                                pass
                        except Exception as e:
                            # capture full traceback for easier debugging
                            import traceback
                            tb = traceback.format_exc()
                            failed[name] = str(e)
                            print(f"[CONTROL_API][ERROR] setup() for {name} raised: {tb}")
                            continue

                    reloaded.append(name)
                except Exception as e:
                    failed[name] = str(e)

            resp = {"ok": True, "reloaded": reloaded, "failed": failed, "unloaded": unloaded}

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
