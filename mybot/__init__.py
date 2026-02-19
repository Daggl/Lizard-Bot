import os

# Lightweight top-level package that points to the real package under src/mybot
# This helps static analyzers and runtime imports when `src/` is not on sys.path.
__path__.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "mybot")))
