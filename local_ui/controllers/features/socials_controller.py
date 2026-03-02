"""Controller mixin for per-guild Social Media configuration."""

from config.config_io import (config_json_path, load_guild_config,
                              save_json_merged)
from PySide6 import QtWidgets


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def _read_table_entries(table: QtWidgets.QTableWidget) -> str:
    """Read all non-empty entries from a single-column QTableWidget as comma-separated string."""
    entries = []
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item:
            text = item.text().strip()
            if text:
                entries.append(text)
    return ",".join(entries)


def _populate_table_from_csv(table: QtWidgets.QTableWidget, csv_value: str):
    """Populate a single-column QTableWidget from a comma-separated string."""
    entries = [e.strip() for e in str(csv_value or "").split(",") if e.strip()]
    table.setRowCount(len(entries))
    for i, entry in enumerate(entries):
        table.setItem(i, 0, QtWidgets.QTableWidgetItem(entry))


def _read_route_table(table: QtWidgets.QTableWidget) -> dict:
    """Read a 2-column (Creator, Channel ID) route table into a dict."""
    routes = {}
    for row in range(table.rowCount()):
        creator_item = table.item(row, 0)
        channel_item = table.item(row, 1)
        if creator_item and channel_item:
            creator = creator_item.text().strip().lower()
            ch_raw = channel_item.text().strip()
            if creator and ch_raw and ch_raw.isdigit():
                routes[creator] = int(ch_raw)
    return routes


def _populate_route_table(table: QtWidgets.QTableWidget, channel_map: dict):
    """Populate a 2-column route table from a dict {creator: channel_id}."""
    if not isinstance(channel_map, dict):
        channel_map = {}
    table.setRowCount(len(channel_map))
    for i, (creator, ch_id) in enumerate(channel_map.items()):
        table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(creator)))
        table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(ch_id)))


