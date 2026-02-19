import os
import json


def _repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _ensure_config_dir():
    root = _repo_root()
    cfg_dir = os.path.join(root, "config")
    os.makedirs(cfg_dir, exist_ok=True)
    return cfg_dir


def ensure_configs_from_example():
    """Create per-cog config files from config.example.json if missing.

    Returns list of created filenames (basename), or empty list.
    """
    root = _repo_root()
    example_path = os.path.join(root, "config.example.json")
    cfg_dir = _ensure_config_dir()

    if not os.path.exists(example_path):
        return []

    try:
        with open(example_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    created = []

    if isinstance(data, dict):
        for key, value in data.items():
            target = os.path.join(cfg_dir, f"{key}.json")
            if not os.path.exists(target):
                try:
                    with open(target, "w", encoding="utf-8") as out:
                        json.dump(value or {}, out, indent=4)
                    created.append(os.path.basename(target))
                except Exception:
                    continue

    return created


def load_cog_config(name: str) -> dict:
    """Load `config/<name>.json` as a dict. Returns {} if missing or invalid."""
    cfg_dir = _ensure_config_dir()
    path = os.path.join(cfg_dir, f"{name}.json")

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
"""Simple config loader for per-cog JSON files (packaged).

This is a copy of the top-level `utils/config.py` adjusted to work when
imported as `mybot.utils.config` from the `src/mybot` package.
"""
import json
import os
from typing import Dict

_CACHE: Dict[str, dict] = {}


def _find_repo_root_from_package() -> str:
    # package is located in src/mybot/utils; climb up to repo root
    here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.abspath(here)


def load_cog_config(name: str) -> dict:
    """Load and cache a config file from `config/{name}.json`.

    Returns an empty dict if the file doesn't exist or cannot be parsed.
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


def ensure_configs_from_example() -> list:
    """Create per-cog files in `config/` from `config.example.json` if missing.

    Returns a list of created file paths (relative to repo root).
    """

    repo_root = _find_repo_root_from_package()
    example_path = os.path.join(repo_root, "config.example.json")
    config_dir = os.path.join(repo_root, "config")

    created = []

    if not os.path.exists(example_path):
        return created

    try:
        with open(example_path, "r", encoding="utf-8") as fh:
            example = json.load(fh)
    except Exception:
        return created

    os.makedirs(config_dir, exist_ok=True)

    # example may contain a mapping of per-cog objects
    for key, val in example.items():
        target = os.path.join(config_dir, f"{key}.json")
        if os.path.exists(target):
            continue
        try:
            with open(target, "w", encoding="utf-8") as out:
                json.dump(val, out, indent=2, ensure_ascii=False)
            created.append(os.path.relpath(target, repo_root))
        except Exception:
            continue

    return created
