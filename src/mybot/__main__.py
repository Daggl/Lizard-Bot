"""Module entrypoint for running the bot as a module.

Usage:
    python -m src.mybot

This simply delegates to the existing `bot.py` runner so behaviour
remains unchanged while allowing a package-style invocation.
"""

import asyncio
import importlib
import os
import sys

# Ensure repository root is on sys.path so top-level modules (bot.py) are importable
# __file__ is .../src/mybot/__main__.py; climb up three levels to reach the repo root
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Resolve the callable `main` from either the package runner or a top-level
# `bot.py`. Prefer the package module when available (running as
# `python -m src.mybot`), but fall back to importing `bot.main` for
# back-compat when a top-level runner is present.
main = None

# Preferred: package runner
try:
    from src.mybot.lizard import main as pkg_main

    main = pkg_main
except Exception:
    # ignore and try top-level
    pass

if main is None:
    try:
        # Import top-level runner dynamically to avoid static import errors
        # in editor/linters when `bot.py` is not present.
        mod = importlib.import_module("bot")
        top_main = getattr(mod, "main", None)
        if callable(top_main):
            main = top_main
    except Exception:
        pass

if main is None:
    raise ImportError(
        "Could not locate a callable named 'main' "
        "in src.mybot.lizard or top-level 'bot' module"
    )

if __name__ == "__main__":
    asyncio.run(main())
