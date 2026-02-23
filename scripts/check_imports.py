import importlib
import os
import sys
import traceback

root = os.path.abspath("src")
# Ensure `src` is on sys.path so imports like `mybot...` work
if root not in sys.path:
    sys.path.insert(0, root)
modules = []
for dirpath, dirs, files in os.walk(os.path.join(root, "mybot")):
    for f in files:
        if f.endswith(".py") and f != "__main__.py":
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace("\\", ".")
            modules.append(rel[:-3])
errors = 0
print("FOUND", len(modules), "modules")
for m in sorted(modules):
    try:
        importlib.import_module(m)
        print("OK", m)
    except Exception:
        errors += 1
        print("\nERR", m, ":")
        traceback.print_exc()
print("\nDONE errors=", errors)
