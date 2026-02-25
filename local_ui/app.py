"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""



import sys
import os
import json
import socket
import sqlite3
import subprocess
import traceback
from datetime import datetime
# HTML embed removed; no html module required
from PySide6 import QtWidgets, QtCore, QtGui


API_ADDR = ("127.0.0.1", 8765)


# Background thread to poll log files or sqlite DBs without blocking the UI
class LogPoller(QtCore.QThread):
    new_line = QtCore.Signal(str)

    def __init__(self, path: str, mode: str = "file", table: str = None, last_rowid: int = 0, interval: float = 5.0):
        super().__init__()
        self.path = path
        self.mode = mode  # 'file' or 'db'
        self.table = table
        self._last_rowid = int(last_rowid or 0)
        self._interval = float(interval)
        self._stopped = False

    def stop(self):
        self._stopped = True
        try:
            self.wait(2000)
        except Exception:
            pass

    def run(self):
        try:
            if self.mode == "db":
                # open local sqlite connection here
                try:
                    conn = sqlite3.connect(self.path)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                except Exception:
                    return

                while not self._stopped:
                    try:
                        cur.execute(f"SELECT rowid, * FROM '{self.table}' WHERE rowid > ? ORDER BY rowid ASC", (self._last_rowid,))
                        rows = cur.fetchall()
                        for row in rows:
                            try:
                                # emit formatted row as string; caller will format further if needed
                                try:
                                    data = dict(row)
                                    s = json.dumps(data, ensure_ascii=False)
                                except Exception:
                                    s = str(tuple(row))
                                self.new_line.emit(s)
                            except Exception:
                                pass
                            try:
                                self._last_rowid = int(row['rowid'])
                            except Exception:
                                try:
                                    self._last_rowid = int(row[0])
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # sleep in ms-aware chunks
                    for _ in range(int(self._interval * 10)):
                        if self._stopped:
                            break
                        self.msleep(100)
                try:
                    conn.close()
                except Exception:
                    pass
            else:
                # file mode: tail the file
                try:
                    with open(self.path, 'r', encoding='utf-8', errors='ignore') as fh:
                        fh.seek(0, os.SEEK_END)
                        while not self._stopped:
                            line = fh.readline()
                            if line:
                                self.new_line.emit(line.rstrip('\n'))
                            else:
                                self.msleep(int(self._interval * 1000))
                except Exception:
                    pass
        except Exception:
            pass


# Event tracing is expensive; enable only when UI_EVENT_TRACE=1 is set in the environment.
if os.environ.get("UI_EVENT_TRACE") == "1":
    try:
        _trace_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs")
        os.makedirs(_trace_dir, exist_ok=True)
        with open(os.path.join(_trace_dir, "ui_run_trace.log"), "a", encoding="utf-8") as _tf:
            _tf.write(f"startup: {datetime.now().isoformat()}\n")
        print("UI startup: trace written", flush=True)
    except Exception:
        try:
            print("UI startup: trace failed", flush=True)
        except Exception:
            pass


