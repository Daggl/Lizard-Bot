import json
import os
import sys


def main():
    example_path = os.path.join(os.getcwd(), "data", "config.example.json")

    if not os.path.exists(example_path):
        print("ERROR: data/config.example.json not found")
        sys.exit(1)

    try:
        with open(example_path, "r", encoding="utf-8") as fh:
            example = json.load(fh)
    except Exception as exc:
        print("ERROR: failed to read example:", exc)
        sys.exit(1)

    os.makedirs("config", exist_ok=True)

    created = []

    if isinstance(example, dict):
        for key, val in example.items():
            target = os.path.join("config", f"{key}.json")
            if os.path.exists(target):
                continue
            try:
                with open(target, "w", encoding="utf-8") as out:
                    json.dump(val or {}, out, indent=2, ensure_ascii=False)
                created.append(target)
            except Exception as exc:
                print("WARN: failed to write", target, exc)

    print("CREATED", created)


if __name__ == "__main__":
    main()
