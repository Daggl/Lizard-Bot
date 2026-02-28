import os
import sys

from core.repo_paths import get_repo_root

try:
    from mybot.utils.config_store import config_json_path as _config_json_path
    from mybot.utils.config_store import load_json_dict as _load_json_dict
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
    from mybot.utils.config_store import load_json_dict as _load_json_dict
    from mybot.utils.config_store import save_json_merged as _save_json_merged
    from mybot.utils.env_store import ensure_env_file as _ensure_env_file
    from mybot.utils.env_store import env_file_path as _env_file_path
    from mybot.utils.env_store import load_env_dict as _load_env_dict
    from mybot.utils.env_store import save_env_dict as _save_env_dict
    from mybot.utils.env_store import save_env_merged as _save_env_merged


def config_json_path(repo_root: str, filename: str, guild_id: str | int | None = None) -> str:
    return _config_json_path(repo_root, filename, guild_id=guild_id)


def load_json_dict(path: str) -> dict:
    return _load_json_dict(path)


def load_guild_config(repo_root: str, filename: str, guild_id: str | int | None = None) -> dict:
    """Load a guild-specific config with fallback to the global config.

    Tries ``config/guilds/{guild_id}/{filename}`` first.  If that file does not
    exist or is empty, falls back to ``config/{filename}``.  This ensures the
    UI always shows meaningful values even when no per-guild override exists.
    """
    if guild_id:
        guild_path = _config_json_path(repo_root, filename, guild_id=guild_id)
        if os.path.isfile(guild_path):
            data = _load_json_dict(guild_path)
            if data:
                return data
    # fallback to global
    global_path = _config_json_path(repo_root, filename)
    return _load_json_dict(global_path)


def save_json_merged(path: str, data: dict) -> dict:
    return _save_json_merged(path, data)


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
