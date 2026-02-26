import os


def get_repo_root() -> str:
    env_root = os.environ.get("DC_BOT_REPO_ROOT")
    if env_root:
        try:
            abs_env = os.path.abspath(env_root)
            if os.path.isdir(abs_env):
                return abs_env
        except Exception:
            pass

    here = os.path.abspath(os.path.dirname(__file__))
    candidate = os.path.abspath(os.path.join(here, ".."))
    if os.path.exists(os.path.join(candidate, "data", "config.example.json")):
        return candidate

    current = here
    while True:
        if os.path.exists(os.path.join(current, "data", "config.example.json")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return candidate
