import os
import shutil
import time


def cleanup_tracked(tracked_path: str) -> int:
    """Remove consecutive or repeated 'Tailing' header lines from tracked.log.

    Returns number of lines removed.
    """
    if not os.path.exists(tracked_path):
        print("tracked.log not found:", tracked_path)
        return 0

    # backup
    bak = tracked_path + ".bak." + str(int(time.time()))
    shutil.copy2(tracked_path, bak)

    removed = 0
    out_lines = []
    last_relevant = None

    def is_header(line: str) -> bool:
        s = line.strip()
        return s.startswith("--- Tailing") or s.startswith("--- Tailing DB:")

    with open(tracked_path, "r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            if is_header(raw):
                # skip if same as last relevant (ignoring blank lines between)
                if last_relevant is not None and last_relevant.strip() == raw.strip():
                    removed += 1
                    continue
                out_lines.append(raw)
                last_relevant = raw
            else:
                out_lines.append(raw)
                # update last_relevant only for non-blank content
                if raw.strip():
                    last_relevant = raw

    # write back
    tmp_path = tracked_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", errors="ignore") as fh:
        fh.writelines(out_lines)
    shutil.move(tmp_path, tracked_path)

    return removed


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tracked_path = os.path.join(repo_root, "data", "logs", "tracked.log")
    removed = cleanup_tracked(tracked_path)
    print(f"Cleanup complete. Lines removed: {removed}")
    print(f"Backup of original file created alongside tracked.log with .bak timestamp")


if __name__ == '__main__':
    main()
