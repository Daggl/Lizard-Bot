"""Module entrypoint for running the bot as a module.

Usage:
    python -m src.mybot

This simply delegates to the existing `bot.py` runner so behaviour
remains unchanged while allowing a package-style invocation.
"""

import asyncio
import os
import sys

# Ensure project root is on sys.path so top-level modules (bot.py) are importable
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from bot import main
except Exception:
    # Fallback: try importing main from src.mybot package modules if available
    try:
        # import the callable `main` from the package module
        from src.mybot.lizard import main as pkg_main

        main = pkg_main
    except Exception:
        raise

if __name__ == "__main__":
    asyncio.run(main())
