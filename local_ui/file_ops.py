import os
import time


def prune_backups(target_path: str, keep: int = 5):
    try:
        folder = os.path.dirname(target_path)
        base = os.path.basename(target_path)
        prefix = f"{base}.bak."
        backups = []
        for name in os.listdir(folder):
            if not name.startswith(prefix):
                continue
            full = os.path.join(folder, name)
            try:
                mtime = os.path.getmtime(full)
            except Exception:
                mtime = 0
            backups.append((mtime, full))

        backups.sort(key=lambda item: item[0], reverse=True)
        for _, old_path in backups[max(0, int(keep)):]:
            try:
                os.remove(old_path)
            except Exception:
                pass
    except Exception:
        pass


def rotate_log_file(log_path: str, max_bytes: int = 2_000_000, keep: int = 5):
    try:
        if not log_path or not os.path.exists(log_path):
            return
        if os.path.getsize(log_path) < int(max_bytes):
            return
        rotated = f"{log_path}.bak.{int(time.time())}"
        os.replace(log_path, rotated)
        prune_backups(log_path, keep=keep)
    except Exception:
        pass


def open_tracked_writer(repo_root: str, current_fp, header: str):
    try:
        tracked_dir = os.path.join(repo_root, "data", "logs")
        os.makedirs(tracked_dir, exist_ok=True)
        tracked_path = os.path.join(tracked_dir, "tracked.log")
        rotate_log_file(tracked_path, max_bytes=2_000_000, keep=5)

        if current_fp:
            try:
                current_fp.close()
            except Exception:
                pass

        fp = open(tracked_path, "a", encoding="utf-8", errors="ignore")
        try:
            fp.write(header + "\n")
            fp.flush()
        except Exception:
            pass
        return fp
    except Exception:
        return current_fp
