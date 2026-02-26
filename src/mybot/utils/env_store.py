import os
import tempfile


DEFAULT_ENV_VALUES = {
    "DISCORD_TOKEN": "",
    "CONTROL_API_TOKEN": "",
    "WEB_INTERNAL_TOKEN": "",
    "SPOTIFY_CLIENT_ID": "",
    "SPOTIFY_CLIENT_SECRET": "",
    "DISCORD_CLIENT_ID": "",
    "DISCORD_CLIENT_SECRET": "",
    "OAUTH_REDIRECT_URI": "",
    "APP_ORIGIN": "",
    "APP_ENV": "",
}

_ENV_HEADER = [
    "# Auto-generated on first run.",
    "# Fill at least DISCORD_TOKEN before starting the bot.",
    "",
]


def env_file_path(repo_root: str) -> str:
    return os.path.join(repo_root, ".env")


def ensure_env_file(repo_root: str) -> tuple[str, bool]:
    path = env_file_path(repo_root)
    if os.path.exists(path):
        _backfill_missing_default_keys(path)
        return path, False

    lines = list(_ENV_HEADER)
    for key, value in DEFAULT_ENV_VALUES.items():
        lines.append(f"{key}={value}")
    _write_lines_atomic(path, lines)
    return path, True


def _backfill_missing_default_keys(path: str) -> None:
    existing = load_env_dict(path)
    missing = [key for key in DEFAULT_ENV_VALUES.keys() if key not in existing]
    if not missing:
        return

    lines = _read_lines(path)
    if lines and lines[-1] != "":
        lines.append("")
    for key in missing:
        lines.append(f"{key}={DEFAULT_ENV_VALUES.get(key, '')}")
    _write_lines_atomic(path, lines)


def load_env_dict(path: str) -> dict[str, str]:
    values = {}
    if not os.path.exists(path):
        return values

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                parsed = _parse_env_line(line)
                if parsed is None:
                    continue
                key, value = parsed
                values[key] = value
    except Exception:
        return {}
    return values


def save_env_merged(repo_root: str, data: dict) -> dict[str, str]:
    path, _created = ensure_env_file(repo_root)
    existing_lines = _read_lines(path)
    merged = load_env_dict(path)

    updates = {}
    for key, value in (data or {}).items():
        norm_key = str(key or "").strip()
        if not norm_key:
            continue
        updates[norm_key] = "" if value is None else str(value)

    merged.update(updates)

    remaining = dict(updates)
    out_lines = []
    for line in existing_lines:
        parsed = _parse_env_line(line)
        if parsed is None:
            out_lines.append(line.rstrip("\n"))
            continue
        key, _old = parsed
        if key in remaining:
            out_lines.append(f"{key}={remaining.pop(key)}")
        else:
            out_lines.append(line.rstrip("\n"))

    if remaining:
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        for key, value in remaining.items():
            out_lines.append(f"{key}={value}")

    _write_lines_atomic(path, out_lines)
    return merged


def save_env_dict(repo_root: str, data: dict) -> dict[str, str]:
    path, _created = ensure_env_file(repo_root)
    sanitized = {}
    for key, value in (data or {}).items():
        norm_key = str(key or "").strip()
        if not norm_key:
            continue
        sanitized[norm_key] = "" if value is None else str(value)

    out_lines = list(_ENV_HEADER)
    for key, value in sanitized.items():
        out_lines.append(f"{key}={value}")
    _write_lines_atomic(path, out_lines)
    return sanitized


def _parse_env_line(line: str):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None

    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        value = value[1:-1]
    return key, value


def _read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().splitlines()
    except Exception:
        return []


def _write_lines_atomic(path: str, lines: list[str]) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=folder,
        delete=False,
        suffix=".tmp",
        newline="\n",
    ) as tf:
        content = "\n".join(lines)
        if content and not content.endswith("\n"):
            content += "\n"
        tf.write(content)
        tmp_name = tf.name
    os.replace(tmp_name, path)
