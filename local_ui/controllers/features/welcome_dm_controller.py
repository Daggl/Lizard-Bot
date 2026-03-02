"""Controller mixin for per-guild Welcome DM configuration."""

from config.config_io import (config_json_path, load_guild_config,
                              save_json_merged)
from PySide6 import QtWidgets


class WelcomeDmControllerMixin:
    """Mixin that adds Welcome DM config load/save to the main window."""

    def _welcome_dm_config_path(self):
        return config_json_path(
            self._repo_root, "welcome_dm.json",
            guild_id=getattr(self, "_active_guild_id", None),
        )

    def _load_welcome_dm_config(self):
        gid = getattr(self, "_active_guild_id", None)
        cfg = load_guild_config(self._repo_root, "welcome_dm.json", guild_id=gid)
        if not isinstance(cfg, dict):
            cfg = {}

        try:
            if hasattr(self, "wdm_enabled"):
                self.wdm_enabled.setChecked(bool(cfg.get("ENABLED", False)))
            if hasattr(self, "wdm_message") and not self.wdm_message.hasFocus():
                self.wdm_message.setPlainText(str(cfg.get("MESSAGE", "") or ""))
            if hasattr(self, "wdm_embed_title") and not self.wdm_embed_title.hasFocus():
                self.wdm_embed_title.setText(str(cfg.get("EMBED_TITLE", "") or ""))
            if hasattr(self, "wdm_embed_description") and not self.wdm_embed_description.hasFocus():
                self.wdm_embed_description.setPlainText(str(cfg.get("EMBED_DESCRIPTION", "") or ""))
            if hasattr(self, "wdm_embed_color") and not self.wdm_embed_color.hasFocus():
                self.wdm_embed_color.setText(str(cfg.get("EMBED_COLOR", "#5865F2") or "#5865F2"))
        except Exception:
            pass

    def _save_welcome_dm_settings(self, reload_after: bool = False):
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

            payload = {
                "ENABLED": self.wdm_enabled.isChecked(),
                "MESSAGE": (self.wdm_message.toPlainText() or "").strip(),
                "EMBED_TITLE": (self.wdm_embed_title.text() or "").strip(),
                "EMBED_DESCRIPTION": (self.wdm_embed_description.toPlainText() or "").strip(),
                "EMBED_COLOR": (self.wdm_embed_color.text() or "#5865F2").strip(),
            }

            path = self._welcome_dm_config_path()
            if not path:
                QtWidgets.QMessageBox.warning(
                    self, "Welcome DM", "No guild selected."
                )
                return

            save_json_merged(path, payload)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"}, timeout=3.0,
                        cb=self._on_reload_after_save_welcome_dm,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Welcome DM settings saved.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _on_reload_after_save_welcome_dm(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_welcome_dm_config()
                except Exception:
                    pass
        except Exception:
            pass
