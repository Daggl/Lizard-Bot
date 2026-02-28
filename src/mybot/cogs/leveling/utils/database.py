import json
import os
import time

from mybot.utils.paths import guild_data_path


class Database:
    """Per-guild level database with in-memory caching."""

    def __init__(self):
        # Cache: guild_id -> user data dict
        self._cache: dict[str, dict] = {}

    def _get_data_path(self, guild_id: int | str | None) -> str:
        """Get the path to the levels data file for a guild."""
        return guild_data_path(guild_id, "levels_data.json")

    def _load_guild(self, guild_id: int | str | None) -> dict:
        """Load data for a specific guild into cache."""
        gid = str(guild_id) if guild_id else ""
        if gid in self._cache:
            return self._cache[gid]

        path = self._get_data_path(guild_id)
        if not path:
            self._cache[gid] = {}
            return self._cache[gid]

        if not os.path.exists(path):
            self._cache[gid] = {}
            return self._cache[gid]

        try:
            with open(path, "r", encoding="utf-8") as f:
                self._cache[gid] = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # backup corrupt file
            backup_name = path + f".bad-{int(time.time())}"
            try:
                os.replace(path, backup_name)
            except Exception:
                pass
            self._cache[gid] = {}

        return self._cache[gid]

    def _save_guild(self, guild_id: int | str | None):
        """Save data for a specific guild to disk."""
        gid = str(guild_id) if guild_id else ""
        path = self._get_data_path(guild_id)
        if not path:
            return

        data = self._cache.get(gid, {})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load(self, guild_id: int | str | None = None):
        """Load data for a guild (or reload cache)."""
        gid = str(guild_id) if guild_id else ""
        # Force reload from disk
        if gid in self._cache:
            del self._cache[gid]
        self._load_guild(guild_id)

    def save(self, guild_id: int | str | None = None):
        """Save data for a specific guild."""
        self._save_guild(guild_id)

    def get_user(self, user_id, guild_id: int | str | None = None):
        """Get user data for a specific guild."""
        data = self._load_guild(guild_id)
        user_id = str(user_id)

        if user_id not in data:
            data[user_id] = {
                "xp": 0,
                "level": 1,
                "messages": 0,
                "voice_time": 0,
                "achievements": [],
            }

        return data[user_id]

    @property
    def data(self):
        """Deprecated: For backward compatibility. Returns empty dict."""
        # This was used for global access, now deprecated
        return {}
