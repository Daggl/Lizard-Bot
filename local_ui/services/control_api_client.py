import json
import os
import socket

from config.config_io import ensure_env_file, load_env_dict
from core.repo_paths import get_repo_root

API_ADDR = ("127.0.0.1", 8765)


def _current_control_api_token() -> str:
    try:
        repo_root = get_repo_root()
        env_path, _created = ensure_env_file(repo_root)
        data = load_env_dict(env_path)
        token = str(data.get("CONTROL_API_TOKEN", "") or "").strip()
        if token:
            return token
    except Exception:
        pass
    return str(os.environ.get("CONTROL_API_TOKEN", "") or "").strip()


def send_cmd(cmd: dict, timeout: float = 10.0):
    try:
        token = _current_control_api_token()
        payload = dict(cmd)
        if token:
            payload["token"] = token

        with socket.create_connection(API_ADDR, timeout=timeout) as s:
            s.sendall((json.dumps(payload) + "\n").encode())
            buf = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    break
            line = buf.split(b"\n", 1)[0]
            return json.loads(line.decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}
