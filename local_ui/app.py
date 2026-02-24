"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""

import sys
import os
import json
import socket
from PySide6 import QtWidgets, QtCore, QtGui


API_ADDR = ("127.0.0.1", 8765)


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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DC Bot — Local UI")
        self.resize(900, 600)

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
        self.config_btn = QtWidgets.QPushButton("Edit Configs")
        self.shutdown_btn = QtWidgets.QPushButton("Shutdown Bot")

        for w in (self.ping_btn, self.refresh_btn, self.reload_btn, self.config_btn, self.shutdown_btn):
            btn_row.addWidget(w)

        dash_layout.addLayout(btn_row)

        # connect dashboard buttons
        self.ping_btn.clicked.connect(self.on_ping)
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.reload_btn.clicked.connect(self.on_reload)
        self.config_btn.clicked.connect(self.on_edit_configs)
        self.shutdown_btn.clicked.connect(self.on_shutdown)

        # Preview quick card
        self.preview_card = QtWidgets.QGroupBox("Preview")
        self.preview_card.setMinimumHeight(220)
        prev_layout = QtWidgets.QHBoxLayout(self.preview_card)
        self.preview_image = QtWidgets.QLabel()
        self.preview_image.setFixedSize(360, 120)
        self.preview_image.setScaledContents(True)
        prev_layout.addWidget(self.preview_image)
        self.preview_text = QtWidgets.QLabel("No preview available")
        prev_layout.addWidget(self.preview_text)
        dash_layout.addWidget(self.preview_card)

        dash_layout.addStretch()

        tabs.addTab(dash, "Dashboard")

        # Logs tab (live tail)
        logs = QtWidgets.QWidget()
        logs_layout = QtWidgets.QVBoxLayout(logs)
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        logs_layout.addWidget(self.log_text)
        tabs.addTab(logs, "Logs")

        # Config editor tab
        self.cfg_editor = ConfigEditor(self)
        tabs.addTab(self.cfg_editor, "Configs")

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
        self.log_timer.timeout.connect(self.tail_logs)
        self.log_timer.start(1000)

        # initialize
        self._log_fp = None
        self._open_log()
        self.on_refresh()
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
        else:
            self.status_label.setText(f"Status: offline ({r.get('error')})")

    def on_shutdown(self):
        r = send_cmd({"action": "shutdown"})
        if r.get("ok"):
            QtWidgets.QMessageBox.information(self, "Shutdown", "Bot is shutting down")
        else:
            QtWidgets.QMessageBox.warning(self, "Shutdown", f"Failed: {r}")

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
        # try to open repo-level `discord.log` if present
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_path = os.path.join(repo_root, "discord.log")
            if os.path.exists(log_path):
                self._log_fp = open(log_path, "r", encoding="utf-8", errors="ignore")
                # seek to end
                self._log_fp.seek(0, os.SEEK_END)
        except Exception:
            self._log_fp = None

    def tail_logs(self):
        if not self._log_fp:
            return
        try:
            for line in self._log_fp:
                self.log_text.appendPlainText(line.rstrip())
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
                self.preview_text.setText("No welcome config found")
                self.preview_image.clear()
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception:
            cfg = {}

        name = cfg.get("EXAMPLE_NAME", "NewMember")
        rules = cfg.get("RULES_CHANNEL_ID", 0)
        verify = cfg.get("VERIFY_CHANNEL_ID", 0)
        role = cfg.get("ROLE_ID", 0)

        text = f"@{name} — Verify: {verify}\nRules: {rules}\nRole: {role}"
        self.preview_text.setText(text)

        # show banner image if available
        banner = cfg.get("BANNER_PATH") or os.path.join(repo_root, "assets", "welcome.png")
        try:
            if banner and os.path.exists(banner):
                pix = QtGui.QPixmap(banner)
                self.preview_image.setPixmap(pix.scaled(self.preview_image.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
            else:
                self.preview_image.clear()
        except Exception:
            self.preview_image.clear()


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
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
