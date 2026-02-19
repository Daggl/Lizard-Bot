import os
import json


def _repo_root():
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_config_dir():
	root = _repo_root()
	cfg_dir = os.path.join(root, "config")
	os.makedirs(cfg_dir, exist_ok=True)
	return cfg_dir


def ensure_configs_from_example():
	root = _repo_root()
	example_path = os.path.join(root, "config.example.json")
	cfg_dir = _ensure_config_dir()

	if not os.path.exists(example_path):
		return []

	try:
		with open(example_path, "r", encoding="utf-8") as f:
			data = json.load(f)
	except Exception:
		return []

	created = []

	if isinstance(data, dict):
		for key, value in data.items():
			target = os.path.join(cfg_dir, f"{key}.json")
			if not os.path.exists(target):
				try:
					with open(target, "w", encoding="utf-8") as out:
						json.dump(value or {}, out, indent=4)
					created.append(os.path.basename(target))
				except Exception:
					continue

	return created


def load_cog_config(name: str) -> dict:
	cfg_dir = _ensure_config_dir()
	path = os.path.join(cfg_dir, f"{name}.json")

	if not os.path.exists(path):
		return {}

	try:
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return {}


__all__ = ["load_cog_config", "ensure_configs_from_example"]
