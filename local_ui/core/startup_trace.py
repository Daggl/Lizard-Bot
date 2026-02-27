import os
from datetime import datetime

from .repo_paths import get_repo_root


def write_startup_trace():
    if os.environ.get("UI_EVENT_TRACE") != "1":
        return
    try:
        trace_dir = os.path.join(get_repo_root(), "data", "logs")
        os.makedirs(trace_dir, exist_ok=True)
        with open(os.path.join(trace_dir, "ui_run_trace.log"), "a", encoding="utf-8") as tf:
            tf.write(f"startup: {datetime.now().isoformat()}\\n")
        print("UI startup: trace written", flush=True)
    except Exception:
        try:
            print("UI startup: trace failed", flush=True)
        except Exception:
            pass
