import os
import subprocess
import sys
import time
from datetime import datetime

from PySide6 import QtWidgets, QtCore

from control_api_client import send_cmd


UI_RESTART_EXIT_CODE = 42


class LifecycleControllerMixin:
    def on_shutdown(self):
        ok = QtWidgets.QMessageBox.question(
            self,
            "Shutdown",
            "Bot herunterfahren und UI schließen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if ok != QtWidgets.QMessageBox.Yes:
            return
        self.send_cmd_async({"action": "shutdown"}, timeout=2.5, cb=self._on_shutdown_result)

    def _on_shutdown_result(self, r: dict):
        try:
            if r.get("ok"):
                QtWidgets.QMessageBox.information(self, "Shutdown", "Bot wird heruntergefahren. UI wird geschlossen.")
                try:
                    self._set_status("Shutdown: bot + UI")
                    self.statusBar().showMessage("Shutdown ausgelöst...", 2000)
                except Exception:
                    pass
            else:
                QtWidgets.QMessageBox.warning(self, "Shutdown", f"Bot-Shutdown fehlgeschlagen: {r}\nUI wird trotzdem beendet.")
                try:
                    self._set_status("Shutdown: UI only")
                    self.statusBar().showMessage("Bot konnte nicht bestätigt werden, UI beendet...", 2500)
                except Exception:
                    pass
        finally:
            try:
                QtWidgets.QApplication.quit()
            except Exception:
                pass
            try:
                QtCore.QTimer.singleShot(350, lambda: os._exit(0))
            except Exception:
                try:
                    os._exit(0)
                except Exception:
                    pass

    def on_restart_and_restart_ui(self):
        try:
            self._set_status("Restart: preparing...")
        except Exception as e:
            self._debug_log(f"restart status set failed: {e}")
        ok = QtWidgets.QMessageBox.question(self, "Restart", "Restart the bot and the UI? This will stop the bot and relaunch both.", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if ok != QtWidgets.QMessageBox.Yes:
            return

        if os.environ.get("LOCAL_UI_SUPERVISED") == "1":
            try:
                self._set_status("Restart: requesting supervised restart...")
                self.statusBar().showMessage("Restart wird an Supervisor übergeben...", 2500)
            except Exception as e:
                self._debug_log(f"supervised restart status failed: {e}")
            try:
                marker_dir = os.path.join(self._repo_root, "data", "logs")
                os.makedirs(marker_dir, exist_ok=True)
                marker_path = os.path.join(marker_dir, "ui_restart.request")
                with open(marker_path, "w", encoding="utf-8") as fh:
                    fh.write(datetime.now().isoformat())
            except Exception as e:
                self._debug_log(f"restart marker write failed: {e}")
            try:
                send_cmd({"action": "shutdown"}, timeout=2.5)
            except Exception as e:
                self._debug_log(f"supervised restart shutdown request failed: {e}")
            try:
                QtWidgets.QApplication.exit(UI_RESTART_EXIT_CODE)
            except Exception:
                try:
                    os._exit(UI_RESTART_EXIT_CODE)
                except Exception as e:
                    self._debug_log(f"forced supervised exit failed: {e}")
            return

        try:
            send_cmd({"action": "shutdown"}, timeout=2.5)
        except Exception as e:
            self._debug_log(f"restart shutdown request failed: {e}")

        try:
            deadline = time.time() + 4.0
            while time.time() < deadline:
                p = send_cmd({"action": "ping"}, timeout=0.6)
                if not p.get("ok"):
                    break
                time.sleep(0.25)
        except Exception as e:
            self._debug_log(f"restart ping wait failed: {e}")

        bot_started = False
        ui_started = False

        try:
            env = os.environ.copy()
            env["LOCAL_UI_ENABLE"] = "1"
            env["PYTHONUNBUFFERED"] = "1"
            subprocess.Popen([sys.executable, "-u", "-m", "src.mybot"], cwd=self._repo_root, env=env)
            bot_started = True
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to start bot process: {e}")

        try:
            app_path = os.path.abspath(__file__)
            repo_root = self._repo_root
            launcher_code = (
                "import os,sys,time,subprocess;"
                "time.sleep(1.1);"
                "env=os.environ.copy();"
                "env['PYTHONUNBUFFERED']='1';"
                f"subprocess.Popen([sys.executable,'-u',r'{app_path}'], cwd=r'{repo_root}', env=env)"
            )
            subprocess.Popen([sys.executable, "-c", launcher_code], cwd=self._repo_root)
            ui_started = True
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to relaunch UI: {e}")

        if ui_started:
            try:
                if bot_started:
                    self._set_status("Restart: bot + UI started")
                    self.statusBar().showMessage("Restart ausgelöst: Bot und UI werden neu gestartet...", 3000)
                else:
                    self._set_status("Restart: UI started, bot start failed")
                    self.statusBar().showMessage("UI neu gestartet, Bot-Start fehlgeschlagen (siehe Meldung).", 4000)
            except Exception:
                pass
            try:
                QtCore.QTimer.singleShot(350, QtWidgets.QApplication.quit)
            except Exception:
                try:
                    QtWidgets.QApplication.quit()
                except Exception:
                    try:
                        sys.exit(0)
                    except Exception:
                        pass
        else:
            try:
                self._set_status("Restart: failed (UI relaunch)")
                self.statusBar().showMessage("Restart abgebrochen: Neue UI konnte nicht gestartet werden.", 5000)
            except Exception:
                pass
