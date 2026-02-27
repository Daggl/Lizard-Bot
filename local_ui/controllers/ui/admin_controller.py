from PySide6 import QtWidgets

from config.config_editor import ConfigEditor
from services.guides import open_bot_tutorial, open_commands_guide
from ui.setup_wizard import SetupWizardDialog


class AdminControllerMixin:
    def on_reload(self):
        self.send_cmd_async({"action": "reload"}, timeout=3.0, cb=self._on_reload_result)

    def _on_reload_result(self, r: dict):
        if r.get("ok"):
            reloaded = r.get("reloaded", [])
            failed = r.get("failed", {})
            msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
            details = ''
            if failed:
                details = '\n'.join(f"{k}: {v}" for k, v in failed.items())
                msg = msg + "\n" + details
            QtWidgets.QMessageBox.information(self, "Reload Cogs", msg)
        else:
            QtWidgets.QMessageBox.warning(self, "Reload Cogs", f"Failed: {r}")

    def _on_reload_after_save_rank(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_rank_config()
                except Exception as e:
                    self._debug_log(f"reload-after-rank: load_rank_config failed: {e}")
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception as e:
            self._debug_log(f"reload-after-rank handler failed: {e}")

    def _on_reload_after_save_preview(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_welcome_message_from_file()
                except Exception as e:
                    self._debug_log(f"reload-after-preview: load_welcome_message failed: {e}")
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception as e:
            self._debug_log(f"reload-after-preview handler failed: {e}")

    def on_edit_configs(self):
        try:
            tabs = self.parent().findChild(QtWidgets.QTabWidget)
        except Exception:
            tabs = None
        if tabs:
            for i in range(tabs.count()):
                if tabs.tabText(i) == "Configs":
                    tabs.setCurrentIndex(i)
                    return
        dlg = ConfigEditor(self)
        dlg.exec()

    def on_open_bot_tutorial(self):
        try:
            open_bot_tutorial(self)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Tutorial", f"Failed to open tutorial: {e}")

    def on_open_commands_guide(self):
        try:
            open_commands_guide(self)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Commands", f"Failed to open commands guide: {e}")

    def on_open_setup_wizard(self):
        try:
            dlg = SetupWizardDialog(self._repo_root, self, read_only=self._is_safe_read_only())
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                try:
                    self._load_rank_config()
                except Exception:
                    pass
                try:
                    self._load_leveling_config()
                except Exception:
                    pass
                try:
                    self._load_birthdays_config()
                except Exception:
                    pass
                try:
                    self._load_welcome_message_from_file()
                except Exception:
                    pass
                try:
                    self.update_preview()
                except Exception:
                    pass
                try:
                    self._set_status("Setup Wizard: saved")
                except Exception:
                    pass
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Setup Wizard", f"Failed to open setup wizard: {e}")

    def _is_safe_read_only(self) -> bool:
        try:
            chk = getattr(self, "safe_read_only_chk", None)
            return bool(chk.isChecked()) if chk is not None else False
        except Exception:
            return False

    def _is_safe_auto_reload_off(self) -> bool:
        try:
            chk = getattr(self, "safe_auto_reload_off_chk", None)
            return bool(chk.isChecked()) if chk is not None else False
        except Exception:
            return False

    def _apply_safe_debug_logging(self):
        try:
            chk = getattr(self, "safe_debug_logging_chk", None)
            enabled = bool(chk.isChecked()) if chk is not None else False
            if enabled:
                import os

                os.environ["UI_DEBUG"] = "1"
            else:
                import os

                os.environ.pop("UI_DEBUG", None)
        except Exception:
            pass

    def on_safe_mode_flags_changed(self, *_args):
        try:
            read_only = self._is_safe_read_only()
            debug_on = bool(getattr(self, "safe_debug_logging_chk", None).isChecked()) if getattr(self, "safe_debug_logging_chk", None) is not None else False
            auto_reload_off = self._is_safe_auto_reload_off()
            self._apply_safe_debug_logging()
            self._save_ui_settings(
                {
                    "safe_read_only": read_only,
                    "safe_debug_logging": debug_on,
                    "safe_auto_reload_off": auto_reload_off,
                }
            )
            try:
                self._set_status("Safe Mode updated")
            except Exception:
                pass
        except Exception:
            pass

    def _event_tester_channel_id_text(self) -> str:
        try:
            line_edit = getattr(self, "event_test_channel_id", None)
            if line_edit is None:
                return ""
            return str(line_edit.text() or "").strip()
        except Exception:
            return ""

    def on_event_test_channel_changed(self):
        try:
            raw = self._event_tester_channel_id_text()
            if raw and not raw.isdigit():
                QtWidgets.QMessageBox.warning(self, "Event Tester", "Channel ID must contain only digits.")
                return
            self._save_ui_settings({"event_test_channel_id": raw})
            try:
                self._set_status("Event Tester: channel saved")
            except Exception:
                pass
        except Exception:
            pass

    def _run_event_test(self, command_name: str, label: str):
        try:
            try:
                self._set_status(f"Event Tester: {label}...")
            except Exception:
                pass
            req = {"action": "event_test", "test": command_name}
            channel_id = self._event_tester_channel_id_text()
            if channel_id:
                if not channel_id.isdigit():
                    QtWidgets.QMessageBox.warning(self, "Event Tester", "Channel ID must contain only digits.")
                    return
                req["channel_id"] = channel_id
            self.send_cmd_async(
                req,
                timeout=25.0,
                cb=lambda r, lbl=label: self._on_event_test_result(lbl, r),
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Event Tester", f"Failed to request test: {e}")

    def on_run_admin_test_command(self):
        combo = getattr(self, "event_test_combo", None)
        if combo is None:
            QtWidgets.QMessageBox.warning(self, "Event Tester", "Test selector not available.")
            return
        command_name = str(combo.currentData() or "").strip()
        label = str(combo.currentText() or command_name)
        if not command_name:
            QtWidgets.QMessageBox.warning(self, "Event Tester", "Please select a test command.")
            return
        self._run_event_test(command_name, label)

    def _on_event_test_result(self, label: str, r: dict):
        try:
            if r.get("ok"):
                details = r.get("details")
                msg = f"{label} test finished successfully."
                if details:
                    msg = f"{msg}\n\n{details}"
                QtWidgets.QMessageBox.information(self, "Event Tester", msg)
                try:
                    self._set_status(f"Event Tester: {label} done")
                except Exception:
                    pass
            else:
                QtWidgets.QMessageBox.warning(self, "Event Tester", f"{label} test failed: {r}")
                try:
                    self._set_status(f"Event Tester: {label} failed")
                except Exception:
                    pass
        except Exception:
            pass
