import json
import os
import time
from typing import Any


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def safe_load_json(path: str, default: Any = None) -> Any:
    """Load JSON from `path`. If missing, create with `default`. If corrupt, back up
    the bad file and return/create `default`.
    """
    if default is None:
        default = {}

    folder = os.path.dirname(path) or '.'
    ensure_dir(folder)

    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        # backup corrupt file
        backup = f"{path}.bad-{int(time.time())}"
        try:
            os.replace(path, backup)
        except Exception:
            pass
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default


def safe_save_json(path: str, data: Any) -> None:
    folder = os.path.dirname(path) or '.'
    ensure_dir(folder)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
