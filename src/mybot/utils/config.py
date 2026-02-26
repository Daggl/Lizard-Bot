import json
import os
from typing import Dict, List

from mybot.utils.config_store import config_json_path, load_json_dict, save_json, save_json_merged
from mybot.utils.paths import REPO_ROOT

_CACHE: Dict[str, dict] = {}
_CACHE_MTIME: Dict[str, float] = {}


def _file_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except Exception:
        return -1.0


def load_cog_config(name: str) -> dict:
    """Load and cache `config/{name}.json` from the repository root.

    Returns an empty dict if the file is missing or cannot be parsed.
    """

    repo_root = REPO_ROOT
    cfg_path = config_json_path(repo_root, f"{name}.json")
    current_mtime = _file_mtime(cfg_path)

    if name in _CACHE and _CACHE_MTIME.get(name, -2.0) == current_mtime:
        return _CACHE[name]

    data = load_json_dict(cfg_path)

    _CACHE[name] = data
    _CACHE_MTIME[name] = current_mtime
    return data


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


def write_cog_config(name: str, data: dict) -> bool:
    """Write `data` to `config/{name}.json` and update the cache.

    Returns True on success, False on failure.
    """
    repo_root = REPO_ROOT
    cfg_path = config_json_path(repo_root, f"{name}.json")
    try:
        existing = save_json_merged(cfg_path, data or {})

        # update cache
        _CACHE[name] = existing
        _CACHE_MTIME[name] = _file_mtime(cfg_path)
        return True
    except Exception:
        return False
