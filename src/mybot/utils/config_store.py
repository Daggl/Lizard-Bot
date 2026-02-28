"""JSON configuration file I/O with atomic writes and merge support."""

import json
import os
import tempfile
from typing import Any


def config_json_path(repo_root: str, filename: str, guild_id: str | int | None = None) -> str:
    """Return the full path to a config JSON file, creating the directory if needed.

    When *guild_id* is provided the path points to a guild-specific override
    file: ``config/guilds/{guild_id}/{filename}``.  When *guild_id* is None,
    returns empty string - global configs are not supported.
    """
    if guild_id is None:
        return ""
    cfg_dir = os.path.join(repo_root, "config", "guilds", str(guild_id))
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, filename)


def global_config_path(repo_root: str, filename: str) -> str:
    """Return the full path to a global config file (e.g., local_ui.json).

    Use sparingly - most configs should be per-guild.
    """
    cfg_dir = os.path.join(repo_root, "config")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, filename)


def load_json_dict(path: str) -> dict:
    """Load a JSON file and return its contents as a dict.

    Returns an empty dict on missing file, empty path, parse error, or non-dict content.
    """
    if not path:
        return {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh) or {}
                if isinstance(data, dict):
                    return data
        return {}
    except Exception:
        return {}


def save_json(path: str, data: Any, indent: int = 2) -> bool:
    """Atomically write *data* as JSON to *path* using a temp file + rename.

    Returns ``True`` on success, ``False`` on error (including empty path).
    The temp file is cleaned up on failure so it is never leaked.
    """
    if not path:
        return False
    tmp_name = None
    try:
        folder = os.path.dirname(path) or "."
        os.makedirs(folder, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=folder,
            delete=False,
            suffix=".tmp",
        ) as tf:
            json.dump(data, tf, indent=indent, ensure_ascii=False)
            tmp_name = tf.name
        os.replace(tmp_name, path)
        return True
    except Exception:
        # Clean up temp file on failure
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        return False


def save_json_merged(path: str, data: dict) -> dict:
    """Merge *data* into an existing JSON file and save atomically.

    Returns the merged dictionary.
    """
    existing = load_json_dict(path)
    existing.update(data or {})
    save_json(path, existing, indent=2)
    return existing
