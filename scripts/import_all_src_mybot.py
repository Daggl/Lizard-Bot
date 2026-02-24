import pkgutil
import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "src" / "mybot"
sys.path.insert(0, str(root.parents[1]))

failed = []
count = 0
for finder, name, ispkg in pkgutil.walk_packages([str(root)], prefix="src.mybot."):
    try:
        importlib.import_module(name)
        count += 1
    except Exception as e:
        failed.append((name, e))

print(f"Imported {count} modules under src.mybot")
if failed:
    print("Failures:")
    for n, e in failed:
        print(n, "=>", repr(e))
    raise SystemExit(2)
else:
    print("All imports OK")
