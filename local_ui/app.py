"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""



import sys
import os
import threading
import subprocess
import time
from datetime import datetime
# HTML embed removed; no html module required
from PySide6 import QtWidgets, QtCore, QtGui
from config_editor import ConfigEditor
from control_api_client import send_cmd
from exception_handler import install_exception_hook
from repo_paths import get_repo_root
from runtime import run_main_window
from startup_trace import write_startup_trace
from ui_tabs import build_configs_tab, build_dashboard_tab, build_logs_tab, build_welcome_and_rank_tabs
from controllers.admin_controller import AdminControllerMixin
from controllers.birthdays_controller import BirthdaysControllerMixin
from controllers.dashboard_controller import DashboardControllerMixin
from controllers.emoji_controller import EmojiControllerMixin
from controllers.leveling_controller import LevelingControllerMixin
from controllers.logs_controller import LogsControllerMixin
from controllers.preview_controller import PreviewControllerMixin


UI_RESTART_EXIT_CODE = 42

write_startup_trace()


install_exception_hook()


class MainWindow(LevelingControllerMixin, BirthdaysControllerMixin, LogsControllerMixin, DashboardControllerMixin, AdminControllerMixin, EmojiControllerMixin, PreviewControllerMixin, QtWidgets.QMainWindow):
    _async_done = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lizard UI")
        self.resize(1220, 780)
        self.setMinimumSize(1160, 740)
        # Repo root path for data/logs tracking
        self._repo_root = get_repo_root()

        # central tabs
        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)

        build_dashboard_tab(self, tabs)
        build_logs_tab(self, tabs)
        build_configs_tab(self, tabs, ConfigEditor)

        build_welcome_and_rank_tabs(self, tabs, QtCore)

        self.setCentralWidget(tabs)

        # styling
        self.setStyleSheet("""
        QWidget {
            font-family: Segoe UI, Arial, Helvetica, sans-serif;
            background: #121417;
            color: #E7EBF3;
        }
        QMainWindow {
            background: #121417;
        }
        QTabWidget::pane {
            border: 1px solid #2A3240;
            border-radius: 10px;
            background: #171C23;
            top: -1px;
        }
        QTabBar::tab {
            background: #1B212A;
            color: #C9D2E3;
            border: 1px solid #2A3240;
            padding: 8px 14px;
            margin-right: 6px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            min-width: 90px;
        }
        QTabBar::tab:selected {
            background: #283246;
            color: #FFFFFF;
            border-color: #4A76C9;
        }
        QTabBar::tab:hover {
            background: #222A35;
        }
        #statusLabel {
            font-weight: 700;
            font-size: 14px;
            color: #D8E5FF;
            padding: 8px 10px;
            background: #1B2230;
            border: 1px solid #334258;
            border-radius: 8px;
        }
        QPushButton {
            background: #222A35;
            color: #F0F4FF;
            border: 1px solid #334258;
            border-radius: 8px;
            padding: 7px 12px;
        }
        QPushButton:hover {
            background: #2A3544;
            border-color: #4A76C9;
        }
        QPushButton:pressed {
            background: #1A212B;
        }
        QPushButton:disabled {
            color: #7D8798;
            border-color: #3A4352;
            background: #1A1F27;
        }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {
            background: #0F141B;
            color: #EAF1FF;
            border: 1px solid #334258;
            border-radius: 7px;
            selection-background-color: #3B5D9A;
        }
        QLineEdit, QComboBox {
            min-height: 28px;
            padding: 4px 8px;
        }
        QPlainTextEdit, QTextEdit {
            padding: 8px;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 1px solid #5D8BE0;
            background: #101722;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QComboBox QAbstractItemView {
            background: #171D26;
            color: #EAF1FF;
            border: 1px solid #334258;
            selection-background-color: #314C7E;
        }
        QScrollBar:vertical {
            background: #151A22;
            width: 10px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #354257;
            border-radius: 5px;
            min-height: 24px;
        }
        QScrollBar::handle:vertical:hover {
            background: #496084;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QLabel {
            color: #DCE5F5;
        }
        QLabel#sectionLabel {
            color: #8FB6FF;
            font-weight: 700;
            padding-top: 8px;
            padding-bottom: 2px;
        }
        QStatusBar {
            background: #151B24;
            color: #C8D5EE;
            border-top: 1px solid #2A3240;
        }
        QGroupBox {
            border: 1px solid #2C3542;
            border-radius: 8px;
            margin-top: 8px;
            padding: 10px;
        }
        """)

        # timers
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.timeout.connect(self.on_refresh)
        self.status_timer.start(3000)

        self.log_timer = QtCore.QTimer(self)
        # keep a fallback timer but increase interval to reduce load
        self.log_timer.timeout.connect(self.tail_logs)
        self.log_timer.start(5000)

        # background poller for logs (db or tail); created when a log is chosen
        self._log_poller = None
        self._status_inflight = False

        # initialize
        self._log_fp = None
        self._active_log_path = None
        self._active_log_mode = "file"
        # sqlite support
        self._db_conn = None
        self._db_table = None
        self._db_last_rowid = 0
        self._tracked_fp = None
        # data URL for a banner received via the Refresh Preview button
        self._preview_banner_data_url = None
        # rank preview persisted settings
        self._rank_config = {}
        self._rank_config_path = None
        self._preview_dirty = False
        self._preview_syncing = False
        self._title_font_lookup = {}
        self._dash_console_path = os.path.join(self._repo_root, "data", "logs", "start_all_console.log")
        self._dash_console_pos = 0
        self._ui_settings = {}
        try:
            self._load_title_font_choices()
            self._load_user_font_choices()
            self._load_rank_name_font_choices()
            self._load_rank_info_font_choices()
        except Exception:
            pass
        self._open_log()
        self.on_refresh()
        # load rank config if present
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
            self._load_ui_settings()
        except Exception:
            pass
        # helper to update status label and force UI repaint
        def _set_status(msg: str):
            try:
                # update dashboard label
                try:
                    self.status_label.setText(msg)
                except Exception:
                    pass
                # also show in the main window status bar for stronger feedback
                try:
                    self.statusBar().showMessage(msg, 5000)
                except Exception:
                    pass
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
        # attach helper to instance for use in handlers
        self._set_status = _set_status
        try:
            self._async_done.connect(self._process_async_result)
        except Exception:
            pass
        # write a startup marker so the user can confirm the UI launched
        try:
            try:
                start_dir = os.path.join(self._repo_root, "data", "logs")
                os.makedirs(start_dir, exist_ok=True)
                with open(os.path.join(start_dir, "ui_start.log"), "a", encoding="utf-8") as fh:
                    fh.write(f"UI started at {datetime.now().isoformat()}\n")
            except Exception:
                pass
        except Exception:
            pass

        # heartbeat timer to show the UI is alive every 2s
        # NOTE: use the status bar only for the periodic "Alive" message so
        # it doesn't overwrite the dashboard `status_label` which is updated
        # by refresh/status actions.
        try:
            self._alive_timer = QtCore.QTimer(self)
            self._alive_timer.timeout.connect(lambda: self.statusBar().showMessage(f"Alive {datetime.now().strftime('%H:%M:%S')}", 2000))
            self._alive_timer.start(2000)
        except Exception:
            pass

        # dashboard live console poller (reads start_all supervisor output)
        try:
            self._dash_console_timer = QtCore.QTimer(self)
            self._dash_console_timer.timeout.connect(self._poll_dashboard_console)
            self._dash_console_timer.start(1000)
            self._poll_dashboard_console()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self._cleanup_runtime_resources()
        except Exception:
            pass
        return super().closeEvent(event)

    def _debug_log(self, message: str):
        try:
            if os.environ.get("UI_DEBUG") != "1":
                return
            log_dir = os.path.join(self._repo_root, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "ui_debug.log"), "a", encoding="utf-8", errors="ignore") as fh:
                fh.write(f"{datetime.now().isoformat()} {message}\n")
        except Exception:
            pass

    def _safe_stop_timer(self, name: str):
        try:
            timer = getattr(self, name, None)
            if timer:
                timer.stop()
        except Exception:
            pass

    def _safe_close_attr(self, name: str):
        try:
            obj = getattr(self, name, None)
            if obj:
                obj.close()
        except Exception:
            pass
        finally:
            try:
                setattr(self, name, None)
            except Exception:
                pass

    def _cleanup_runtime_resources(self):
        for timer_name in ("status_timer", "log_timer", "_alive_timer", "_dash_console_timer"):
            self._safe_stop_timer(timer_name)
        try:
            poller = getattr(self, "_log_poller", None)
            if poller:
                poller.stop()
        except Exception:
            pass
        finally:
            try:
                self._log_poller = None
            except Exception:
                pass
        self._safe_close_attr("_log_fp")
        self._safe_close_attr("_tracked_fp")
        self._safe_close_attr("_db_conn")

    def send_cmd_async(self, cmd: dict, timeout: float = 1.0, cb=None):
        def _worker():
            try:
                res = send_cmd(cmd, timeout=timeout)
            except Exception as e:
                res = {"ok": False, "error": str(e)}
            try:
                self._async_done.emit((cb, res))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _process_async_result(self, payload):
        try:
            cb, res = payload
            if cb:
                cb(res)
        except Exception:
            pass

    def on_refresh_preview(self):
        """Request a banner preview from the bot and update the preview widgets."""
        try:
            try:
                self._set_status("Preview: requesting...")
            except Exception:
                pass
            overrides = {
                "BANNER_PATH": self.pv_banner_path.text() or None,
                "BG_MODE": self.pv_bg_mode.currentData() or "cover",
                "BG_ZOOM": int(self.pv_bg_zoom.value()),
                "BG_OFFSET_X": int(self.pv_bg_x.value()),
                "BG_OFFSET_Y": int(self.pv_bg_y.value()),
                "BANNER_TITLE": self.pv_title.text() or "WELCOME",
                "FONT_WELCOME": self._selected_title_font_path(),
                "FONT_USERNAME": self._selected_user_font_path(),
                "TITLE_FONT_SIZE": int(self.pv_title_size.value()),
                "USERNAME_FONT_SIZE": int(self.pv_user_size.value()),
                "TITLE_COLOR": self.pv_title_color.text() or "#FFFFFF",
                "USERNAME_COLOR": self.pv_user_color.text() or "#E6E6E6",
                "TITLE_OFFSET_X": int(self.pv_title_x.value()),
                "TITLE_OFFSET_Y": int(self.pv_title_y.value()),
                "USERNAME_OFFSET_X": int(self.pv_user_x.value()),
                "USERNAME_OFFSET_Y": int(self.pv_user_y.value()),
                "TEXT_OFFSET_X": int(self.pv_text_x.value()),
                "TEXT_OFFSET_Y": int(self.pv_text_y.value()),
                "OFFSET_X": int(self.pv_avatar_x.value()),
                "OFFSET_Y": int(self.pv_avatar_y.value()),
            }
            self.send_cmd_async(
                {"action": "ping"},
                timeout=0.6,
                cb=lambda ping, overrides=overrides: self._on_preview_ping_result(ping, overrides),
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Preview error", str(e))

    def _on_preview_ping_result(self, ping: dict, overrides: dict):
        try:
            if not ping.get("ok"):
                QtWidgets.QMessageBox.warning(self, "Preview", f"Control API not available, using local banner ({ping.get('error')})")
                try:
                    self.update_preview()
                except Exception:
                    pass
                return
            self.send_cmd_async(
                {"action": "banner_preview", "overrides": overrides},
                timeout=5.0,
                cb=self._on_preview_banner_result,
            )
        except Exception:
            pass

    def _on_preview_banner_result(self, r: dict):
        try:
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        self.pv_banner.setPixmap(scaled)
                    except Exception:
                        self.pv_banner.setPixmap(pix)
                    self._preview_banner_data_url = f"data:image/png;base64,{b64}"
                    try:
                        self._apply_live_preview()
                    except Exception:
                        pass
                    return
            QtWidgets.QMessageBox.warning(self, "Preview", f"Failed to get banner from bot: {r}")
            try:
                self.update_preview()
            except Exception:
                pass
        except Exception:
            pass

    def on_refresh_rankpreview(self):
        """Request a rank image from the bot and display it in the Rank tab."""
        try:
            try:
                self._set_status("Rank Preview: requesting...")
            except Exception:
                pass
            # prefer explicit field; if empty, use persisted config
            bg = self.rk_bg_path.text() or self._rank_config.get("BG_PATH") if getattr(self, "_rank_config", None) is not None else None
            req = {"action": "rank_preview"}
            if bg:
                req["bg_path"] = bg
            req["bg_mode"] = self.rk_bg_mode.currentData() or "cover"
            req["bg_zoom"] = int(self.rk_bg_zoom.value())
            req["bg_offset_x"] = int(self.rk_bg_x.value())
            req["bg_offset_y"] = int(self.rk_bg_y.value())
            req["name_font"] = self._selected_rank_name_font_path()
            req["info_font"] = self._selected_rank_info_font_path()
            req["name_font_size"] = int(self.rk_name_size.value())
            req["info_font_size"] = int(self.rk_info_size.value())
            req["name_color"] = self.rk_name_color.text() or "#FFFFFF"
            req["info_color"] = self.rk_info_color.text() or "#C8C8C8"
            req["text_offset_x"] = int(self.rk_text_x.value())
            req["text_offset_y"] = int(self.rk_text_y.value())
            self.send_cmd_async(req, timeout=3.0, cb=self._on_rankpreview_result)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Rank Preview error", str(e))

    def _on_rankpreview_result(self, r: dict):
        try:
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                    except Exception:
                        self.rk_image.setPixmap(pix)
                    self._rank_preview_data_url = f"data:image/png;base64,{b64}"
                    return
            QtWidgets.QMessageBox.warning(self, "Rank Preview", f"Failed to get rank image from bot: {r}")
        except Exception:
            pass

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
            # Ensure the Python process exits so terminal command ends.
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
        """Shutdown the bot (via control API), restart the bot module, then relaunch the UI.

        This method will: 1) ask for confirmation, 2) request bot shutdown, 3) spawn a new bot process
        via `python -m src.mybot`, 4) spawn a new UI process running this script, and
        5) quit the current UI.
        """
        try:
            self._set_status("Restart: preparing...")
        except Exception as e:
            self._debug_log(f"restart status set failed: {e}")
        ok = QtWidgets.QMessageBox.question(self, "Restart", "Restart the bot and the UI? This will stop the bot and relaunch both.", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if ok != QtWidgets.QMessageBox.Yes:
            return

        # If started via start_all.py supervisor, delegate full restart to it so
        # bot + UI are relaunched cleanly in the same terminal session.
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

        # 1) request bot shutdown via control API (best-effort) and wait briefly
        try:
            send_cmd({"action": "shutdown"}, timeout=2.5)
        except Exception as e:
            self._debug_log(f"restart shutdown request failed: {e}")

        # wait until old API is down (or timeout), to reduce restart races
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

        # 2) start the bot module (current project entrypoint)
        try:
            env = os.environ.copy()
            env["LOCAL_UI_ENABLE"] = "1"
            env["PYTHONUNBUFFERED"] = "1"
            subprocess.Popen([sys.executable, "-u", "-m", "src.mybot"], cwd=self._repo_root, env=env)
            bot_started = True
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to start bot process: {e}")

        # 3) spawn a delayed UI relaunch helper so lock/port 8766 is released first
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

        # 4) quit current application
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

def main():
    sys.exit(run_main_window(MainWindow))


if __name__ == "__main__":
    main()
