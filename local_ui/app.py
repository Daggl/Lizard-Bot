"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""



import sys
import os
import json
import threading
import sqlite3
import subprocess
import time
from datetime import datetime
# HTML embed removed; no html module required
from PySide6 import QtWidgets, QtCore, QtGui
from config_editor import ConfigEditor
from config_io import config_json_path, load_json_dict, save_json_merged
from control_api_client import send_cmd
from exception_handler import install_exception_hook
from file_ops import open_tracked_writer, prune_backups, rotate_log_file
from guides import open_bot_tutorial, open_commands_guide
from log_format import format_db_row
from log_poller import LogPoller
from repo_paths import get_repo_root
from runtime import run_main_window
from setup_wizard import SetupWizardDialog
from startup_trace import write_startup_trace
from ui_tabs import build_configs_tab, build_dashboard_tab, build_logs_tab, build_welcome_and_rank_tabs


UI_RESTART_EXIT_CODE = 42


write_startup_trace()


install_exception_hook()


class MainWindow(QtWidgets.QMainWindow):
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

    def _format_uptime(self, seconds: int) -> str:
        try:
            s = int(max(0, seconds or 0))
            days, rem = divmod(s, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, secs = divmod(rem, 60)
            if days > 0:
                return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except Exception:
            return "—"

    def _set_monitor_offline(self):
        try:
            self.mon_ready.setText("No")
            self.mon_user.setText("—")
            self.mon_ping.setText("—")
            self.mon_uptime.setText("—")
            self.mon_cpu.setText("—")
            self.mon_mem.setText("—")
            self.mon_cogs.setText("—")
        except Exception:
            pass

    def on_ping(self):
        self.send_cmd_async({"action": "ping"}, timeout=0.8, cb=self._on_ping_result)

    def _on_ping_result(self, r: dict):
        QtWidgets.QMessageBox.information(self, "Ping", str(r))

    def on_refresh(self):
        if self._status_inflight:
            return
        self._status_inflight = True
        self.send_cmd_async({"action": "status"}, timeout=1.0, cb=self._on_refresh_result)

    def _on_refresh_result(self, r: dict):
        try:
            if r and r.get("ok"):
                user = r.get("user") or "(no user)"
                ready = bool(r.get("ready"))
                cogs = r.get("cogs", [])
                ping_ms = r.get("gateway_ping_ms")
                uptime_seconds = r.get("uptime_seconds")
                cpu_percent = r.get("cpu_percent")
                system_cpu_percent = r.get("system_cpu_percent")
                mem_mb = r.get("memory_rss_mb")

                self.status_label.setText(f"User: {user} — Ready: {ready} — Cogs: {len(cogs)}")
                try:
                    self.mon_ready.setText("Yes" if ready else "No")
                    self.mon_user.setText(str(user))
                    self.mon_ping.setText(f"{int(ping_ms)} ms" if isinstance(ping_ms, (int, float)) else "—")
                    self.mon_uptime.setText(self._format_uptime(int(uptime_seconds or 0)))
                    if isinstance(cpu_percent, (int, float)) or isinstance(system_cpu_percent, (int, float)):
                        bot_cpu = float(cpu_percent) if isinstance(cpu_percent, (int, float)) else None
                        sys_cpu = float(system_cpu_percent) if isinstance(system_cpu_percent, (int, float)) else None
                        if bot_cpu is not None and bot_cpu > 0:
                            if bot_cpu < 0.01:
                                self.mon_cpu.setText("<0.01%")
                            else:
                                self.mon_cpu.setText(f"{bot_cpu:.2f}%")
                        elif sys_cpu is not None:
                            if sys_cpu > 0 and sys_cpu < 0.01:
                                self.mon_cpu.setText("<0.01% (sys)")
                            else:
                                self.mon_cpu.setText(f"{sys_cpu:.2f}% (sys)")
                        else:
                            self.mon_cpu.setText("—")
                    else:
                        self.mon_cpu.setText("—")
                    self.mon_mem.setText(f"{float(mem_mb):.1f} MB" if isinstance(mem_mb, (int, float)) else "—")
                    self.mon_cogs.setText(str(len(cogs)))
                except Exception:
                    pass
                try:
                    self.update_preview()
                except Exception:
                    pass
            else:
                self.status_label.setText(f"Status: offline ({(r or {}).get('error')})")
                self._set_monitor_offline()
        finally:
            self._status_inflight = False

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

    def on_reload(self):
        self.send_cmd_async({"action": "reload"}, timeout=3.0, cb=self._on_reload_result)

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
                os.environ["UI_DEBUG"] = "1"
            else:
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
        # switch to Configs tab (if available) or open modal
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

    def _stop_log_poller(self):
        try:
            if getattr(self, "_log_poller", None):
                try:
                    self._log_poller.stop()
                except Exception:
                    pass
                self._log_poller = None
        except Exception:
            pass

    def _start_log_poller(self, path: str, mode: str = "file", table: str = None):
        try:
            self._stop_log_poller()
            if not path:
                return
            if mode == "db":
                poller = LogPoller(
                    path,
                    mode="db",
                    table=table,
                    last_rowid=self._db_last_rowid,
                    interval=2.0,
                )
            else:
                poller = LogPoller(path, mode="file", interval=1.0)
            poller.new_line.connect(self._on_new_log_line)
            poller.start()
            self._log_poller = poller
        except Exception as e:
            self._debug_log(f"start_log_poller failed: {e}")

    def _on_new_log_line(self, line: str):
        try:
            try:
                self.log_text.appendPlainText(line)
            except Exception as e:
                self._debug_log(f"append log line failed: {e}")
            try:
                if getattr(self, "_tracked_fp", None):
                    self._tracked_fp.write(line + "\n")
                    self._tracked_fp.flush()
            except Exception as e:
                self._debug_log(f"tracked log write failed: {e}")
            try:
                self.log_text.verticalScrollBar().setValue(
                    self.log_text.verticalScrollBar().maximum()
                )
            except Exception as e:
                self._debug_log(f"log autoscroll failed: {e}")
        except Exception as e:
            self._debug_log(f"on_new_log_line failed: {e}")

    # ==================================================
    # Log tailing & preview helpers
    # ==================================================

    def _open_log(self):
        # Try to open a log file. Search common locations and pick the most
        # recently modified .log file if multiple candidates exist.
        try:
            try:
                self._set_status("Logs: choosing file...")
            except Exception:
                pass
            repo_root = self._repo_root
            candidates = []
            # common locations
            candidates.append(os.path.join(repo_root, "discord.log"))
            candidates.append(os.path.join(repo_root, "logs"))
            candidates.append(os.path.join(repo_root, "log"))
            candidates.append(os.path.join(repo_root, "data", "logs"))

            log_files = []
            for p in candidates:
                if os.path.isdir(p):
                    for fn in os.listdir(p):
                        if fn.lower().endswith(('.log', '.txt')):
                            full = os.path.join(p, fn)
                            try:
                                mtime = os.path.getmtime(full)
                                log_files.append((mtime, full))
                            except Exception:
                                pass
                else:
                    if os.path.exists(p) and os.path.isfile(p):
                        try:
                            mtime = os.path.getmtime(p)
                            log_files.append((mtime, p))
                        except Exception:
                            pass

            # choose the most recent log file
            if log_files:
                log_files.sort(reverse=True)
                _, log_path = log_files[0]
                try:
                    self._log_fp = open(log_path, "r", encoding="utf-8", errors="ignore")
                    self._log_fp.seek(0, os.SEEK_END)
                    # clear any previous message and show which file is tailed
                    try:
                        self.log_text.clear()
                        self.log_text.appendPlainText(f"Tailing: {log_path}")
                        # ensure tracked logs dir exists and open tracked writer
                        try:
                            self._open_tracked_writer(
                                f"\n--- Tailing: {log_path} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                            )
                        except Exception:
                            pass
                    except Exception:
                        pass
                    try:
                        self._start_log_poller(log_path, mode="file")
                    except Exception:
                        pass
                    return
                except Exception:
                    self._log_fp = None

            # no log file found
            self._log_fp = None
            try:
                self.log_text.clear()
                self.log_text.appendPlainText("No log file found in common locations.\nStart the bot or place a log file named 'discord.log' in the repo root or a 'logs' folder.")
            except Exception:
                pass
        except Exception:
            self._log_fp = None

    def _choose_log_file(self):
        try:
            try:
                self._set_status("Logs: choosing file...")
            except Exception:
                pass
            repo_root = self._repo_root
            start_dir = repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose log file", start_dir, "Log files (*.log *.txt);;All files (*)")
            if path:
                try:
                    self._stop_log_poller()
                    self._safe_close_attr("_db_conn")
                    self._db_table = None
                    self._db_last_rowid = 0
                    self._safe_close_attr("_log_fp")

                    # handle sqlite DB files
                    if path.lower().endswith(('.db', '.sqlite')):
                        try:
                            # open sqlite connection
                            conn = sqlite3.connect(path)
                            conn.row_factory = sqlite3.Row
                            self._db_conn = conn
                            # find user tables
                            cur = conn.cursor()
                            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                            tables = [r[0] for r in cur.fetchall()]
                            if not tables:
                                QtWidgets.QMessageBox.warning(self, "Open DB", "Keine Tabellen in der Datenbank gefunden.")
                                return
                            # if multiple tables, ask user to pick
                            table = tables[0]
                            if len(tables) > 1:
                                table, ok = QtWidgets.QInputDialog.getItem(self, "Wähle Tabelle", "Tabelle:", tables, 0, False)
                                if not ok:
                                    return
                            self._db_table = table
                            # get last rowid
                            try:
                                cur.execute(f"SELECT max(rowid) as m FROM '{table}';")
                                r = cur.fetchone()
                                self._db_last_rowid = int(r['m']) if r and r['m'] is not None else 0
                            except Exception:
                                self._db_last_rowid = 0
                            # initial load: show last 200 rows
                            try:
                                cur.execute(f"SELECT rowid, * FROM '{table}' ORDER BY rowid DESC LIMIT 200;")
                                rows = cur.fetchall()
                                self.log_text.clear()
                                self.log_text.appendPlainText(f"Tailing DB: {path} table: {table}")
                                for row in reversed(rows):
                                    # format row using smart formatter
                                    try:
                                        line = self._format_db_row(row)
                                        self.log_text.appendPlainText(line)
                                    except Exception:
                                        try:
                                            values = dict(row)
                                            self.log_text.appendPlainText(str(values))
                                        except Exception:
                                            self.log_text.appendPlainText(str(tuple(row)))
                            except Exception as e:
                                QtWidgets.QMessageBox.warning(self, "Open DB", f"Fehler beim Lesen der Tabelle: {e}")
                            # open tracked writer
                            try:
                                self._open_tracked_writer(
                                    f"\n--- Tailing DB: {path} table: {table} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                                )
                            except Exception:
                                pass
                            try:
                                self._start_log_poller(path, mode="db", table=table)
                            except Exception:
                                pass
                            return
                        except Exception as e:
                            QtWidgets.QMessageBox.warning(self, "Open DB", f"Fehler beim Öffnen der Datenbank: {e}")
                            return

                    # otherwise open as plain text file
                    self._log_fp = open(path, "r", encoding="utf-8", errors="ignore")
                    self._log_fp.seek(0, os.SEEK_END)
                    self.log_text.clear()
                    self.log_text.appendPlainText(f"Tailing: {path}")
                    # ensure tracked logs dir exists and open tracked writer
                    try:
                        self._open_tracked_writer(
                            f"\n--- Tailing: {path} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                        )
                    except Exception:
                        pass
                    try:
                        self._start_log_poller(path, mode="file")
                    except Exception:
                        pass
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Open log", f"Failed to open log file: {e}")
        except Exception:
            pass

    def _choose_banner(self):
        try:
            try:
                self._set_status("Banner: choosing image...")
            except Exception:
                pass
            repo_root = self._repo_root
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose banner image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.pv_banner_path.setText(path)
                pix = QtGui.QPixmap(path)
                try:
                    scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    self.pv_banner.setPixmap(scaled)
                except Exception:
                    self.pv_banner.setPixmap(pix)
        except Exception:
            pass

    def _format_db_row(self, row: sqlite3.Row) -> str:
        return format_db_row(row)

    def _choose_rank_bg(self):
        try:
            try:
                self._set_status("Rank: choosing background...")
            except Exception:
                pass
            repo_root = self._repo_root
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose rank background image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.rk_bg_path.setText(path)
                # optional: show it scaled in the rank image preview area
                try:
                    pix = QtGui.QPixmap(path)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
                # persist selection immediately
                try:
                    self._save_rank_config({"BG_PATH": path})
                except Exception:
                    pass
        except Exception:
            pass

    def _rank_config_paths(self):
        return config_json_path(self._repo_root, "rank.json")

    def _leveling_config_paths(self):
        return config_json_path(self._repo_root, "leveling.json")

    def _ui_settings_path(self):
        return config_json_path(self._repo_root, "local_ui.json")

    def _load_ui_settings(self):
        path = self._ui_settings_path()
        cfg = load_json_dict(path)
        self._ui_settings = cfg if isinstance(cfg, dict) else {}
        channel_id = str(self._ui_settings.get("event_test_channel_id", "") or "").strip()
        try:
            if hasattr(self, "event_test_channel_id"):
                self.event_test_channel_id.setText(channel_id)
        except Exception:
            pass
        try:
            read_only = bool(self._ui_settings.get("safe_read_only", False))
            debug_on = bool(self._ui_settings.get("safe_debug_logging", False))
            auto_reload_off = bool(self._ui_settings.get("safe_auto_reload_off", False))
            for attr, value in (
                ("safe_read_only_chk", read_only),
                ("safe_debug_logging_chk", debug_on),
                ("safe_auto_reload_off_chk", auto_reload_off),
            ):
                chk = getattr(self, attr, None)
                if chk is None:
                    continue
                try:
                    chk.blockSignals(True)
                    chk.setChecked(value)
                finally:
                    chk.blockSignals(False)
            self._apply_safe_debug_logging()
        except Exception:
            pass

    def _save_ui_settings(self, data: dict):
        path = self._ui_settings_path()
        merged = save_json_merged(path, data or {})
        self._ui_settings = merged if isinstance(merged, dict) else dict(data or {})

    def _load_leveling_config(self):
        cfg_path = self._leveling_config_paths()
        cfg = load_json_dict(cfg_path)

        default_rewards = {
            "5": "Bronze",
            "10": "Silber",
            "20": "Gold",
            "30": "Diamond",
            "40": "Platinum",
            "50": "Master",
            "60": "Grandmaster",
            "70": "Karl-Heinz",
        }
        default_achievements = {
            "Chatter I": {"messages": 100},
            "Chatter II": {"messages": 500},
            "Chatter III": {"messages": 1000},
            "Chatter IV": {"messages": 5000},
            "Voice Starter": {"voice_time": 3600},
            "Voice Pro": {"voice_time": 18000},
            "Voice Master": {"voice_time": 36000},
            "Level 5": {"level": 5},
            "Level 10": {"level": 10},
            "Level 25": {"level": 25},
            "Level 50": {"level": 50},
        }

        levelup_tpl = str(
            cfg.get(
                "LEVEL_UP_MESSAGE_TEMPLATE",
                "{member_mention}\nyou just reached level {level}!\nkeep it up, cutie!",
            )
        )
        achievement_tpl = str(
            cfg.get(
                "ACHIEVEMENT_MESSAGE_TEMPLATE",
                "🏆 {member_mention} got Achievement **{achievement_name}**",
            )
        )
        win_emoji = str(cfg.get("EMOJI_WIN", "") or "")
        heart_emoji = str(cfg.get("EMOJI_HEART", "") or "")
        xp_per_message = int(cfg.get("XP_PER_MESSAGE", 15) or 15)
        voice_xp_per_minute = int(cfg.get("VOICE_XP_PER_MINUTE", 10) or 10)
        message_cooldown = int(cfg.get("MESSAGE_COOLDOWN", 30) or 30)
        achievement_channel_id = str(cfg.get("ACHIEVEMENT_CHANNEL_ID", "") or "")
        rewards_cfg = cfg.get("LEVEL_REWARDS")
        achievements_cfg = cfg.get("ACHIEVEMENTS")
        if not isinstance(rewards_cfg, dict):
            rewards_cfg = default_rewards
        if not isinstance(achievements_cfg, dict):
            achievements_cfg = default_achievements

        try:
            if not self.lv_levelup_msg.hasFocus():
                self.lv_levelup_msg.setPlainText(levelup_tpl)
            if not self.lv_achievement_msg.hasFocus():
                self.lv_achievement_msg.setPlainText(achievement_tpl)
            if not self.lv_emoji_win.hasFocus():
                self.lv_emoji_win.setText(win_emoji)
            if not self.lv_emoji_heart.hasFocus():
                self.lv_emoji_heart.setText(heart_emoji)
            self.lv_xp_per_message.setValue(max(1, xp_per_message))
            self.lv_voice_xp_per_minute.setValue(max(1, voice_xp_per_minute))
            self.lv_message_cooldown.setValue(max(0, message_cooldown))
            if not self.lv_achievement_channel_id.hasFocus():
                self.lv_achievement_channel_id.setText(achievement_channel_id)
            self._populate_level_rewards_table(rewards_cfg)
            self._populate_achievements_table(achievements_cfg)
        except Exception:
            pass

    def _save_leveling_config(self, data: dict):
        cfg_path = self._leveling_config_paths()
        save_json_merged(cfg_path, data or {})

    def _populate_level_rewards_table(self, rewards_cfg: dict):
        table = getattr(self, "lv_rewards_table", None)
        if table is None:
            return
        try:
            rows = []
            if isinstance(rewards_cfg, dict):
                for level_raw, role_name in rewards_cfg.items():
                    try:
                        level = int(level_raw)
                    except Exception:
                        continue
                    role = str(role_name or "").strip()
                    if level > 0 and role:
                        rows.append((level, role))
            rows.sort(key=lambda it: it[0])
            table.setRowCount(0)
            for level, role in rows:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(level)))
                table.setItem(row, 1, QtWidgets.QTableWidgetItem(role))
        except Exception:
            pass

    def _populate_achievements_table(self, achievements_cfg: dict):
        table = getattr(self, "lv_achievements_table", None)
        if table is None:
            return
        try:
            rows = []
            if isinstance(achievements_cfg, dict):
                for achievement_name, req in achievements_cfg.items():
                    name = str(achievement_name or "").strip()
                    if not name or not isinstance(req, dict):
                        continue
                    for req_type, req_value in req.items():
                        req_type_s = str(req_type or "").strip()
                        try:
                            req_int = int(req_value)
                        except Exception:
                            continue
                        if req_type_s and req_int > 0:
                            rows.append((name, req_type_s, req_int))
            rows.sort(key=lambda it: (it[0].lower(), it[1].lower()))
            table.setRowCount(0)
            for ach_name, req_type, req_val in rows:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QtWidgets.QTableWidgetItem(ach_name))
                table.setItem(row, 1, QtWidgets.QTableWidgetItem(req_type))
                table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(req_val)))
        except Exception:
            pass

    def _collect_level_rewards_from_table(self) -> dict:
        table = getattr(self, "lv_rewards_table", None)
        if table is None:
            return {}
        out = {}
        for row in range(table.rowCount()):
            level_item = table.item(row, 0)
            role_item = table.item(row, 1)
            level_raw = str(level_item.text() if level_item else "").strip()
            role_name = str(role_item.text() if role_item else "").strip()
            if not level_raw and not role_name:
                continue
            try:
                level_int = int(level_raw)
            except Exception as exc:
                raise ValueError(f"Rewards row {row + 1}: invalid level ({exc})") from exc
            if level_int <= 0:
                raise ValueError(f"Rewards row {row + 1}: level must be > 0")
            if not role_name:
                raise ValueError(f"Rewards row {row + 1}: role name is empty")
            out[str(level_int)] = role_name
        return out

    def _collect_achievements_from_table(self) -> dict:
        table = getattr(self, "lv_achievements_table", None)
        if table is None:
            return {}
        allowed_types = {"messages", "voice_time", "level", "xp"}
        out = {}
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            type_item = table.item(row, 1)
            value_item = table.item(row, 2)
            ach_name = str(name_item.text() if name_item else "").strip()
            req_type = str(type_item.text() if type_item else "").strip()
            req_value_raw = str(value_item.text() if value_item else "").strip()
            if not ach_name and not req_type and not req_value_raw:
                continue
            if not ach_name:
                raise ValueError(f"Achievements row {row + 1}: achievement name is empty")
            if req_type not in allowed_types:
                raise ValueError(f"Achievements row {row + 1}: type must be one of {sorted(allowed_types)}")
            try:
                req_value = int(req_value_raw)
            except Exception as exc:
                raise ValueError(f"Achievements row {row + 1}: invalid value ({exc})") from exc
            if req_value <= 0:
                raise ValueError(f"Achievements row {row + 1}: value must be > 0")
            out.setdefault(ach_name, {})[req_type] = req_value
        return out

    def on_leveling_add_reward_row(self):
        table = getattr(self, "lv_rewards_table", None)
        if table is None:
            return
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QtWidgets.QTableWidgetItem("1"))
        table.setItem(row, 1, QtWidgets.QTableWidgetItem("Role Name"))
        table.setCurrentCell(row, 0)

    def on_leveling_remove_reward_row(self):
        table = getattr(self, "lv_rewards_table", None)
        if table is None:
            return
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def on_leveling_add_achievement_row(self):
        table = getattr(self, "lv_achievements_table", None)
        if table is None:
            return
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QtWidgets.QTableWidgetItem("Achievement Name"))
        table.setItem(row, 1, QtWidgets.QTableWidgetItem("messages"))
        table.setItem(row, 2, QtWidgets.QTableWidgetItem("100"))
        table.setCurrentCell(row, 0)

    def on_leveling_remove_achievement_row(self):
        table = getattr(self, "lv_achievements_table", None)
        if table is None:
            return
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def _load_rank_config(self):
        cfg_path = self._rank_config_paths()
        self._rank_config_path = cfg_path
        cfg = load_json_dict(cfg_path)
        self._rank_config = cfg
        # populate UI fields if empty
        try:
            bg = cfg.get("BG_PATH")
            if bg and (not self.rk_bg_path.text()):
                self.rk_bg_path.setText(str(bg))
                try:
                    pix = QtGui.QPixmap(bg)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
            mode_val = str(cfg.get("BG_MODE", "cover") or "cover")
            idx = self.rk_bg_mode.findData(mode_val)
            self.rk_bg_mode.setCurrentIndex(idx if idx >= 0 else 0)
            self.rk_bg_zoom.setValue(int(cfg.get("BG_ZOOM", 100) or 100))
            self.rk_bg_x.setValue(int(cfg.get("BG_OFFSET_X", 0) or 0))
            self.rk_bg_y.setValue(int(cfg.get("BG_OFFSET_Y", 0) or 0))
            self._load_rank_name_font_choices(str(cfg.get("NAME_FONT", "assets/fonts/Poppins-Bold.ttf")))
            self._load_rank_info_font_choices(str(cfg.get("INFO_FONT", "assets/fonts/Poppins-Regular.ttf")))
            self.rk_name_size.setValue(int(cfg.get("NAME_FONT_SIZE", 60) or 60))
            self.rk_info_size.setValue(int(cfg.get("INFO_FONT_SIZE", 40) or 40))
            self.rk_name_color.setText(str(cfg.get("NAME_COLOR", "#FFFFFF") or "#FFFFFF"))
            self.rk_info_color.setText(str(cfg.get("INFO_COLOR", "#C8C8C8") or "#C8C8C8"))
            self.rk_text_x.setValue(int(cfg.get("TEXT_OFFSET_X", 0) or 0))
            self.rk_text_y.setValue(int(cfg.get("TEXT_OFFSET_Y", 0) or 0))
            # populate example name if present and user not editing
            name = cfg.get("EXAMPLE_NAME")
            if name and (not self.rk_name.text()):
                try:
                    self.rk_name.setText(str(name))
                except Exception:
                    pass
        except Exception:
            pass

    def _save_rank_config(self, data: dict):
        cfg_path = self._rank_config_paths()
        self._rank_config = save_json_merged(cfg_path, data or {})

    def _save_rank_preview(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")
            data = {}
            name = self.rk_name.text() or None
            bg = self.rk_bg_path.text() or None
            if name:
                data["EXAMPLE_NAME"] = name
            if bg:
                data["BG_PATH"] = bg
            data["BG_MODE"] = self.rk_bg_mode.currentData() or "cover"
            data["BG_ZOOM"] = int(self.rk_bg_zoom.value())
            data["BG_OFFSET_X"] = int(self.rk_bg_x.value())
            data["BG_OFFSET_Y"] = int(self.rk_bg_y.value())
            data["NAME_FONT"] = self._selected_rank_name_font_path() or "assets/fonts/Poppins-Bold.ttf"
            data["INFO_FONT"] = self._selected_rank_info_font_path() or "assets/fonts/Poppins-Regular.ttf"
            data["NAME_FONT_SIZE"] = int(self.rk_name_size.value())
            data["INFO_FONT_SIZE"] = int(self.rk_info_size.value())
            data["NAME_COLOR"] = (self.rk_name_color.text() or "#FFFFFF").strip()
            data["INFO_COLOR"] = (self.rk_info_color.text() or "#C8C8C8").strip()
            data["TEXT_OFFSET_X"] = int(self.rk_text_x.value())
            data["TEXT_OFFSET_Y"] = int(self.rk_text_y.value())
            if data:
                self._save_rank_config(data)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_rank,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Rankcard settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save rankcard settings: {e}")

    def _save_leveling_settings(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")

            ach_channel_raw = str(self.lv_achievement_channel_id.text() or "").strip()
            if ach_channel_raw and not ach_channel_raw.isdigit():
                QtWidgets.QMessageBox.warning(self, "Leveling", "Achievement Channel ID must contain only digits.")
                return

            try:
                rewards_obj = self._collect_level_rewards_from_table()
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Leveling", f"Invalid rewards rows: {exc}")
                return

            try:
                achievements_obj = self._collect_achievements_from_table()
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Leveling", f"Invalid achievement rows: {exc}")
                return

            lvl_data = {
                "XP_PER_MESSAGE": int(self.lv_xp_per_message.value()),
                "VOICE_XP_PER_MINUTE": int(self.lv_voice_xp_per_minute.value()),
                "MESSAGE_COOLDOWN": int(self.lv_message_cooldown.value()),
                "LEVEL_UP_MESSAGE_TEMPLATE": self.lv_levelup_msg.toPlainText().strip() or "{member_mention}\\nyou just reached level {level}!\\nkeep it up, cutie!",
                "ACHIEVEMENT_MESSAGE_TEMPLATE": self.lv_achievement_msg.toPlainText().strip() or "🏆 {member_mention} got Achievement **{achievement_name}**",
                "EMOJI_WIN": (self.lv_emoji_win.text() or "").strip(),
                "EMOJI_HEART": (self.lv_emoji_heart.text() or "").strip(),
                "LEVEL_REWARDS": rewards_obj,
                "ACHIEVEMENTS": achievements_obj,
            }
            if ach_channel_raw:
                lvl_data["ACHIEVEMENT_CHANNEL_ID"] = int(ach_channel_raw)

            self._save_leveling_config(lvl_data)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_rank,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Leveling settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save leveling settings: {e}")

    def _insert_placeholder(self, text: str):
        self._insert_placeholder_into(self.pv_message, text)

    def _insert_placeholder_into(self, target: QtWidgets.QPlainTextEdit, text: str):
        try:
            cur = target.textCursor()
            cur.insertText(text)
            target.setTextCursor(cur)
            # trigger live preview
            try:
                self._preview_debounce.start()
            except Exception:
                pass
        except Exception:
            pass

    def _pick_color(self, target: QtWidgets.QLineEdit, title: str = "Choose color"):
        try:
            initial = QtGui.QColor((target.text() or "").strip())
            if not initial.isValid():
                initial = QtGui.QColor("#FFFFFF")
            chosen = QtWidgets.QColorDialog.getColor(initial, self, title)
            if chosen.isValid():
                target.setText(chosen.name().upper())
                try:
                    self._preview_debounce.start()
                except Exception:
                    pass
                try:
                    self._mark_preview_dirty()
                except Exception:
                    pass
        except Exception:
            pass

    def _mark_preview_dirty(self, *_args):
        try:
            if getattr(self, "_preview_syncing", False):
                return
            self._preview_dirty = True
        except Exception:
            pass

    def _selected_title_font_path(self) -> str:
        return self._resolve_font_combo_path(self.pv_title_font)

    def _selected_user_font_path(self) -> str:
        return self._resolve_font_combo_path(self.pv_user_font)

    def _selected_rank_name_font_path(self) -> str:
        return self._resolve_font_combo_path(self.rk_name_font)

    def _selected_rank_info_font_path(self) -> str:
        return self._resolve_font_combo_path(self.rk_info_font)

    def _resolve_font_combo_path(self, combo: QtWidgets.QComboBox) -> str:
        try:
            txt = (combo.currentText() or "").strip()
            txt_l = txt.lower()
            looks_like_path = (
                "/" in txt
                or "\\" in txt
                or txt_l.endswith(".ttf")
                or txt_l.endswith(".otf")
                or txt_l.endswith(".ttc")
            )
            if txt and looks_like_path:
                return txt
        except Exception:
            pass
        try:
            data = combo.currentData()
            if isinstance(data, str) and data.strip():
                return data.strip()
        except Exception:
            pass
        try:
            return (combo.currentText() or "").strip()
        except Exception:
            return ""

    def _load_font_choices(self, combo: QtWidgets.QComboBox, selected_path: str = None):
        try:
            repo_root = self._repo_root
            assets_fonts = os.path.join(repo_root, "assets", "fonts")
            sys_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
            exts = (".ttf", ".otf", ".ttc")

            font_paths = []
            for base_dir, source in ((assets_fonts, "assets"), (sys_fonts, "system")):
                if not os.path.isdir(base_dir):
                    continue
                try:
                    for name in os.listdir(base_dir):
                        if not name.lower().endswith(exts):
                            continue
                        full = os.path.join(base_dir, name)
                        if os.path.isfile(full):
                            font_paths.append((full, source))
                except Exception:
                    pass

            # de-duplicate by absolute path
            dedup = {}
            for full, source in font_paths:
                key = os.path.abspath(full).lower()
                if key not in dedup:
                    dedup[key] = (full, source)

            items = []
            for _, (full, source) in dedup.items():
                label = f"{os.path.splitext(os.path.basename(full))[0]} ({source})"
                items.append((label, full))

            items.sort(key=lambda it: it[0].lower())

            current_text = ""
            try:
                current_text = combo.currentText() or ""
            except Exception:
                pass

            desired = (selected_path or "").strip() or current_text.strip()

            self._preview_syncing = True
            try:
                combo.blockSignals(True)
                combo.clear()
                self._title_font_lookup = {}
                for label, full in items:
                    combo.addItem(label, full)
                    self._title_font_lookup[label] = full

                if desired:
                    idx = combo.findData(desired)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    else:
                        combo.setEditText(desired)
            finally:
                try:
                    combo.blockSignals(False)
                except Exception:
                    pass
                self._preview_syncing = False
        except Exception:
            pass

    def _load_title_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.pv_title_font, selected_path)

    def _load_user_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.pv_user_font, selected_path)

    def _load_rank_name_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.rk_name_font, selected_path)

    def _load_rank_info_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.rk_info_font, selected_path)

    def _prune_backups(self, target_path: str, keep: int = 5):
        prune_backups(target_path, keep=keep)

    def _rotate_log_file(self, log_path: str, max_bytes: int = 2_000_000, keep: int = 5):
        rotate_log_file(log_path, max_bytes=max_bytes, keep=keep)

    def _open_tracked_writer(self, header: str):
        self._tracked_fp = open_tracked_writer(
            self._repo_root,
            getattr(self, "_tracked_fp", None),
            header,
        )

    def _save_preview(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")
            try:
                self._set_status("Preview: saving...")
            except Exception:
                pass
            repo_root = self._repo_root
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as fh:
                    cfg = json.load(fh)
            except Exception:
                cfg = {}

            cfg["EXAMPLE_NAME"] = self.pv_name.text() or cfg.get("EXAMPLE_NAME", "NewMember")
            cfg["BG_MODE"] = self.pv_bg_mode.currentData() or cfg.get("BG_MODE", "cover")
            cfg["BG_ZOOM"] = int(self.pv_bg_zoom.value())
            cfg["BG_OFFSET_X"] = int(self.pv_bg_x.value())
            cfg["BG_OFFSET_Y"] = int(self.pv_bg_y.value())
            cfg["BANNER_TITLE"] = self.pv_title.text() or cfg.get("BANNER_TITLE", "WELCOME")
            cfg["OFFSET_X"] = int(self.pv_avatar_x.value())
            cfg["OFFSET_Y"] = int(self.pv_avatar_y.value())
            cfg["TITLE_FONT_SIZE"] = int(self.pv_title_size.value())
            cfg["USERNAME_FONT_SIZE"] = int(self.pv_user_size.value())
            cfg["TITLE_COLOR"] = (self.pv_title_color.text() or cfg.get("TITLE_COLOR", "#FFFFFF")).strip()
            cfg["USERNAME_COLOR"] = (self.pv_user_color.text() or cfg.get("USERNAME_COLOR", "#E6E6E6")).strip()
            cfg["TITLE_OFFSET_X"] = int(self.pv_title_x.value())
            cfg["TITLE_OFFSET_Y"] = int(self.pv_title_y.value())
            cfg["USERNAME_OFFSET_X"] = int(self.pv_user_x.value())
            cfg["USERNAME_OFFSET_Y"] = int(self.pv_user_y.value())
            cfg["TEXT_OFFSET_X"] = int(self.pv_text_x.value())
            cfg["TEXT_OFFSET_Y"] = int(self.pv_text_y.value())

            selected_title_font = self._selected_title_font_path() or cfg.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")
            saved_title_font = selected_title_font
            try:
                if selected_title_font and os.path.exists(selected_title_font):
                    assets_fonts = os.path.join(repo_root, "assets", "fonts")
                    os.makedirs(assets_fonts, exist_ok=True)
                    base_name = os.path.basename(selected_title_font)
                    target_path = os.path.join(assets_fonts, base_name)
                    import shutil

                    if os.path.abspath(selected_title_font) != os.path.abspath(target_path):
                        shutil.copy2(selected_title_font, target_path)
                    saved_title_font = os.path.join("assets", "fonts", base_name).replace("\\", "/")
            except Exception:
                pass

            cfg["FONT_WELCOME"] = saved_title_font

            selected_user_font = self._selected_user_font_path() or cfg.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")
            saved_user_font = selected_user_font
            try:
                if selected_user_font and os.path.exists(selected_user_font):
                    assets_fonts = os.path.join(repo_root, "assets", "fonts")
                    os.makedirs(assets_fonts, exist_ok=True)
                    base_name = os.path.basename(selected_user_font)
                    target_path = os.path.join(assets_fonts, base_name)
                    import shutil

                    if os.path.abspath(selected_user_font) != os.path.abspath(target_path):
                        shutil.copy2(selected_user_font, target_path)
                    saved_user_font = os.path.join("assets", "fonts", base_name).replace("\\", "/")
            except Exception:
                pass

            cfg["FONT_USERNAME"] = saved_user_font

            banner_path_input = self.pv_banner_path.text() or cfg.get("BANNER_PATH", "assets/welcome.png")
            banner_path_saved = banner_path_input
            try:
                if banner_path_input and os.path.exists(banner_path_input):
                    assets_dir = os.path.join(repo_root, "assets")
                    os.makedirs(assets_dir, exist_ok=True)
                    _, ext = os.path.splitext(banner_path_input)
                    ext = ext.lower() if ext else ".png"
                    if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
                        ext = ".png"
                    target_name = f"welcome_custom{ext}"
                    target_path = os.path.join(assets_dir, target_name)
                    import shutil

                    shutil.copy2(banner_path_input, target_path)
                    banner_path_saved = os.path.join("assets", target_name).replace("\\", "/")
                    self.pv_banner_path.setText(banner_path_saved)
            except Exception:
                pass

            cfg["BANNER_PATH"] = banner_path_saved or cfg.get("BANNER_PATH", "assets/welcome.png")
            # Prevent accidental deletion: do not overwrite WELCOME_MESSAGE with an empty value.
            new_msg = self.pv_message.toPlainText()
            if new_msg and new_msg.strip():
                cfg["WELCOME_MESSAGE"] = new_msg
            else:
                # keep existing message if present
                cfg["WELCOME_MESSAGE"] = cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", ""))

            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            # create a backup of the existing config to avoid data loss
            try:
                if os.path.exists(cfg_path):
                    import shutil, time
                    bak = cfg_path + ".bak." + str(int(time.time()))
                    shutil.copy2(cfg_path, bak)
                    self._prune_backups(cfg_path, keep=5)
            except Exception:
                pass
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2, ensure_ascii=False)

            self._preview_dirty = False

            # update preview immediately
            try:
                self.update_preview()
            except Exception:
                pass

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_preview,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Preview settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save preview settings: {e}")

    def _apply_live_preview(self):
        # render preview from current fields (banner + formatted message)
        try:
            name = self.pv_name.text() or "NewMember"
            banner = self.pv_banner_path.text() or ""
            message = self.pv_message.toPlainText() or "Welcome {mention}!"

            # Use a cached banner data URL produced only by the Refresh Preview button.
            # Do NOT call the control API here — banner generation should be explicit.
            banner_url = getattr(self, "_preview_banner_data_url", None) or ""
            if banner_url:
                # if we have a data URL, pv_banner was already set by the Refresh handler
                pass
            else:
                # fall back to local file if provided
                if banner and os.path.exists(banner):
                    try:
                        pix = QtGui.QPixmap(banner)
                        try:
                            scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                            self.pv_banner.setPixmap(scaled)
                        except Exception:
                            self.pv_banner.setPixmap(pix)
                    except Exception:
                        try:
                            self.pv_banner.clear()
                        except Exception:
                            pass
                    banner_url = f"file:///{os.path.abspath(banner).replace('\\', '/')}"
                else:
                    try:
                        self.pv_banner.clear()
                    except Exception:
                        pass

            # substitute placeholder in plain text (no HTML embed)
            rendered = message.replace("{mention}", f"@{name}")
            try:
                self.pv_banner.setToolTip(rendered)
            except Exception:
                pass

            # No rich embed is rendered; banner tooltip is used for message preview.
            pass
        except Exception:
            pass

    def tail_logs(self):
        try:
            # Prefer background poller when active to keep UI thread light.
            if getattr(self, "_log_poller", None):
                return
            # if tailing a sqlite DB
            if getattr(self, "_db_conn", None) and getattr(self, "_db_table", None):
                try:
                    cur = self._db_conn.cursor()
                    cur.execute(f"SELECT rowid, * FROM '{self._db_table}' WHERE rowid > ? ORDER BY rowid ASC", (self._db_last_rowid,))
                    rows = cur.fetchall()
                    for row in rows:
                        try:
                            line = self._format_db_row(row)
                        except Exception:
                            try:
                                line = str(dict(row))
                            except Exception:
                                line = str(tuple(row))
                        self.log_text.appendPlainText(line)
                        try:
                            if getattr(self, "_tracked_fp", None):
                                self._tracked_fp.write(line + "\n")
                                self._tracked_fp.flush()
                        except Exception:
                            pass
                        try:
                            self._db_last_rowid = int(row['rowid'])
                        except Exception:
                            try:
                                self._db_last_rowid = int(row[0])
                            except Exception:
                                pass
                    # scroll
                    self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
                except Exception:
                    pass
                return

            # otherwise tail a plain file
            if not getattr(self, "_log_fp", None):
                return
            for line in self._log_fp:
                txt = line.rstrip()
                self.log_text.appendPlainText(txt)
                # also append to tracked log if available
                try:
                    if getattr(self, "_tracked_fp", None):
                        try:
                            self._tracked_fp.write(txt + "\n")
                            self._tracked_fp.flush()
                        except Exception:
                            pass
                except Exception:
                    pass
            # keep the view scrolled to bottom
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        except Exception:
            pass

    def _poll_dashboard_console(self):
        try:
            path = getattr(self, "_dash_console_path", None)
            if not path:
                return
            if not os.path.exists(path):
                self._dash_console_pos = 0
                return

            try:
                size = os.path.getsize(path)
            except Exception:
                size = None

            pos = int(getattr(self, "_dash_console_pos", 0) or 0)
            if size is not None and pos > size:
                pos = 0

            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                if pos > 0:
                    fh.seek(pos)
                chunk = fh.read()
                self._dash_console_pos = fh.tell()

            if not chunk:
                return

            lines = chunk.splitlines()
            if lines:
                self.dash_console.appendPlainText("\n".join(lines))
                sb = self.dash_console.verticalScrollBar()
                sb.setValue(sb.maximum())
        except Exception:
            pass

    def update_preview(self):
        # simple preview using config/welcome.json values
        try:
            repo_root = self._repo_root
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            if not os.path.exists(cfg_path):
                try:
                    self.status_label.setText("No welcome config found")
                    self.pv_banner.clear()
                except Exception:
                    pass
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception:
            cfg = {}

        # show banner image if available (for Preview tab)
        banner = cfg.get("BANNER_PATH") or os.path.join(repo_root, "assets", "welcome.png")
        try:
            # if a generated banner data URL exists (from Refresh), do not overwrite the shown pixmap
            if getattr(self, "_preview_banner_data_url", None):
                # keep the banner set by Refresh Preview
                pass
            else:
                if banner and os.path.exists(banner):
                    pix = QtGui.QPixmap(banner)
                    try:
                        scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        self.pv_banner.setPixmap(scaled)
                    except Exception:
                        try:
                            self.pv_banner.setPixmap(pix)
                        except Exception:
                            pass
                else:
                    try:
                        self.pv_banner.clear()
                    except Exception:
                        pass
        except Exception:
            try:
                self.pv_banner.clear()
            except Exception:
                pass

        # update fields in Preview tab and render
        try:
            # Do not clobber manual edits: while unsaved changes exist, keep UI values.
            if not getattr(self, "_preview_dirty", False):
                self._preview_syncing = True
                try:
                    if not self.pv_name.hasFocus():
                        self.pv_name.setText(str(cfg.get("EXAMPLE_NAME", "NewMember")))
                    if not self.pv_banner_path.hasFocus():
                        self.pv_banner_path.setText(str(cfg.get("BANNER_PATH", "")))
                    if not self.pv_bg_mode.hasFocus():
                        mode_val = str(cfg.get("BG_MODE", "cover") or "cover")
                        idx = self.pv_bg_mode.findData(mode_val)
                        self.pv_bg_mode.setCurrentIndex(idx if idx >= 0 else 0)
                    if not self.pv_bg_zoom.hasFocus():
                        self.pv_bg_zoom.setValue(int(cfg.get("BG_ZOOM", 100) or 100))
                    if not self.pv_bg_x.hasFocus():
                        self.pv_bg_x.setValue(int(cfg.get("BG_OFFSET_X", 0) or 0))
                    if not self.pv_bg_y.hasFocus():
                        self.pv_bg_y.setValue(int(cfg.get("BG_OFFSET_Y", 0) or 0))
                    if not self.pv_title.hasFocus():
                        self.pv_title.setText(str(cfg.get("BANNER_TITLE", "WELCOME")))
                    if not self.pv_title_font.hasFocus():
                        self._load_title_font_choices(str(cfg.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")))
                    if not self.pv_user_font.hasFocus():
                        self._load_user_font_choices(str(cfg.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")))
                    if not self.pv_title_size.hasFocus():
                        self.pv_title_size.setValue(int(cfg.get("TITLE_FONT_SIZE", 140) or 140))
                    if not self.pv_user_size.hasFocus():
                        self.pv_user_size.setValue(int(cfg.get("USERNAME_FONT_SIZE", 64) or 64))
                    if not self.pv_title_color.hasFocus():
                        self.pv_title_color.setText(str(cfg.get("TITLE_COLOR", "#FFFFFF")))
                    if not self.pv_user_color.hasFocus():
                        self.pv_user_color.setText(str(cfg.get("USERNAME_COLOR", "#E6E6E6")))
                    if not self.pv_title_x.hasFocus():
                        self.pv_title_x.setValue(int(cfg.get("TITLE_OFFSET_X", 0) or 0))
                    if not self.pv_title_y.hasFocus():
                        self.pv_title_y.setValue(int(cfg.get("TITLE_OFFSET_Y", 0) or 0))
                    if not self.pv_user_x.hasFocus():
                        self.pv_user_x.setValue(int(cfg.get("USERNAME_OFFSET_X", 0) or 0))
                    if not self.pv_user_y.hasFocus():
                        self.pv_user_y.setValue(int(cfg.get("USERNAME_OFFSET_Y", 0) or 0))
                    if not self.pv_text_x.hasFocus():
                        self.pv_text_x.setValue(int(cfg.get("TEXT_OFFSET_X", 0) or 0))
                    if not self.pv_text_y.hasFocus():
                        self.pv_text_y.setValue(int(cfg.get("TEXT_OFFSET_Y", 0) or 0))
                    if not self.pv_avatar_x.hasFocus():
                        self.pv_avatar_x.setValue(int(cfg.get("OFFSET_X", 0) or 0))
                    if not self.pv_avatar_y.hasFocus():
                        self.pv_avatar_y.setValue(int(cfg.get("OFFSET_Y", 0) or 0))

                    # Load canonical message when not actively edited.
                    welcome_msg = cfg.get("WELCOME_MESSAGE")
                    if welcome_msg and not self.pv_message.hasFocus():
                        cur_text = self.pv_message.toPlainText()
                        if not cur_text or not cur_text.strip():
                            try:
                                self.pv_message.setPlainText(str(welcome_msg))
                            except Exception:
                                pass
                finally:
                    self._preview_syncing = False

            try:
                self._apply_live_preview()
            except Exception:
                pass
        except Exception:
            pass

    def _load_welcome_message_from_file(self):
        """Load the canonical `WELCOME_MESSAGE` from config/welcome.json and
        set it into the Preview message field (overwrites current text).
        This is intended to be called only after a successful Save + Reload.
        """
        try:
            repo_root = self._repo_root
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            if not os.path.exists(cfg_path):
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            msg = str(cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", "Welcome {mention}!")))
            # overwrite regardless of focus because the user explicitly requested reload
            try:
                self._preview_syncing = True
                self.pv_message.setPlainText(msg)
            except Exception:
                pass
            finally:
                self._preview_syncing = False
            self._preview_dirty = False
            try:
                self._apply_live_preview()
            except Exception:
                pass
        except Exception:
            pass


def main():
    sys.exit(run_main_window(MainWindow))


if __name__ == "__main__":
    main()
