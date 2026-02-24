import json
import os
from typing import Dict, List

_CACHE: Dict[str, dict] = {}


def _find_repo_root_from_package() -> str:
    """Return the repository root path when imported from src/mybot/utils."""
    # __file__ is .../src/mybot/utils/config.py; climb up 4 levels to repo root
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.abspath(here)


def load_cog_config(name: str) -> dict:
    """Load and cache `config/{name}.json` from the repository root.

    Returns an empty dict if the file is missing or cannot be parsed.
    """

    if name in _CACHE:
        return _CACHE[name]

    repo_root = _find_repo_root_from_package()
    cfg_path = os.path.join(repo_root, "config", f"{name}.json")

    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = {}

    _CACHE[name] = data
    return data


def clear_cog_config_cache(name: str = None) -> None:
    """Clear cached config for `name` or all caches if name is None.

    This is useful when config files are edited at runtime and the bot
    should pick up new values without a full restart.
    """

    global _CACHE
    if name is None:
        _CACHE.clear()
    else:
        _CACHE.pop(name, None)


def get_cached_configs() -> dict:
    """Return a shallow copy of the current config cache (for debugging)."""

    return dict(_CACHE)


def ensure_configs_from_example() -> List[str]:
    """Create per-cog config files in `config/` from `config.example.json` if missing.

    Returns a list of created file paths (relative to repo root).
    """

    repo_root = _find_repo_root_from_package()
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
            target = os.path.join(config_dir, f"{key}.json")
            if os.path.exists(target):
                continue
            try:
                with open(target, "w", encoding="utf-8") as out:
                    json.dump(val or {}, out, indent=2, ensure_ascii=False)
                created.append(os.path.relpath(target, repo_root))
            except Exception:
                continue

    return created


def write_cog_config(name: str, data: dict) -> bool:
    """Write `data` to `config/{name}.json` and update the cache.

    Returns True on success, False on failure.
    """
    repo_root = _find_repo_root_from_package()
    cfg_path = os.path.join(repo_root, "config", f"{name}.json")
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    try:
        # merge with existing if present
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                existing = json.load(fh) or {}
        except Exception:
            existing = {}

        # update existing with provided keys
        existing.update(data or {})

        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2, ensure_ascii=False)

        # update cache
        _CACHE[name] = existing
        return True
    except Exception:
        return False
