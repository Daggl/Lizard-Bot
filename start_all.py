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
    bot_cmd = [sys.executable, "-u", "-m", "src.mybot"]
    ui_cmd = [sys.executable, "-u", "local_ui/app.py"]

    bot_proc = subprocess.Popen(bot_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
    ui_proc = subprocess.Popen(ui_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)

    threads = []
    t = threading.Thread(target=stream_reader, args=("BOT", bot_proc.stdout), daemon=True)
    t.start()
    threads.append(t)
    t2 = threading.Thread(target=stream_reader, args=("UI", ui_proc.stdout), daemon=True)
    t2.start()
    threads.append(t2)

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

    # wait for both to exit
    try:
        bot_proc.wait()
    except KeyboardInterrupt:
        handle_sigint(None, None)

    try:
        ui_proc.wait()
    except KeyboardInterrupt:
        handle_sigint(None, None)


if __name__ == "__main__":
    main()
