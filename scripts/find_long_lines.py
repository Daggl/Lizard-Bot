import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: find_long_lines.py <file> [maxlen]")
    sys.exit(2)

p = Path(sys.argv[1])
maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 88

lines = p.read_text(encoding="utf-8").splitlines()
for i, l in enumerate(lines, 1):
    if len(l) > maxlen:
        print(f"{i}:{len(l)}: {l}")
