#!/usr/bin/env python3
"""
Start both the bot and the local UI with the same environment.

Usage: python start_all.py

This script loads variables from `.env` in the project root (if present),
ensures `LOCAL_UI_ENABLE=1` and starts the bot (`python -m src.mybot`) and
the UI (`python local_ui/app.py`) as subprocesses. Standard output from each
process is prefixed so you can follow both in one terminal.
"""
import os
import sys
import threading
import subprocess
import signal
import time


UI_RESTART_EXIT_CODE = 42


def load_dotenv(path):
    if not os.path.exists(path):
        return {}
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def stream_reader(prefix, stream):
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            print(f"[{prefix}] {line.rstrip()}")
    except Exception:
        pass


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(here, ".env")
    env = os.environ.copy()
    env.update(load_dotenv(dotenv_path))
    restart_marker = os.path.join(here, "data", "logs", "ui_restart.request")

    # Ensure UI control is enabled for bot (force enable)
    env["LOCAL_UI_ENABLE"] = "1"
    # Force unbuffered output so logs appear immediately
    env["PYTHONUNBUFFERED"] = "1"

    # If CONTROL_API_TOKEN not set, leave as-is (UI will also try to read it from env)
    print("Starting bot and local UI with the following env vars (hidden values not shown):")
    for key in ("LOCAL_UI_ENABLE", "CONTROL_API_TOKEN", "WEB_INTERNAL_TOKEN"):
        if key in env:
            if key.endswith("TOKEN") or key.endswith("SECRET"):
                print(f"  {key}=<REDACTED>")
            else:
                print(f"  {key}={env[key]}")

    # Use -u to force unbuffered stdout/stderr in child Python processes
    # Ensure per-cog config files exist (create from data/config.example.json when missing)
    try:
        create_configs = os.path.join(here, "scripts", "create_configs.py")
        if os.path.exists(create_configs):
            subprocess.run([sys.executable, create_configs], check=False)
    except Exception:
        pass

    bot_cmd = [sys.executable, "-u", "-m", "src.mybot"]
    ui_cmd = [sys.executable, "-u", "local_ui/app.py"]

    def _start_children():
        bot_env = env.copy()
        ui_env = env.copy()
        # Signal to UI that start_all.py supervises restart/shutdown lifecycle.
        ui_env["LOCAL_UI_SUPERVISED"] = "1"

        bot_proc_local = subprocess.Popen(bot_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=bot_env, text=True)
        ui_proc_local = subprocess.Popen(ui_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ui_env, text=True)

        threads_local = []
        t_bot = threading.Thread(target=stream_reader, args=("BOT", bot_proc_local.stdout), daemon=True)
        t_bot.start()
        threads_local.append(t_bot)
        t_ui = threading.Thread(target=stream_reader, args=("UI", ui_proc_local.stdout), daemon=True)
        t_ui.start()
        threads_local.append(t_ui)
        return bot_proc_local, ui_proc_local, threads_local

    bot_proc, ui_proc, threads = _start_children()

    def handle_sigint(signum, frame):
        print("Shutting down processes...")
        try:
            bot_proc.terminate()
        except Exception:
            pass
        try:
            ui_proc.terminate()
        except Exception:
            pass

    signal.signal(signal.SIGINT, handle_sigint)

    # supervise lifecycle; UI can request full restart by exiting with UI_RESTART_EXIT_CODE
    while True:
        try:
            ui_code = ui_proc.wait()
        except KeyboardInterrupt:
            handle_sigint(None, None)
            break

        restart_requested = (ui_code == UI_RESTART_EXIT_CODE)
        if not restart_requested:
            try:
                restart_requested = os.path.exists(restart_marker)
            except Exception:
                restart_requested = False

        if restart_requested:
            print("UI requested full restart (bot + UI) in current terminal...")
            try:
                if os.path.exists(restart_marker):
                    os.remove(restart_marker)
            except Exception:
                pass
            try:
                if bot_proc.poll() is None:
                    bot_proc.terminate()
                    try:
                        bot_proc.wait(timeout=6)
                    except Exception:
                        bot_proc.kill()
            except Exception:
                pass

            # short cooldown to free ports cleanly
            time.sleep(0.6)
            bot_proc, ui_proc, threads = _start_children()
            continue

        # normal exit path: stop bot too and finish
        try:
            if bot_proc.poll() is None:
                bot_proc.terminate()
                try:
                    bot_proc.wait(timeout=6)
                except Exception:
                    bot_proc.kill()
        except Exception:
            pass
        break


if __name__ == "__main__":
    main()
