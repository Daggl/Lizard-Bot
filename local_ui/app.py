"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""

import sys
import os
import json
import socket
from PySide6 import QtWidgets, QtCore


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


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DC Bot - Local UI")
        self.resize(420, 140)

        self.status_label = QtWidgets.QLabel("Status: unknown")
        self.ping_btn = QtWidgets.QPushButton("Ping")
        self.shutdown_btn = QtWidgets.QPushButton("Shutdown Bot")
        self.refresh_btn = QtWidgets.QPushButton("Refresh Status")
        self.reload_btn = QtWidgets.QPushButton("Reload Cogs")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.status_label)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.ping_btn)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.reload_btn)
        row.addWidget(self.shutdown_btn)
        layout.addLayout(row)

        self.ping_btn.clicked.connect(self.on_ping)
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.shutdown_btn.clicked.connect(self.on_shutdown)
        self.reload_btn.clicked.connect(self.on_reload)

        # poll status every 3 seconds
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.on_refresh)
        self.timer.start(3000)

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


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