class SocialsControllerMixin:
    """Mixin that adds Social Media config load/save to the main window."""

    def _socials_config_path(self):
        return config_json_path(
            self._repo_root, "social_media.json",
            guild_id=getattr(self, "_active_guild_id", None),
        )

    def _load_socials_config(self):
        gid = getattr(self, "_active_guild_id", None)
        cfg = load_guild_config(self._repo_root, "social_media.json", guild_id=gid)
        if not isinstance(cfg, dict):
            cfg = {}

        try:
            # Twitch
            twitch = cfg.get("TWITCH", {}) if isinstance(cfg.get("TWITCH"), dict) else {}
            if hasattr(self, "sm_twitch_enabled"):
                self.sm_twitch_enabled.setChecked(bool(twitch.get("ENABLED", False)))
            if hasattr(self, "sm_twitch_channel_id") and not self.sm_twitch_channel_id.hasFocus():
                cid = str(twitch.get("CHANNEL_ID", "") or "").strip()
                self.sm_twitch_channel_id.setText(cid if cid and cid != "0" else "")
            if hasattr(self, "sm_twitch_usernames_table") and not self.sm_twitch_usernames_table.hasFocus():
                _populate_table_from_csv(self.sm_twitch_usernames_table, twitch.get("USERNAMES", ""))
            if hasattr(self, "sm_twitch_client_id") and not self.sm_twitch_client_id.hasFocus():
                self.sm_twitch_client_id.setText(str(twitch.get("CLIENT_ID", "") or ""))
            if hasattr(self, "sm_twitch_oauth") and not self.sm_twitch_oauth.hasFocus():
                self.sm_twitch_oauth.setText(str(twitch.get("OAUTH_TOKEN", "") or ""))
            if hasattr(self, "sm_twitch_routes_table") and not self.sm_twitch_routes_table.hasFocus():
                _populate_route_table(self.sm_twitch_routes_table, twitch.get("CHANNEL_MAP", {}))

            # YouTube
            youtube = cfg.get("YOUTUBE", {}) if isinstance(cfg.get("YOUTUBE"), dict) else {}
            if hasattr(self, "sm_youtube_enabled"):
                self.sm_youtube_enabled.setChecked(bool(youtube.get("ENABLED", False)))
            if hasattr(self, "sm_youtube_channel_id") and not self.sm_youtube_channel_id.hasFocus():
                cid = str(youtube.get("CHANNEL_ID", "") or "").strip()
                self.sm_youtube_channel_id.setText(cid if cid and cid != "0" else "")
            if hasattr(self, "sm_youtube_ids_table") and not self.sm_youtube_ids_table.hasFocus():
                _populate_table_from_csv(self.sm_youtube_ids_table, youtube.get("YOUTUBE_CHANNEL_IDS", ""))
            if hasattr(self, "sm_youtube_routes_table") and not self.sm_youtube_routes_table.hasFocus():
                _populate_route_table(self.sm_youtube_routes_table, youtube.get("CHANNEL_MAP", {}))

            # Twitter/X
            twitter = cfg.get("TWITTER", {}) if isinstance(cfg.get("TWITTER"), dict) else {}
            if hasattr(self, "sm_twitter_enabled"):
                self.sm_twitter_enabled.setChecked(bool(twitter.get("ENABLED", False)))
            if hasattr(self, "sm_twitter_channel_id") and not self.sm_twitter_channel_id.hasFocus():
                cid = str(twitter.get("CHANNEL_ID", "") or "").strip()
                self.sm_twitter_channel_id.setText(cid if cid and cid != "0" else "")
            if hasattr(self, "sm_twitter_bearer") and not self.sm_twitter_bearer.hasFocus():
                self.sm_twitter_bearer.setText(str(twitter.get("BEARER_TOKEN", "") or ""))
            if hasattr(self, "sm_twitter_usernames_table") and not self.sm_twitter_usernames_table.hasFocus():
                _populate_table_from_csv(self.sm_twitter_usernames_table, twitter.get("USERNAMES", ""))
            if hasattr(self, "sm_twitter_routes_table") and not self.sm_twitter_routes_table.hasFocus():
                _populate_route_table(self.sm_twitter_routes_table, twitter.get("CHANNEL_MAP", {}))

            # TikTok
            tiktok = cfg.get("TIKTOK", {}) if isinstance(cfg.get("TIKTOK"), dict) else {}
            if hasattr(self, "sm_tiktok_enabled"):
                self.sm_tiktok_enabled.setChecked(bool(tiktok.get("ENABLED", False)))
            if hasattr(self, "sm_tiktok_channel_id") and not self.sm_tiktok_channel_id.hasFocus():
                cid = str(tiktok.get("CHANNEL_ID", "") or "").strip()
                self.sm_tiktok_channel_id.setText(cid if cid and cid != "0" else "")
            if hasattr(self, "sm_tiktok_usernames_table") and not self.sm_tiktok_usernames_table.hasFocus():
                _populate_table_from_csv(self.sm_tiktok_usernames_table, tiktok.get("USERNAMES", ""))
            if hasattr(self, "sm_tiktok_routes_table") and not self.sm_tiktok_routes_table.hasFocus():
                _populate_route_table(self.sm_tiktok_routes_table, tiktok.get("CHANNEL_MAP", {}))
        except Exception:
            pass

    def _save_socials_config(self, data: dict):
        save_json_merged(self._socials_config_path(), data or {})

    def _on_reload_after_save_socials(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_socials_config()
                except Exception:
                    pass
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg += "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception:
            pass

    def _save_socials_settings(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(
                    self, "Safe Mode",
                    "Nur lesen ist aktiv: Speichern ist deaktiviert.",
                )
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(
                    self, "Safe Mode",
                    "Auto reload ist aus: Speichern ohne Reload.",
                )

            # Validate channel IDs
            def _parse_cid(widget):
                raw = (widget.text() or "").strip()
                if not raw:
                    return 0
                if not raw.isdigit():
                    raise ValueError(f"Channel ID must contain only digits: {raw}")
                return int(raw)

            try:
                twitch_cid = _parse_cid(self.sm_twitch_channel_id)
                youtube_cid = _parse_cid(self.sm_youtube_channel_id)
                twitter_cid = _parse_cid(self.sm_twitter_channel_id)
                tiktok_cid = _parse_cid(self.sm_tiktok_channel_id)
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Social Media", str(exc))
                return

            payload = {
                "TWITCH": {
                    "ENABLED": self.sm_twitch_enabled.isChecked(),
                    "CHANNEL_ID": twitch_cid,
                    "USERNAMES": _read_table_entries(self.sm_twitch_usernames_table),
                    "CLIENT_ID": (self.sm_twitch_client_id.text() or "").strip(),
                    "OAUTH_TOKEN": (self.sm_twitch_oauth.text() or "").strip(),
                    "CHANNEL_MAP": _read_route_table(self.sm_twitch_routes_table) if hasattr(self, "sm_twitch_routes_table") else {},
                },
                "YOUTUBE": {
                    "ENABLED": self.sm_youtube_enabled.isChecked(),
                    "CHANNEL_ID": youtube_cid,
                    "YOUTUBE_CHANNEL_IDS": _read_table_entries(self.sm_youtube_ids_table),
                    "CHANNEL_MAP": _read_route_table(self.sm_youtube_routes_table) if hasattr(self, "sm_youtube_routes_table") else {},
                },
                "TWITTER": {
                    "ENABLED": self.sm_twitter_enabled.isChecked(),
                    "CHANNEL_ID": twitter_cid,
                    "BEARER_TOKEN": (self.sm_twitter_bearer.text() or "").strip(),
                    "USERNAMES": _read_table_entries(self.sm_twitter_usernames_table),
                    "CHANNEL_MAP": _read_route_table(self.sm_twitter_routes_table) if hasattr(self, "sm_twitter_routes_table") else {},
                },
                "TIKTOK": {
                    "ENABLED": self.sm_tiktok_enabled.isChecked(),
                    "CHANNEL_ID": tiktok_cid,
                    "USERNAMES": _read_table_entries(self.sm_tiktok_usernames_table),
                    "CHANNEL_MAP": _read_route_table(self.sm_tiktok_routes_table) if hasattr(self, "sm_tiktok_routes_table") else {},
                },
                "CUSTOM": {
                    "ENABLED": False,
                    "CHANNEL_ID": 0,
                    "FEED_URLS": "",
                },
            }
            self._save_socials_config(payload)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_socials,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Save error", str(e))
