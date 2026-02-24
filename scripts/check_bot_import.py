import importlib
import sys
from pathlib import Path

# Ensure repository root is on sys.path so `src` package is discoverable
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

try:
    importlib.import_module("src.mybot.lizard")
    print("import-ok")
except Exception as e:
    print("import-failed:", e)
    raise
