"""Thread-safe JSON storage utilities with atomic writes and corruption recovery."""

import json
import os
import tempfile
import time
from typing import Any


def ensure_dir(path: str) -> None:
    """Create directory (and parents) if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def safe_load_json(path: str, default: Any = None) -> Any:
    """Load JSON from *path*. If missing, create with *default*. If corrupt,
    back up the bad file and return/create *default*.
    """
    if default is None:
        default = {}

    folder = os.path.dirname(path) or "."
    ensure_dir(folder)

    if not os.path.exists(path):
        safe_save_json(path, default)
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        # Backup corrupt file before overwriting
        backup = f"{path}.bad-{int(time.time())}"
        try:
            os.replace(path, backup)
        except Exception:
            pass
        safe_save_json(path, default)
        return default


def safe_save_json(path: str, data: Any) -> None:
    """Atomically write *data* as JSON to *path* using a temp file + rename.

    This prevents partial writes if the process is interrupted.
    """
    folder = os.path.dirname(path) or "."
    ensure_dir(folder)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=folder, delete=False, suffix=".tmp"
        ) as tf:
            json.dump(data, tf, ensure_ascii=False, indent=4)
            tmp_name = tf.name
        os.replace(tmp_name, path)
    except Exception:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise
