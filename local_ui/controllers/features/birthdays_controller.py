from config.config_io import (config_json_path, load_guild_config,
                              load_json_dict, save_json_merged)
from PySide6 import QtGui, QtWidgets


class BirthdaysControllerMixin:
    def _birthdays_config_path(self):
        return config_json_path(self._repo_root, "birthdays.json", guild_id=getattr(self, '_active_guild_id', None))

    def _load_birthdays_config(self):
        gid = getattr(self, '_active_guild_id', None)
        cfg = load_guild_config(self._repo_root, "birthdays.json", guild_id=gid)
        if not isinstance(cfg, dict):
            cfg = {}

        embed_title = str(cfg.get("EMBED_TITLE", "") or "")
        embed_desc = str(cfg.get("EMBED_DESCRIPTION", "") or "")
        embed_footer = str(cfg.get("EMBED_FOOTER", "") or "")
        embed_color = str(cfg.get("EMBED_COLOR", "") or "").strip()
        role_id = str(cfg.get("ROLE_ID", "") or "").strip()

        try:
            if hasattr(self, "bd_embed_title") and not self.bd_embed_title.hasFocus():
                self.bd_embed_title.setText(embed_title)
            if hasattr(self, "bd_embed_description") and not self.bd_embed_description.hasFocus():
                self.bd_embed_description.setPlainText(embed_desc)
            if hasattr(self, "bd_embed_footer") and not self.bd_embed_footer.hasFocus():
                self.bd_embed_footer.setText(embed_footer)
            if hasattr(self, "bd_embed_color") and not self.bd_embed_color.hasFocus():
                self.bd_embed_color.setText(embed_color)
            if hasattr(self, "bd_role_id") and not self.bd_role_id.hasFocus():
                self.bd_role_id.setText(role_id if role_id and role_id != "0" else "")
        except Exception:
            pass

    def _save_birthdays_config(self, data: dict):
        save_json_merged(self._birthdays_config_path(), data or {})

    def _on_reload_after_save_birthdays(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_birthdays_config()
                except Exception as e:
                    self._debug_log(f"reload-after-birthdays: load_birthdays_config failed: {e}")
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception as e:
            self._debug_log(f"reload-after-birthdays handler failed: {e}")

    def _save_birthday_settings(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")

            gid = getattr(self, '_active_guild_id', None)
            existing_cfg = load_guild_config(self._repo_root, "birthdays.json", guild_id=gid)
            if not isinstance(existing_cfg, dict):
                existing_cfg = {}
            existing_channel_id = existing_cfg.get("CHANNEL_ID", 0)
            try:
                existing_channel_id = int(existing_channel_id or 0)
            except Exception:
                existing_channel_id = 0

            color_raw = (self.bd_embed_color.text() or "").strip()
            if color_raw and not QtGui.QColor(color_raw).isValid():
                QtWidgets.QMessageBox.warning(self, "Birthdays", "Embed color must be a valid color (e.g. #F1C40F).")
                return

            # Parse role ID
            role_id_raw = (self.bd_role_id.text() or "").strip()
            role_id = 0
            if role_id_raw:
                if not role_id_raw.isdigit():
                    QtWidgets.QMessageBox.warning(self, "Birthdays", "Role ID must contain only digits.")
                    return
                role_id = int(role_id_raw)

            payload = {
                "CHANNEL_ID": existing_channel_id,
                "ROLE_ID": role_id,
                "EMBED_TITLE": (self.bd_embed_title.text() or "").strip(),
                "EMBED_DESCRIPTION": (self.bd_embed_description.toPlainText() or "").strip(),
                "EMBED_FOOTER": (self.bd_embed_footer.text() or "").strip(),
                "EMBED_COLOR": color_raw,
            }
            self._save_birthdays_config(payload)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_birthdays,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Birthday settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save birthday settings: {e}")