def send_cmd(cmd: dict, timeout: float = 1.0):
    try:
        # attach token from environment if present
        token = os.environ.get("CONTROL_API_TOKEN")
        payload = dict(cmd)
        if token:
            payload["token"] = token

        with socket.create_connection(API_ADDR, timeout=timeout) as s:
            s.sendall((json.dumps(payload) + "\n").encode())
            # read a line
            buf = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    break
            line = buf.split(b"\n", 1)[0]
            return json.loads(line.decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Global exception handler so click-time crashes show a dialog and are logged
def _handle_uncaught_exception(exc_type, exc_value, exc_tb):
    tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        # print to stderr/console
        print(tb, file=sys.stderr)
    except Exception:
        pass
    try:
        # attempt to show a dialog if Qt is running
        app = QtWidgets.QApplication.instance()
        if app:
            try:
                QtWidgets.QMessageBox.critical(None, "Unhandled Exception", tb)
            except Exception:
                pass
    except Exception:
        pass
    try:
        # write to a persistent ui crash log
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(repo_root, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, "ui_crash.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"--- {datetime.now().isoformat()} ---\n")
            fh.write(tb + "\n")
    except Exception:
        pass


sys.excepthook = _handle_uncaught_exception


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DC Bot — Local UI")
        self.resize(900, 600)
        # Repo root path for data/logs tracking
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # central tabs
        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)

        # Dashboard tab
        dash = QtWidgets.QWidget()
        dash_layout = QtWidgets.QVBoxLayout(dash)

        self.status_label = QtWidgets.QLabel("Status: unknown")
        self.status_label.setObjectName("statusLabel")
        dash_layout.addWidget(self.status_label)

        btn_row = QtWidgets.QHBoxLayout()
        self.ping_btn = QtWidgets.QPushButton("Ping")
        self.refresh_btn = QtWidgets.QPushButton("Refresh Status")
        self.reload_btn = QtWidgets.QPushButton("Reload Cogs")
        self.shutdown_btn = QtWidgets.QPushButton("Shutdown Bot")
        self.restart_btn = QtWidgets.QPushButton("Restart Bot & UI")

        for w in (self.ping_btn, self.refresh_btn, self.reload_btn, self.shutdown_btn):
            btn_row.addWidget(w)
        # place restart button to the right of shutdown
        btn_row.addWidget(self.restart_btn)

        dash_layout.addLayout(btn_row)

        # connect dashboard buttons
        self.ping_btn.clicked.connect(self.on_ping)
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.reload_btn.clicked.connect(self.on_reload)
        # config editor is available as its own tab; dashboard button removed
        self.shutdown_btn.clicked.connect(self.on_shutdown)
        self.restart_btn.clicked.connect(self.on_restart_and_restart_ui)

        # Dashboard quick summary removed — detailed preview is in the Preview tab

        dash_layout.addStretch()

        tabs.addTab(dash, "Dashboard")

        # Logs tab (live tail)
        logs = QtWidgets.QWidget()
        logs_layout = QtWidgets.QVBoxLayout(logs)
        top_row = QtWidgets.QHBoxLayout()
        self.choose_log_btn = QtWidgets.QPushButton("Choose Log...")
        self.clear_log_btn = QtWidgets.QPushButton("Clear")
        top_row.addWidget(self.choose_log_btn)
        top_row.addWidget(self.clear_log_btn)
        top_row.addStretch()
        logs_layout.addLayout(top_row)

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        logs_layout.addWidget(self.log_text)
        # wire buttons
        self.choose_log_btn.clicked.connect(self._choose_log_file)
        self.clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        tabs.addTab(logs, "Logs")

        # Config editor tab
        self.cfg_editor = ConfigEditor(self)
        tabs.addTab(self.cfg_editor, "Configs")

        # Preview tab (detailed settings + render)
        preview_w = QtWidgets.QWidget()
        pv_layout = QtWidgets.QVBoxLayout(preview_w)

        pv_top = QtWidgets.QHBoxLayout()
        self.pv_banner = QtWidgets.QLabel()
        self.pv_banner.setFixedSize(520, 180)
        self.pv_banner.setScaledContents(True)
        pv_top.addWidget(self.pv_banner, 0)

        pv_form = QtWidgets.QFormLayout()
        self.pv_name = QtWidgets.QLineEdit()
        self.pv_banner_path = QtWidgets.QLineEdit()
        self.pv_banner_browse = QtWidgets.QPushButton("Choose...")
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.pv_banner_path)
        h.addWidget(self.pv_banner_browse)
        pv_form.addRow("Example name:", self.pv_name)
        pv_form.addRow("Banner image:", h)
        self.pv_message = QtWidgets.QPlainTextEdit()
        self.pv_message.setPlaceholderText("Welcome message template. Use {mention} for mention.")
        pv_form.addRow("Message:", self.pv_message)

        # placeholder helper buttons
        ph_row = QtWidgets.QHBoxLayout()
        self.ph_mention = QtWidgets.QPushButton("{mention}")
        self.ph_rules = QtWidgets.QPushButton("{rules_channel}")
        self.ph_verify = QtWidgets.QPushButton("{verify_channel}")
        self.ph_about = QtWidgets.QPushButton("{aboutme_channel}")
        ph_row.addWidget(self.ph_mention)
        ph_row.addWidget(self.ph_rules)
        ph_row.addWidget(self.ph_verify)
        ph_row.addWidget(self.ph_about)
        pv_form.addRow("Placeholders:", ph_row)

        # wire placeholder buttons to insert text at cursor
        self.ph_mention.clicked.connect(lambda: self._insert_placeholder('{mention}'))
        self.ph_rules.clicked.connect(lambda: self._insert_placeholder('{rules_channel}'))
        self.ph_verify.clicked.connect(lambda: self._insert_placeholder('{verify_channel}'))
        self.ph_about.clicked.connect(lambda: self._insert_placeholder('{aboutme_channel}'))

        pv_top.addLayout(pv_form, 1)
        pv_layout.addLayout(pv_top)

        # Toolbar row for preview actions
        pv_row = QtWidgets.QHBoxLayout()
        self.pv_save = QtWidgets.QPushButton("Save")
        self.pv_save_reload = QtWidgets.QPushButton("Save + Reload")
        self.pv_refresh = QtWidgets.QPushButton("Refresh Preview")
        pv_row.addStretch()
        pv_row.addWidget(self.pv_refresh)
        pv_row.addWidget(self.pv_save)
        pv_row.addWidget(self.pv_save_reload)
        pv_layout.addLayout(pv_row)

        tabs.addTab(preview_w, "Welcome")

        # Rankcard preview tab
        rank_w = QtWidgets.QWidget()
        rank_layout = QtWidgets.QVBoxLayout(rank_w)

        # Rankcard layout: preview on the left, controls on the right
        rk_main = QtWidgets.QHBoxLayout()

        # Left: preview area with header
        rk_left = QtWidgets.QVBoxLayout()
        lbl_preview = QtWidgets.QLabel("Preview")
        lbl_preview.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl_preview.setStyleSheet("font-weight:700; font-size:14px; margin-bottom:6px;")
        rk_left.addWidget(lbl_preview)
        self.rk_image = QtWidgets.QLabel()
        self.rk_image.setFixedSize(700, 210)
        self.rk_image.setScaledContents(True)
        rk_left.addWidget(self.rk_image)
        rk_left.addStretch()

        # Right: form controls and actions
        rk_right = QtWidgets.QVBoxLayout()
        rk_form = QtWidgets.QFormLayout()
        self.rk_name = QtWidgets.QLineEdit()
        self.rk_bg_path = QtWidgets.QLineEdit()
        self.rk_bg_browse = QtWidgets.QPushButton("Choose...")
        hbg = QtWidgets.QHBoxLayout()
        hbg.addWidget(self.rk_bg_path)
        hbg.addWidget(self.rk_bg_browse)
        rk_form.addRow("Example name:", self.rk_name)
        rk_form.addRow("Background PNG:", hbg)
        rk_right.addLayout(rk_form)

        # Add a small info label under the form
        info = QtWidgets.QLabel("Choose a background PNG to preview the rankcard. Use Save + Reload to apply to the bot.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#9aa0a6; font-size:11px; margin-top:8px;")
        rk_right.addWidget(info)
        rk_right.addStretch()

        # action buttons (aligned right)
        rk_buttons = QtWidgets.QHBoxLayout()
        self.rk_refresh = QtWidgets.QPushButton("Refresh Rankcard")
        self.rk_save = QtWidgets.QPushButton("Save")
        self.rk_save_reload = QtWidgets.QPushButton("Save + Reload")
        rk_buttons.addStretch()
        rk_buttons.addWidget(self.rk_refresh)
        rk_buttons.addWidget(self.rk_save)
        rk_buttons.addWidget(self.rk_save_reload)
        rk_right.addLayout(rk_buttons)

        rk_main.addLayout(rk_left, 1)
        rk_main.addLayout(rk_right, 0)
        rank_layout.addLayout(rk_main)

        tabs.addTab(rank_w, "Rankcard")

        # wire rankcard controls
        self.rk_refresh.clicked.connect(self.on_refresh_rankpreview)
        self.rk_bg_browse.clicked.connect(self._choose_rank_bg)
        self.rk_save.clicked.connect(lambda: self._save_rank_preview(reload_after=False))
        self.rk_save_reload.clicked.connect(lambda: self._save_rank_preview(reload_after=True))

        # wire preview controls
        self.pv_banner_browse.clicked.connect(self._choose_banner)
        self.pv_refresh.clicked.connect(self.on_refresh_preview)
        self.pv_save.clicked.connect(lambda: self._save_preview(reload_after=False))
        self.pv_save_reload.clicked.connect(lambda: self._save_preview(reload_after=True))

        # live preview: debounce updates while typing
        self._preview_debounce = QtCore.QTimer(self)
        self._preview_debounce.setSingleShot(True)
        self._preview_debounce.setInterval(250)
        self._preview_debounce.timeout.connect(self._apply_live_preview)

        # QLineEdit.textChanged provides the new text, QPlainTextEdit.textChanged provides no args
        # Use an argless wrapper so signal/slot signatures match and avoid TypeError
        self.pv_name.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_banner_path.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_message.textChanged.connect(lambda: self._preview_debounce.start())
        self.rk_name.textChanged.connect(lambda: self._preview_debounce.start())
        # ensure rank preview doesn't get clobbered when other previews update

        self.setCentralWidget(tabs)

        # styling
        self.setStyleSheet("""
        QWidget { font-family: Segoe UI, Arial, Helvetica, sans-serif; }
        #statusLabel { font-weight: bold; font-size: 14px; }
        QGroupBox { border: 1px solid #ddd; border-radius: 6px; padding: 8px; }
        QPushButton { padding: 6px 10px; }
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
        self._open_log()
        self.on_refresh()
        # load rank config if present
        try:
            self._load_rank_config()
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
    def on_ping(self):
        r = send_cmd({"action": "ping"})
        QtWidgets.QMessageBox.information(self, "Ping", str(r))

    def on_refresh(self):
        r = send_cmd({"action": "status"})
        if r.get("ok"):
            user = r.get("user") or "(no user)"
            ready = r.get("ready")
            cogs = r.get("cogs", [])
            self.status_label.setText(f"User: {user} — Ready: {ready} — Cogs: {len(cogs)}")
            # update preview when status refreshed
            try:
                self.update_preview()
            except Exception:
                pass

    def on_refresh_preview(self):
        """Request a banner preview from the bot and update the preview widgets."""
        try:
            try:
                self._set_status("Preview: requesting...")
            except Exception:
                pass
            name = self.pv_name.text() or "NewMember"
            # quick ping to avoid long waits when the bot control API is not running
            ping = send_cmd({"action": "ping"}, timeout=0.6)
            if not ping.get("ok"):
                # fallback to local preview immediately
                QtWidgets.QMessageBox.warning(self, "Preview", f"Control API not available, using local banner ({ping.get('error')})")
                try:
                    self.update_preview()
                except Exception:
                    pass
                return

            # API reachable — request the generated banner (give it more time)
            r = send_cmd({"action": "banner_preview", "name": name}, timeout=5.0)
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
                        self.pv_banner.setPixmap(scaled)
                    except Exception:
                        self.pv_banner.setPixmap(pix)
                    # store data URL for embedding into the HTML preview
                    self._preview_banner_data_url = f"data:image/png;base64,{b64}"
                    # re-render live preview using this banner
                    try:
                        self._apply_live_preview()
                    except Exception:
                        pass
                    return
            # if we get here, fallback to existing update_preview behaviour
            QtWidgets.QMessageBox.warning(self, "Preview", f"Failed to get banner from bot: {r}")
            try:
                self.update_preview()
            except Exception:
                pass
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Preview error", str(e))
        else:
            self.status_label.setText(f"Status: offline ({r.get('error')})")

    def on_refresh_rankpreview(self):
        """Request a rankcard from the bot and display it in the Rankcard tab."""
        try:
            try:
                self._set_status("Rank Preview: requesting...")
            except Exception:
                pass
            name = self.rk_name.text() or (self.pv_name.text() or "NewMember")
            # prefer explicit field; if empty, use persisted config
            bg = self.rk_bg_path.text() or self._rank_config.get("BG_PATH") if getattr(self, "_rank_config", None) is not None else None
            req = {"action": "rank_preview", "name": name}
            if bg:
                req["bg_path"] = bg
            r = send_cmd(req, timeout=3.0)
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
                    except Exception:
                        self.rk_image.setPixmap(pix)
                    # store for persistence if needed
                    self._rank_preview_data_url = f"data:image/png;base64,{b64}"
                    return
            QtWidgets.QMessageBox.warning(self, "Rank Preview", f"Failed to get rankcard from bot: {r}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Rank Preview error", str(e))

    def on_shutdown(self):
        r = send_cmd({"action": "shutdown"})
        if r.get("ok"):
            QtWidgets.QMessageBox.information(self, "Shutdown", "Bot is shutting down")
        else:
            QtWidgets.QMessageBox.warning(self, "Shutdown", f"Failed: {r}")

    def on_restart_and_restart_ui(self):
        """Shutdown the bot (via control API), attempt to start bot.py, then relaunch the UI.

        This method will: 1) ask for confirmation, 2) request bot shutdown, 3) spawn a new bot process
        if `bot.py` exists in the repo root, 4) spawn a new UI process running this script, and
        5) quit the current UI.
        """
        try:
            self._set_status("Restart: preparing...")
        except Exception:
            pass
        ok = QtWidgets.QMessageBox.question(self, "Restart", "Restart the bot and the UI? This will stop the bot and relaunch both.", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if ok != QtWidgets.QMessageBox.Yes:
            return

        # 1) request bot shutdown via control API (best-effort)
        try:
            r = send_cmd({"action": "shutdown"}, timeout=2.0)
        except Exception:
            r = {"ok": False}

        # 2) attempt to start bot.py if present
        try:
            bot_path = os.path.join(self._repo_root, "bot.py")
            if os.path.exists(bot_path):
                try:
                    subprocess.Popen([sys.executable, bot_path], cwd=self._repo_root)
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to start bot.py: {e}")
            else:
                QtWidgets.QMessageBox.information(self, "Restart", "bot.py not found — UI will restart only.")
        except Exception:
            pass

        # 3) spawn a new UI process running this script
        try:
            subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=self._repo_root)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to relaunch UI: {e}")

        # 4) quit current application
        try:
            QtWidgets.QApplication.quit()
        except Exception:
            try:
                sys.exit(0)
            except Exception:
                pass

    def on_reload(self):
        r = send_cmd({"action": "reload"})
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
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
                            tracked_dir = os.path.join(self._repo_root, "data", "logs")
                            os.makedirs(tracked_dir, exist_ok=True)
                            # open tracked file in append mode
                            tracked_path = os.path.join(tracked_dir, "tracked.log")
                            # close previous tracked fp if present
                            if getattr(self, "_tracked_fp", None):
                                try:
                                    self._tracked_fp.close()
                                except Exception:
                                    pass
                            self._tracked_fp = open(tracked_path, "a", encoding="utf-8", errors="ignore")
                            # write header about source
                            try:
                                self._tracked_fp.write(f"\n--- Tailing: {log_path} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---\n")
                                self._tracked_fp.flush()
                            except Exception:
                                pass
                        except Exception:
                            pass
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
                self._set_status("Banner: choosing image...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            start_dir = repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose log file", start_dir, "Log files (*.log *.txt);;All files (*)")
            if path:
                try:
                    # close any previous file or DB connection
                    try:
                        if getattr(self, "_db_conn", None):
                            try:
                                self._db_conn.close()
                            except Exception:
                                pass
                            self._db_conn = None
                            self._db_table = None
                            self._db_last_rowid = 0
                        if getattr(self, "_log_fp", None):
                            try:
                                self._log_fp.close()
                            except Exception:
                                pass
                            self._log_fp = None
                    except Exception:
                        pass

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
                                tracked_dir = os.path.join(self._repo_root, "data", "logs")
                                os.makedirs(tracked_dir, exist_ok=True)
                                tracked_path = os.path.join(tracked_dir, "tracked.log")
                                if getattr(self, "_tracked_fp", None):
                                    try:
                                        self._tracked_fp.close()
                                    except Exception:
                                        pass
                                self._tracked_fp = open(tracked_path, "a", encoding="utf-8", errors="ignore")
                                try:
                                    self._tracked_fp.write(f"\n--- Tailing DB: {path} table: {table} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---\n")
                                    self._tracked_fp.flush()
                                except Exception:
                                    pass
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
                        tracked_dir = os.path.join(self._repo_root, "data", "logs")
                        os.makedirs(tracked_dir, exist_ok=True)
                        tracked_path = os.path.join(tracked_dir, "tracked.log")
                        if getattr(self, "_tracked_fp", None):
                            try:
                                self._tracked_fp.close()
                            except Exception:
                                pass
                        self._tracked_fp = open(tracked_path, "a", encoding="utf-8", errors="ignore")
                        try:
                            self._tracked_fp.write(f"\n--- Tailing: {path} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---\n")
                            self._tracked_fp.flush()
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Open log", f"Failed to open log file: {e}")
        except Exception:
            pass

    def _choose_banner(self):
        try:
            try:
                self._set_status("Rank: choosing background...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose banner image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.pv_banner_path.setText(path)
                pix = QtGui.QPixmap(path)
                try:
                    scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
                    self.pv_banner.setPixmap(scaled)
                except Exception:
                    self.pv_banner.setPixmap(pix)
        except Exception:
            pass

    def _format_db_row(self, row: sqlite3.Row) -> str:
        """Format a sqlite3.Row by detecting common message/timestamp columns.

        Returns a single-line string like "[time] message" when possible,
        otherwise falls back to a dict/string representation.
        """
        try:
            data = dict(row)
        except Exception:
            try:
                return str(tuple(row))
            except Exception:
                return str(row)

        # prioritized keys commonly used for messages and timestamps
        msg_priority = ("message", "msg", "text", "content", "body", "payload", "data")
        ts_priority = ("created_at", "timestamp", "ts", "time", "date", "created")

        def _extract_message(d):
            # direct matches
            for k in msg_priority:
                if k in d and d.get(k) is not None:
                    return d.get(k)
            # substring matches
            for k in d.keys():
                lk = k.lower()
                if any(x in lk for x in ("message", "text", "content", "body", "payload")):
                    return d.get(k)
            return None

        def _extract_timestamp(d):
            for k in ts_priority:
                if k in d and d.get(k) is not None:
                    return d.get(k)
            for k in d.keys():
                lk = k.lower()
                if "time" in lk or "date" in lk or lk in ("ts", "timestamp", "created_at", "created"):
                    return d.get(k)
            return None

        msg_val = _extract_message(data)
        ts_val = _extract_timestamp(data)

        # if message looks like JSON string, try to parse and extract inner message
        if isinstance(msg_val, str):
            s = msg_val.strip()
            if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                try:
                    inner = json.loads(s)
                    if isinstance(inner, dict):
                        m2 = _extract_message(inner)
                        if m2 is not None:
                            msg_val = m2
                        else:
                            msg_val = inner
                except Exception:
                    pass

        # timestamp parsing helpers
        ts_str = None
        if ts_val is not None:
            try:
                if isinstance(ts_val, (int, float)):
                    # handle milliseconds vs seconds
                    v = float(ts_val)
                    if v > 1e12:
                        v = v / 1000.0
                    ts_str = datetime.fromtimestamp(v).isoformat(sep=' ')
                else:
                    s = str(ts_val).strip()
                    # numeric string
                    if s.isdigit():
                        v = float(s)
                        if v > 1e12:
                            v = v / 1000.0
                        ts_str = datetime.fromtimestamp(v).isoformat(sep=' ')
                    else:
                        # try ISO parser
                        try:
                            # handle trailing Z
                            s2 = s.replace('Z', '+00:00') if s.endswith('Z') else s
                            ts_str = datetime.fromisoformat(s2).isoformat(sep=' ')
                        except Exception:
                            ts_str = s
            except Exception:
                try:
                    ts_str = str(ts_val)
                except Exception:
                    ts_str = None

        # normalize message into a single-line string
        if msg_val is not None:
            try:
                if isinstance(msg_val, (dict, list)):
                    m = json.dumps(msg_val, ensure_ascii=False)
                else:
                    m = str(msg_val)
                m = m.replace('\n', ' ').strip()
            except Exception:
                m = str(msg_val)
            if ts_str:
                return f"[{ts_str}] {m}"
            return m

        # fallback: include timestamp if present
        if ts_str:
            try:
                return f"[{ts_str}] {json.dumps(data, ensure_ascii=False)}"
            except Exception:
                return f"[{ts_str}] {str(data)}"

        # last fallback
        try:
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return str(data)

    def _choose_rank_bg(self):
        try:
            try:
                self._set_status("Preview: saving...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose rank background image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.rk_bg_path.setText(path)
                # optional: show it scaled in the rank image preview area
                try:
                    pix = QtGui.QPixmap(path)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
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
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg_dir = os.path.join(repo_root, "config")
        os.makedirs(cfg_dir, exist_ok=True)
        cfg_path = os.path.join(cfg_dir, "rank.json")
        return cfg_path

    def _load_rank_config(self):
        cfg_path = self._rank_config_paths()
        self._rank_config_path = cfg_path
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as fh:
                    cfg = json.load(fh) or {}
            else:
                cfg = {}
        except Exception:
            cfg = {}
        self._rank_config = cfg
        # populate UI fields if empty
        try:
            bg = cfg.get("BG_PATH")
            if bg and (not self.rk_bg_path.text()):
                self.rk_bg_path.setText(str(bg))
                try:
                    pix = QtGui.QPixmap(bg)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
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
        try:
            try:
                with open(cfg_path, "r", encoding="utf-8") as fh:
                    existing = json.load(fh) or {}
            except Exception:
                existing = {}
            existing.update(data or {})
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump(existing, fh, indent=2, ensure_ascii=False)
            self._rank_config = existing
        except Exception:
            pass

    def _save_rank_preview(self, reload_after: bool = False):
        try:
            data = {}
            name = self.rk_name.text() or None
            bg = self.rk_bg_path.text() or None
            if name:
                data["EXAMPLE_NAME"] = name
            if bg:
                data["BG_PATH"] = bg
            if data:
                self._save_rank_config(data)

            if reload_after:
                try:
                    r2 = send_cmd({"action": "reload"}, timeout=3.0)
                    if r2.get("ok"):
                        try:
                            self._load_rank_config()
                        except Exception:
                            pass
                        reloaded = r2.get("reloaded", [])
                        failed = r2.get("failed", {})
                        msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                        if failed:
                            msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                        QtWidgets.QMessageBox.information(self, "Reload", msg)
                    else:
                        QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r2}")
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Rank settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save rank settings: {e}")

    def _insert_placeholder(self, text: str):
        try:
            cur = self.pv_message.textCursor()
            cur.insertText(text)
            self.pv_message.setTextCursor(cur)
            # trigger live preview
            try:
                self._preview_debounce.start()
            except Exception:
                pass
        except Exception:
            pass

    def _save_preview(self, reload_after: bool = False):
        try:
            try:
                self._set_status("Preview: saving...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as fh:
                    cfg = json.load(fh)
            except Exception:
                cfg = {}

            cfg["EXAMPLE_NAME"] = self.pv_name.text() or cfg.get("EXAMPLE_NAME", "NewMember")
            cfg["BANNER_PATH"] = self.pv_banner_path.text() or cfg.get("BANNER_PATH", cfg.get("BANNER_PATH", "assets/welcome.png"))
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
            except Exception:
                pass
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2, ensure_ascii=False)

            # update preview immediately
            try:
                self.update_preview()
            except Exception:
                pass

            if reload_after:
                try:
                    r2 = send_cmd({"action": "reload"}, timeout=3.0)
                    # show reload result to user
                    if r2.get("ok"):
                        # on success, load the persisted welcome message into the preview
                        try:
                            self._load_welcome_message_from_file()
                        except Exception:
                            pass
                        reloaded = r2.get("reloaded", [])
                        failed = r2.get("failed", {})
                        msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                        if failed:
                            msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                        QtWidgets.QMessageBox.information(self, "Reload", msg)
                    else:
                        QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r2}")
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
                            scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
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

    def update_preview(self):
        # simple preview using config/welcome.json values
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
                        scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
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
            # Only update fields if the user is not actively editing them (avoid clobbering)
            if not self.pv_name.hasFocus():
                self.pv_name.setText(str(cfg.get("EXAMPLE_NAME", "NewMember")))
            if not self.pv_banner_path.hasFocus():
                self.pv_banner_path.setText(str(cfg.get("BANNER_PATH", "")))

                # Load the canonical `WELCOME_MESSAGE` into the message field
                # unless the user is currently editing it. Only populate when
                # the field is empty to avoid overwriting user edits.
                welcome_msg = cfg.get("WELCOME_MESSAGE")
                if welcome_msg and not self.pv_message.hasFocus():
                    cur_text = self.pv_message.toPlainText()
                    if not cur_text or not cur_text.strip():
                        try:
                            self.pv_message.setPlainText(str(welcome_msg))
                        except Exception:
                            pass

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
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            if not os.path.exists(cfg_path):
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            msg = str(cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", "Welcome {mention}!")))
            # overwrite regardless of focus because the user explicitly requested reload
            try:
                self.pv_message.setPlainText(msg)
            except Exception:
                pass
            try:
                self._apply_live_preview()
            except Exception:
                pass
        except Exception:
            pass


class ConfigEditor(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Cog Configs")
        self.resize(700, 420)

        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.list = QtWidgets.QListWidget()
        self.load_button = QtWidgets.QPushButton("Refresh List")
        top.addWidget(self.list, 1)
        top.addWidget(self.load_button)
        layout.addLayout(top)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        row = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save")
        self.add_btn = QtWidgets.QPushButton("Add Key")
        self.remove_btn = QtWidgets.QPushButton("Remove Selected")
        row.addWidget(self.add_btn)
        row.addWidget(self.remove_btn)
        row.addStretch()
        row.addWidget(self.save_btn)
        layout.addLayout(row)

        self.load_button.clicked.connect(self.refresh_list)
        self.list.currentItemChanged.connect(self.on_select)
        self.save_btn.clicked.connect(self.on_save)
        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)

        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(os.path.join(self.repo_root, "config"), exist_ok=True)

        self.refresh_list()

    def refresh_list(self):
        cfg_dir = os.path.join(self.repo_root, "config")
        self.list.clear()
        try:
            for fn in sorted(os.listdir(cfg_dir)):
                if fn.endswith(".json"):
                    self.list.addItem(fn)
        except Exception:
            pass

    def on_select(self, current, prev=None):
        if current is None:
            return
        name = current.text()
        path = os.path.join(self.repo_root, "config", name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}

        self.table.setRowCount(0)
        if isinstance(data, dict):
            for k, v in data.items():
                r = self.table.rowCount()
                self.table.insertRow(r)
                key_item = QtWidgets.QTableWidgetItem(str(k))
                key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
                # represent simple values; for complex, show JSON
                if isinstance(v, (dict, list)):
                    val_text = json.dumps(v, ensure_ascii=False)
                else:
                    val_text = str(v) if v is not None else ""
                val_item = QtWidgets.QTableWidgetItem(val_text)
                self.table.setItem(r, 0, key_item)
                self.table.setItem(r, 1, val_item)

    def on_save(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        path = os.path.join(self.repo_root, "config", name)
        data = {}
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0).text()
            vtxt = self.table.item(r, 1).text()
            # try to interpret as int, bool, null, float, or JSON
            val = None
            if vtxt.lower() in ("null", "none", ""):
                val = None
            elif vtxt.lower() in ("true", "false"):
                val = vtxt.lower() == "true"
            else:
                try:
                    val = int(vtxt)
                except Exception:
                    try:
                        val = float(vtxt)
                    except Exception:
                        try:
                            val = json.loads(vtxt)
                        except Exception:
                            val = vtxt
            data[k] = val

        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            QtWidgets.QMessageBox.information(self, "Saved", f"Saved {name}")
            # if parent has update_preview, call it so UI preview updates
            try:
                parent = self.parent()
                if parent and hasattr(parent, "update_preview"):
                    parent.update_preview()
            except Exception:
                pass
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def on_add(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QtWidgets.QTableWidgetItem("NEW_KEY"))
        self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(""))

    def on_remove(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)


def main():
    # Prevent running multiple UI instances: try to bind an internal lock port.
    # If the port is already in use, assume another UI is running and exit.
    _lock_sock = None
    try:
        _lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _lock_sock.bind(("127.0.0.1", 8766))
        _lock_sock.listen(1)
    except Exception:
        try:
            print("Another UI instance seems to be running; exiting.")
        except Exception:
            pass
        try:
            if _lock_sock:
                _lock_sock.close()
        except Exception:
            pass
        return

    app = QtWidgets.QApplication(sys.argv)
    # Install a global event filter to trace mouse/key events for debugging
    class _EventLogger(QtCore.QObject):
        def eventFilter(self, obj, event):
            try:
                t = event.type()
            except Exception:
                t = None

            # Only log discrete input events (avoid high-frequency events like MouseMove)
            try:
                interesting = (
                    QtCore.QEvent.MouseButtonPress,
                    QtCore.QEvent.MouseButtonRelease,
                    QtCore.QEvent.KeyPress,
                    QtCore.QEvent.KeyRelease,
                    QtCore.QEvent.FocusIn,
                    QtCore.QEvent.FocusOut,
                )
            except Exception:
                interesting = ()

            if t in interesting:
                try:
                    name = None
                    if hasattr(QtCore.QEvent, 'typeToString'):
                        try:
                            name = QtCore.QEvent.typeToString(t)
                        except Exception:
                            name = str(t)
                    else:
                        name = str(t)
                    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    objname = getattr(obj, '__class__', type(obj)).__name__
                    line = f"EVENT {datetime.now().isoformat()} {name} obj={objname}\n"
                    # buffer instead of writing immediately
                    try:
                        buf = getattr(self, '_evbuf', None)
                        if buf is None:
                            self._evbuf = []
                            buf = self._evbuf
                        buf.append(line)
                    except Exception:
                        # best-effort fallback to direct append
                        try:
                            trace = os.path.join(repo_root, 'data', 'logs', 'ui_run_trace.log')
                            with open(trace, 'a', encoding='utf-8') as fh:
                                fh.write(line)
                        except Exception:
                            pass
                except Exception:
                    pass

            return super().eventFilter(obj, event)

    # Only enable event tracing if specifically requested via environment
    if os.environ.get("UI_EVENT_TRACE") == "1":
        try:
            evlogger = _EventLogger(app)
            app.installEventFilter(evlogger)
        except Exception:
            evlogger = None
        # setup periodic flush of the event buffer to file to avoid blocking
        def _flush_events():
            try:
                buf = getattr(evlogger, '_evbuf', None)
                if not buf:
                    return
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                trace = os.path.join(repo_root, 'data', 'logs', 'ui_run_trace.log')
                # swap buffer
                towrite = None
                try:
                    towrite = list(buf)
                    evlogger._evbuf.clear()
                except Exception:
                    towrite = buf
                    evlogger._evbuf = []
                try:
                    with open(trace, 'a', encoding='utf-8') as fh:
                        fh.writelines(towrite)
                except Exception:
                    pass
            except Exception:
                pass

        try:
            flush_timer = QtCore.QTimer(app)
            flush_timer.setInterval(700)
            flush_timer.timeout.connect(_flush_events)
            flush_timer.start()
        except Exception:
            pass
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
