import json
import os


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


def save_json_merged(path: str, data: dict) -> dict:
    existing = load_json_dict(path)
    existing.update(data or {})
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return existing
