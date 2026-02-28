import copy
import json
import os
from typing import Dict, List

from .config_store import (config_json_path, load_json_dict, save_json,
                           save_json_merged)
from .paths import REPO_ROOT

_CACHE: Dict[str, dict] = {}
_CACHE_MTIME: Dict[str, float] = {}


def _file_mtime(path: str) -> float:
    try:
        return float(os.stat(path).st_mtime_ns)
    except Exception:
        return -1.0


def load_cog_config(name: str, guild_id: str | int | None = None) -> dict:
    """Load and cache a cog config JSON file.

    When *guild_id* is provided, loads the guild-specific config at
    ``config/guilds/{guild_id}/{name}.json``.  If that file is missing,
    returns an empty dict.

    When *guild_id* is None, returns an empty dict (no global fallback).

    Returns an empty dict if no file is found or cannot be parsed.
    """

    repo_root = REPO_ROOT

    # No guild = no config (pure per-guild system)
    if guild_id is None:
        return {}

    cache_key = f"{guild_id}:{name}"

    guild_path = config_json_path(repo_root, f"{name}.json", guild_id=guild_id)
    if not guild_path:
        return {}

    guild_mtime = _file_mtime(guild_path)
    if guild_mtime >= 0:
        # Guild file exists — use it.
        if cache_key in _CACHE and _CACHE_MTIME.get(cache_key, -2.0) == guild_mtime:
            return copy.deepcopy(_CACHE[cache_key])
        data = load_json_dict(guild_path)
        _CACHE[cache_key] = data
        _CACHE_MTIME[cache_key] = guild_mtime
        return copy.deepcopy(data)

    # File doesn't exist - return empty dict
    return {}


def clear_cog_config_cache(name: str = None) -> None:
    """Clear cached config for `name` or all caches if name is None.

    This is useful when config files are edited at runtime and the bot
    should pick up new values without a full restart.
    """

    global _CACHE, _CACHE_MTIME
    if name is None:
        _CACHE.clear()
        _CACHE_MTIME.clear()
    else:
        _CACHE.pop(name, None)
        _CACHE_MTIME.pop(name, None)


def get_cached_configs() -> dict:
    """Return a shallow copy of the current config cache (for debugging)."""

    return dict(_CACHE)


def ensure_configs_from_example() -> List[str]:
    """DEPRECATED: Global configs are no longer used.

    Configs are now per-guild and created by the UI when a guild is selected.
    Returns an empty list for backward compatibility.
    """
    return []


def sync_cog_configs_from_example() -> dict:
    """DEPRECATED: Global configs are no longer used.

    Configs are now per-guild and created by the UI when a guild is selected.
    Returns empty result for backward compatibility.
    """
    return {"created": [], "updated": []}


def write_cog_config(name: str, data: dict, guild_id: str | int | None = None) -> bool:
    """Write *data* to a cog config JSON file and update the cache.

    When *guild_id* is provided the data is written to the guild-specific
    override at ``config/guilds/{guild_id}/{name}.json``.

    When *guild_id* is None, returns False (no global config writes).

    Returns True on success, False on failure.
    """
    if guild_id is None:
        return False

    repo_root = REPO_ROOT
    cfg_path = config_json_path(repo_root, f"{name}.json", guild_id=guild_id)
    if not cfg_path:
        return False

    cache_key = f"{guild_id}:{name}"
    try:
        existing = save_json_merged(cfg_path, data or {})

        # update cache
        _CACHE[cache_key] = existing
        _CACHE_MTIME[cache_key] = _file_mtime(cfg_path)
        return True
    except Exception:
        return False
