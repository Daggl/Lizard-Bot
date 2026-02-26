import os
import sys

from repo_paths import get_repo_root

try:
    from mybot.utils.config_store import (
        config_json_path as _config_json_path,
        load_json_dict as _load_json_dict,
        save_json_merged as _save_json_merged,
    )
    from mybot.utils.env_store import (
        ensure_env_file as _ensure_env_file,
        env_file_path as _env_file_path,
        load_env_dict as _load_env_dict,
        save_env_dict as _save_env_dict,
        save_env_merged as _save_env_merged,
    )
except Exception:
    repo_root = get_repo_root()
    src_dir = os.path.join(repo_root, "src")
    if os.path.isdir(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from mybot.utils.config_store import (
        config_json_path as _config_json_path,
        load_json_dict as _load_json_dict,
        save_json_merged as _save_json_merged,
    )
    from mybot.utils.env_store import (
        ensure_env_file as _ensure_env_file,
        env_file_path as _env_file_path,
        load_env_dict as _load_env_dict,
        save_env_dict as _save_env_dict,
        save_env_merged as _save_env_merged,
    )


def config_json_path(repo_root: str, filename: str) -> str:
    return _config_json_path(repo_root, filename)


def load_json_dict(path: str) -> dict:
    return _load_json_dict(path)


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
