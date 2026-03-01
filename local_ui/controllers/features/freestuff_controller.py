"""Controller mixin for per-guild Free Stuff configuration."""

from config.config_io import (config_json_path, load_guild_config,
                              save_json_merged)
from PySide6 import QtWidgets


class FreeStuffControllerMixin:
    """Mixin that adds Free Stuff config load/save to the main window."""

    def _freestuff_config_path(self):
        return config_json_path(
            self._repo_root, "freestuff.json",
            guild_id=getattr(self, "_active_guild_id", None),
        )

    def _load_freestuff_config(self):
        gid = getattr(self, "_active_guild_id", None)
        cfg = load_guild_config(self._repo_root, "freestuff.json", guild_id=gid)
        if not isinstance(cfg, dict):
            cfg = {}

        try:
            if hasattr(self, "fs_channel_id") and not self.fs_channel_id.hasFocus():
                cid = str(cfg.get("CHANNEL_ID", "") or "").strip()
                self.fs_channel_id.setText(cid if cid and cid != "0" else "")
            for key in ("EPIC", "STEAM", "GOG", "HUMBLE", "MISC"):
                chk = getattr(self, f"fs_source_{key.lower()}", None)
                if chk is not None:
                    chk.setChecked(bool(cfg.get(f"SOURCE_{key}", True)))
        except Exception:
            pass

    def _save_freestuff_config(self, data: dict):
        save_json_merged(self._freestuff_config_path(), data or {})

    def _on_reload_after_save_freestuff(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_freestuff_config()
                except Exception as e:
                    self._debug_log(f"reload-after-freestuff: load failed: {e}")
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg += "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception as e:
            self._debug_log(f"reload-after-freestuff handler failed: {e}")

    def _save_freestuff_settings(self, reload_after: bool = False):
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

            # Parse channel ID
            cid_raw = (self.fs_channel_id.text() or "").strip()
            channel_id = 0
            if cid_raw:
                if not cid_raw.isdigit():
                    QtWidgets.QMessageBox.warning(
                        self, "Free Stuff",
                        "Channel ID must contain only digits.",
                    )
                    return
                channel_id = int(cid_raw)

            payload = {
                "CHANNEL_ID": channel_id,
                "SOURCE_EPIC": self.fs_source_epic.isChecked(),
                "SOURCE_STEAM": self.fs_source_steam.isChecked(),
                "SOURCE_GOG": self.fs_source_gog.isChecked(),
                "SOURCE_HUMBLE": self.fs_source_humble.isChecked(),
                "SOURCE_MISC": self.fs_source_misc.isChecked(),
            }
            self._save_freestuff_config(payload)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_freestuff,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Free Stuff settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to save Free Stuff settings: {e}"
            )
