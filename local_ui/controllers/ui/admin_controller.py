import os
import shutil
import zipfile
from datetime import datetime

from config.config_editor import ConfigEditor
from PySide6 import QtWidgets
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
                timeout=90.0,
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
        # testall requires a channel ID
        if command_name == "testall":
            channel_id = self._event_tester_channel_id_text()
            if not channel_id or not channel_id.isdigit():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Event Tester",
                    "Test All requires a Channel ID.\nPlease enter a valid Channel ID first.",
                )
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

    # ==================================================
    # CONFIG BACKUP / RESTORE
    # ==================================================

    def on_backup_configs(self):
        """Create a zip backup of the entire config/ directory and .env file."""
        try:
            repo_root = self._repo_root
            config_dir = os.path.join(repo_root, "config")
            env_path = os.path.join(repo_root, ".env")

            if not os.path.isdir(config_dir):
                QtWidgets.QMessageBox.warning(self, "Backup", "No config/ directory found.")
                return

            # Default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"config_backup_{timestamp}.zip"
            backup_dir = os.path.join(repo_root, "data")
            os.makedirs(backup_dir, exist_ok=True)

            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Config Backup",
                os.path.join(backup_dir, default_name),
                "ZIP files (*.zip)",
            )
            if not path:
                return

            file_count = 0
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add all config files
                for root, dirs, files in os.walk(config_dir):
                    for fn in files:
                        full = os.path.join(root, fn)
                        arcname = os.path.relpath(full, repo_root)
                        zf.write(full, arcname)
                        file_count += 1
                # Add .env if it exists
                if os.path.isfile(env_path):
                    zf.write(env_path, ".env")
                    file_count += 1

            QtWidgets.QMessageBox.information(
                self,
                "Backup",
                f"Backup saved: {path}\n{file_count} files archived.",
            )
            try:
                self._set_status(f"Backup saved: {file_count} files")
            except Exception:
                pass
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Backup", f"Backup failed: {e}")

    def on_restore_configs(self):
        """Restore configs from a zip backup."""
        try:
            repo_root = self._repo_root
            backup_dir = os.path.join(repo_root, "data")

            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Restore Config Backup",
                backup_dir,
                "ZIP files (*.zip)",
            )
            if not path:
                return

            # Validate zip
            if not zipfile.is_zipfile(path):
                QtWidgets.QMessageBox.warning(self, "Restore", "Selected file is not a valid ZIP.")
                return

            # List contents for confirmation
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                config_files = [n for n in names if n.startswith("config/") or n == ".env"]

            if not config_files:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Restore",
                    "No config files found in the backup.\n"
                    "Expected files under config/ or .env.",
                )
                return

            reply = QtWidgets.QMessageBox.question(
                self,
                "Restore Configs",
                f"This will overwrite {len(config_files)} config files:\n\n"
                + "\n".join(config_files[:20])
                + ("\n..." if len(config_files) > 20 else "")
                + "\n\nContinue?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            restored = 0
            with zipfile.ZipFile(path, "r") as zf:
                for name in config_files:
                    target = os.path.join(repo_root, name)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    restored += 1

            QtWidgets.QMessageBox.information(
                self,
                "Restore",
                f"Restored {restored} files from backup.\n"
                "Restart the bot or reload cogs for changes to take effect.",
            )
            try:
                self._set_status(f"Restore complete: {restored} files")
            except Exception:
                pass

            # Refresh UI config views
            try:
                if hasattr(self, "cfg_editor") and self.cfg_editor is not None:
                    self.cfg_editor.refresh_list()
            except Exception:
                pass
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
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Restore", f"Restore failed: {e}")
