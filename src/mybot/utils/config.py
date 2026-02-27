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

    When *guild_id* is provided the guild-specific override at
    ``config/guilds/{guild_id}/{name}.json`` is tried first; if that file is
    missing the global ``config/{name}.json`` is used as fallback so that
    guilds without their own overrides still operate normally.

    Returns an empty dict if no file is found or cannot be parsed.
    """

    repo_root = REPO_ROOT
    cache_key = f"{guild_id}:{name}" if guild_id is not None else name

    # --- guild-specific path (if requested) ---
    if guild_id is not None:
        guild_path = config_json_path(repo_root, f"{name}.json", guild_id=guild_id)
        guild_mtime = _file_mtime(guild_path)
        if guild_mtime >= 0:
            # Guild file exists — use it.
            if cache_key in _CACHE and _CACHE_MTIME.get(cache_key, -2.0) == guild_mtime:
                return copy.deepcopy(_CACHE[cache_key])
            data = load_json_dict(guild_path)
            _CACHE[cache_key] = data
            _CACHE_MTIME[cache_key] = guild_mtime
            return copy.deepcopy(data)

    # --- global path (default) ---
    cfg_path = config_json_path(repo_root, f"{name}.json")
    current_mtime = _file_mtime(cfg_path)

    if cache_key in _CACHE and _CACHE_MTIME.get(cache_key, -2.0) == current_mtime:
        return copy.deepcopy(_CACHE[cache_key])

    data = load_json_dict(cfg_path)

    _CACHE[cache_key] = data
    _CACHE_MTIME[cache_key] = current_mtime
    return copy.deepcopy(data)


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
    """Create per-cog config files in `config/` from `config.example.json` if missing.

    Returns a list of created file paths (relative to repo root).
    """

    repo_root = REPO_ROOT
    example_path = os.path.join(repo_root, "data", "config.example.json")
    config_dir = os.path.join(repo_root, "config")

    created: List[str] = []

    if not os.path.exists(example_path):
        return created

    try:
        with open(example_path, "r", encoding="utf-8") as fh:
            example = json.load(fh)
    except Exception:
        return created

    os.makedirs(config_dir, exist_ok=True)

    if isinstance(example, dict):
        for key, val in example.items():
            target = config_json_path(repo_root, f"{key}.json")
            if os.path.exists(target):
                continue
            try:
                if save_json(target, val or {}, indent=2):
                    created.append(os.path.relpath(target, repo_root))
            except Exception:
                continue

    return created


def sync_cog_configs_from_example() -> dict:
    """Ensure config files exist and backfill missing top-level keys from example.

    Returns a dict with lists: {"created": [...], "updated": [...]} where each
    item is a path relative to repository root.
    """

    repo_root = REPO_ROOT
    example_path = os.path.join(repo_root, "data", "config.example.json")
    config_dir = os.path.join(repo_root, "config")

    result = {"created": [], "updated": []}

    if not os.path.exists(example_path):
        return result

    try:
        with open(example_path, "r", encoding="utf-8") as fh:
            example = json.load(fh)
    except Exception:
        return result

    os.makedirs(config_dir, exist_ok=True)

    if not isinstance(example, dict):
        return result

    for key, val in example.items():
        target = config_json_path(repo_root, f"{key}.json")
        rel_target = os.path.relpath(target, repo_root)

        if not os.path.exists(target):
            try:
                if save_json(target, val or {}, indent=2):
                    result["created"].append(rel_target)
                    _CACHE[key] = val or {}
                    _CACHE_MTIME[key] = _file_mtime(target)
            except Exception:
                continue
            continue

        # Backfill missing top-level keys for existing files.
        existing = load_json_dict(target)

        if not isinstance(existing, dict):
            existing = {}

        changed = False
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                if sub_key not in existing:
                    existing[sub_key] = sub_val
                    changed = True

        if changed:
            try:
                if save_json(target, existing, indent=2):
                    result["updated"].append(rel_target)
                    _CACHE[key] = existing
                    _CACHE_MTIME[key] = _file_mtime(target)
            except Exception:
                pass

    return result


def write_cog_config(name: str, data: dict, guild_id: str | int | None = None) -> bool:
    """Write *data* to a cog config JSON file and update the cache.

    When *guild_id* is provided the data is written to the guild-specific
    override at ``config/guilds/{guild_id}/{name}.json``.

    Returns True on success, False on failure.
    """
    repo_root = REPO_ROOT
    cfg_path = config_json_path(repo_root, f"{name}.json", guild_id=guild_id)
    cache_key = f"{guild_id}:{name}" if guild_id is not None else name
    try:
        existing = save_json_merged(cfg_path, data or {})

        # update cache
        _CACHE[cache_key] = existing
        _CACHE_MTIME[cache_key] = _file_mtime(cfg_path)
        return True
    except Exception:
        return False
