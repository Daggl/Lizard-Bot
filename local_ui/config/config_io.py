import os
import sys

from core.repo_paths import get_repo_root

try:
    from mybot.utils.config_store import config_json_path as _config_json_path
    from mybot.utils.config_store import global_config_path as _global_config_path
    from mybot.utils.config_store import load_json_dict as _load_json_dict
    from mybot.utils.config_store import save_json as _save_json
    from mybot.utils.config_store import save_json_deep_merged as _save_json_deep_merged
    from mybot.utils.config_store import save_json_merged as _save_json_merged
    from mybot.utils.env_store import ensure_env_file as _ensure_env_file
    from mybot.utils.env_store import env_file_path as _env_file_path
    from mybot.utils.env_store import load_env_dict as _load_env_dict
    from mybot.utils.env_store import save_env_dict as _save_env_dict
    from mybot.utils.env_store import save_env_merged as _save_env_merged
except Exception:
    repo_root = get_repo_root()
    src_dir = os.path.join(repo_root, "src")
    if os.path.isdir(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from mybot.utils.config_store import config_json_path as _config_json_path
    from mybot.utils.config_store import global_config_path as _global_config_path
    from mybot.utils.config_store import load_json_dict as _load_json_dict
    from mybot.utils.config_store import save_json as _save_json
    from mybot.utils.config_store import save_json_deep_merged as _save_json_deep_merged
    from mybot.utils.config_store import save_json_merged as _save_json_merged
    from mybot.utils.env_store import ensure_env_file as _ensure_env_file
    from mybot.utils.env_store import env_file_path as _env_file_path
    from mybot.utils.env_store import load_env_dict as _load_env_dict
    from mybot.utils.env_store import save_env_dict as _save_env_dict
    from mybot.utils.env_store import save_env_merged as _save_env_merged


def config_json_path(repo_root: str, filename: str, guild_id: str | int | None = None) -> str:
    return _config_json_path(repo_root, filename, guild_id=guild_id)


def global_config_path(repo_root: str, filename: str) -> str:
    return _global_config_path(repo_root, filename)


def load_json_dict(path: str) -> dict:
    return _load_json_dict(path)


def load_guild_config(repo_root: str, filename: str, guild_id: str | int | None = None) -> dict:
    """Load a config **only** for a specific guild.

    When *guild_id* is given, loads the guild-specific file at
    ``config/guilds/{guild_id}/{filename}``.  If that file does not exist the
    caller receives an empty dict so the UI shows clean/empty fields.

    When *guild_id* is ``None`` (no guild selected yet) an empty dict is
    returned — there are no global settings.
    """
    if guild_id:
        guild_path = _config_json_path(repo_root, filename, guild_id=guild_id)
        return _load_json_dict(guild_path)          # {} when file missing
    return {}


def save_json(path: str, data) -> bool:
    """Atomically write *data* as JSON (full replacement, no merge)."""
    return _save_json(path, data)


def save_json_merged(path: str, data: dict) -> dict:
    return _save_json_merged(path, data)


def save_json_deep_merged(path: str, data: dict) -> dict:
    """Deep-merge *data* into an existing file (preserves nested keys)."""
    return _save_json_deep_merged(path, data)


def env_file_path(repo_root: str) -> str:
    return _env_file_path(repo_root)


def ensure_env_file(repo_root: str) -> tuple[str, bool]:
    return _ensure_env_file(repo_root)


def load_env_dict(path: str) -> dict:
    return _load_env_dict(path)


def save_env_merged(repo_root: str, data: dict) -> dict:
    return _save_env_merged(repo_root, data)


def save_env_dict(repo_root: str, data: dict) -> dict:
    return _save_env_dict(repo_root, data)
