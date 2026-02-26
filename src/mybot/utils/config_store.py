import json
import os
import tempfile
from typing import Any


def config_json_path(repo_root: str, filename: str) -> str:
    cfg_dir = os.path.join(repo_root, "config")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, filename)


def load_json_dict(path: str) -> dict:
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
        return False


def save_json_merged(path: str, data: dict) -> dict:
    existing = load_json_dict(path)
    existing.update(data or {})
    save_json(path, existing, indent=2)
    return existing
