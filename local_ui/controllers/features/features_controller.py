"""Controller mixin for per-guild feature toggles."""

from config.config_io import config_json_path, load_guild_config, save_json_merged
from PySide6 import QtWidgets

# Feature keys and their UI descriptions (matches bot-side FEATURES dict).
FEATURE_DEFS = {
    "leveling": {
        "label": "Leveling / XP / Rank",
        "desc": "Users earn XP through messages and voice time. Includes /rank, /leaderboard, level-up announcements and role rewards.",
    },
    "achievements": {
        "label": "Achievements",
        "desc": "Milestone badges awarded automatically or by admins. Displayed on the rank card.",
    },
    "birthdays": {
        "label": "Birthdays",
        "desc": "Users register their birthday with /birthday. The bot sends a congratulation embed on the day.",
    },
    "polls": {
        "label": "Polls",
        "desc": "Create interactive polls with /poll. Supports multiple options and timed closing.",
    },
    "counting": {
        "label": "Counting",
        "desc": "A counting channel game where users count up together. Tracks records and leaderboards.",
    },
    "welcome": {
        "label": "Welcome & Autorole",
        "desc": "Sends a welcome message when a member joins and optionally assigns autoroles.",
    },
    "tickets": {
        "label": "Tickets",
        "desc": "A support ticket system with ticket panels, claim, transcript and close actions.",
    },
    "tempvoice": {
        "label": "TempVoice",
        "desc": "Automatically creates temporary voice channels when users join a designated create-channel.",
    },
    "music": {
        "label": "Music",
        "desc": "Play music from YouTube or import Spotify playlists. Includes queue, skip, stop controls.",
    },
    "logging": {
        "label": "Server Logging",
        "desc": "Logs chat, voice, mod, member and server events to configured channels and the SQLite database.",
    },
    "memes": {
        "label": "Memes",
        "desc": "Create and store memes from images/GIFs with captions. Retrievable by name via /meme show.",
    },
    "membercount": {
        "label": "Member Count Channel",
        "desc": "A voice channel that displays the current member count. Updates automatically when members join or leave.",
    },
    "freestuff": {
        "label": "Free Stuff",
        "desc": "Automatically posts free game and software giveaways (Epic Games, Steam, GOG, etc.) to a configured channel.",
    },
    "socials": {
        "label": "Social Media",
        "desc": "Posts notifications for Twitch streams, YouTube uploads and other social media activity to configured channels. Supports per-creator channel routing.",
    },
    "welcome_dm": {
        "label": "Welcome DM",
        "desc": "Sends a configurable private message to newly joined members. Supports placeholders and optional embeds.",
    },
}

# Order for display
FEATURE_ORDER = [
    "leveling", "achievements", "birthdays", "polls", "counting",
    "welcome", "tickets", "tempvoice", "music", "logging", "memes",
    "membercount", "freestuff", "socials", "welcome_dm",
]


class FeaturesControllerMixin:
    """Mixin that adds per-guild feature toggle load/save."""

    def _features_config_path(self):
        return config_json_path(
            self._repo_root, "features.json",
            guild_id=getattr(self, "_active_guild_id", None),
        )

    def _load_features_config(self):
        """Load feature flags and update checkbox states in the UI."""
        gid = getattr(self, "_active_guild_id", None)
        cfg = load_guild_config(self._repo_root, "features.json", guild_id=gid)
        if not isinstance(cfg, dict):
            cfg = {}

        for key in FEATURE_ORDER:
            chk = getattr(self, f"feat_chk_{key}", None)
            if chk is not None:
                enabled = bool(cfg.get(key, True))  # default enabled
                chk.setChecked(enabled)

        # Update tab visibility based on features
        self._update_feature_tab_visibility(cfg)

    def _save_features_config(self):
        """Collect checkbox states and persist to features.json."""
        data = {}
        for key in FEATURE_ORDER:
            chk = getattr(self, f"feat_chk_{key}", None)
            if chk is not None:
                data[key] = chk.isChecked()

        path = self._features_config_path()
        if not path:
            QtWidgets.QMessageBox.warning(
                self, "Features", "No guild selected — please pick a guild first."
            )
            return

        save_json_merged(path, data)

        # Trigger bot reload so the new flags take effect immediately
        try:
            self.send_cmd_async(
                {"action": "reload"}, timeout=3.0,
                cb=self._on_reload_after_save_features,
            )
        except Exception:
            pass

        # Re-sync guild slash commands so disabled features vanish from Discord
        gid = getattr(self, "_active_guild_id", None)
        if gid:
            try:
                self.send_cmd_async(
                    {"action": "sync_guild_commands", "guild_id": str(gid)},
                    timeout=10.0,
                    cb=self._on_sync_after_save_features,
                )
            except Exception:
                pass

        try:
            self._set_status("Feature flags saved")
        except Exception:
            pass

        # Refresh the config editor so disabled features' files are hidden
        try:
            if hasattr(self, "cfg_editor") and self.cfg_editor is not None:
                self.cfg_editor.refresh_list()
        except Exception:
            pass

        # Update tab visibility
        self._update_feature_tab_visibility(data)

    # Mapping from tab title to feature key
    _TAB_TO_FEATURE = {
        "Welcome": "welcome",
        "Rankcard": "leveling",
        "Leveling": "leveling",
        "Birthdays": "birthdays",
        "Free Stuff": "freestuff",
        "Social Media": "socials",
        "Welcome DM": "welcome_dm",
    }

    def _update_feature_tab_visibility(self, features: dict):
        """Show/hide tabs whose feature is disabled."""
        if not features:
            return
        try:
            tabs = self.centralWidget()
            if not isinstance(tabs, QtWidgets.QTabWidget):
                return
            for i in range(tabs.count()):
                tab_title = tabs.tabText(i)
                feature_key = self._TAB_TO_FEATURE.get(tab_title)
                if feature_key is not None:
                    visible = bool(features.get(feature_key, True))
                    tabs.setTabVisible(i, visible)
        except Exception:
            pass

    def _on_reload_after_save_features(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_features_config()
                except Exception:
                    pass
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Features saved. Reloaded: {len(reloaded)} modules."
                if failed:
                    msg += "\nFailed: " + ", ".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Features", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Features", f"Save OK but reload failed: {r}")
        except Exception:
            pass

    def _on_sync_after_save_features(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._set_status("Slash commands synced for guild")
                except Exception:
                    pass
            else:
                error = r.get("error", "unknown")
                try:
                    self._set_status(f"Command sync failed: {error}")
                except Exception:
                    pass
        except Exception:
            pass
