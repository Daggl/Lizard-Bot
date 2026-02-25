"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""

import sys
import os
import json
import socket
import html as _html
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
        self.shutdown_btn = QtWidgets.QPushButton("Shutdown Bot")

        for w in (self.ping_btn, self.refresh_btn, self.reload_btn, self.shutdown_btn):
            btn_row.addWidget(w)

        dash_layout.addLayout(btn_row)

        # connect dashboard buttons
        self.ping_btn.clicked.connect(self.on_ping)
        self.refresh_btn.clicked.connect(self.on_refresh)
        self.reload_btn.clicked.connect(self.on_reload)
        # config editor is available as its own tab; dashboard button removed
        self.shutdown_btn.clicked.connect(self.on_shutdown)

        # Dashboard quick summary removed — detailed preview is in the Preview tab

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

        # live rendered preview (message + simple embed look)
        # use QTextBrowser for richer HTML support and better image handling
        self.pv_render = QtWidgets.QTextBrowser()
        self.pv_render.setReadOnly(True)
        self.pv_render.setMinimumHeight(160)
        self.pv_render.setFrameShape(QtWidgets.QFrame.NoFrame)
        # keep the embed styling but make the widget background transparent so the embed HTML controls appearance
        self.pv_render.setStyleSheet("background: transparent; color: #e6e6e6;")
        self.pv_render.setOpenExternalLinks(False)
        pv_layout.addWidget(self.pv_render)

        pv_row = QtWidgets.QHBoxLayout()
        self.pv_save = QtWidgets.QPushButton("Save")
        self.pv_save_reload = QtWidgets.QPushButton("Save + Reload")
        self.pv_refresh = QtWidgets.QPushButton("Refresh Preview")
        pv_row.addStretch()
        pv_row.addWidget(self.pv_refresh)
        pv_row.addWidget(self.pv_save)
        pv_row.addWidget(self.pv_save_reload)
        pv_layout.addLayout(pv_row)

        tabs.addTab(preview_w, "Preview")

        # Rankcard preview tab
        rank_w = QtWidgets.QWidget()
        rank_layout = QtWidgets.QVBoxLayout(rank_w)

        rk_top = QtWidgets.QHBoxLayout()
        self.rk_image = QtWidgets.QLabel()
        self.rk_image.setFixedSize(700, 210)
        self.rk_image.setScaledContents(True)
        rk_top.addWidget(self.rk_image, 0)

        rk_form = QtWidgets.QFormLayout()
        self.rk_name = QtWidgets.QLineEdit()
        self.rk_bg_path = QtWidgets.QLineEdit()
        self.rk_bg_browse = QtWidgets.QPushButton("Choose...")
        hbg = QtWidgets.QHBoxLayout()
        hbg.addWidget(self.rk_bg_path)
        hbg.addWidget(self.rk_bg_browse)
        self.rk_refresh = QtWidgets.QPushButton("Refresh Rankcard")
        rk_form.addRow("Example name:", self.rk_name)
        rk_form.addRow("Background PNG:", hbg)

        rk_row = QtWidgets.QHBoxLayout()
        self.rk_save = QtWidgets.QPushButton("Save")
        self.rk_save_reload = QtWidgets.QPushButton("Save + Reload")
        rk_row.addStretch()
        rk_row.addWidget(self.rk_refresh)
        rk_row.addWidget(self.rk_save)
        rk_row.addWidget(self.rk_save_reload)

        rk_top.addLayout(rk_form, 1)
        rank_layout.addLayout(rk_top)
        # push buttons to bottom
        rank_layout.addStretch()
        rank_layout.addLayout(rk_row)

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
        self.log_timer.timeout.connect(self.tail_logs)
        self.log_timer.start(1000)

        # initialize
        self._log_fp = None
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
            name = self.pv_name.text() or "NewMember"
            r = send_cmd({"action": "banner_preview", "name": name}, timeout=2.0)
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        self.pv_banner.setPixmap(pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
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

    def _choose_banner(self):
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose banner image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.pv_banner_path.setText(path)
                pix = QtGui.QPixmap(path)
                self.pv_banner.setPixmap(pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
        except Exception:
            pass

    def _choose_rank_bg(self):
        try:
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
                try:
                    if banner and os.path.exists(banner):
                        pix = QtGui.QPixmap(banner)
                        try:
                            self.pv_banner.setPixmap(pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
                        except Exception:
                            self.pv_banner.setPixmap(pix)
                        banner_url = f"file:///{os.path.abspath(banner).replace('\\', '/')}"
                    else:
                        self.pv_banner.clear()
                except Exception:
                    try:
                        self.pv_banner.clear()
                    except Exception:
                        pass

            # substitute placeholder safely
            safe_name = _html.escape(name)
            # preserve newlines as <br> and substitute mention
            rendered = _html.escape(message).replace("{mention}", f"<b>@{safe_name}</b>")
            rendered = rendered.replace("\n", "<br>")

            # build Discord-like embed HTML using basic table layout (Qt supports a subset of HTML/CSS)
            # left colored bar, dark embed background, banner image below header
            html = """
<div style="font-family:Segoe UI, Arial; color:#e6e6e6;">
    <table cellpadding="0" cellspacing="0" width="100%" style="background:#2f3136; border-radius:8px;">
        <tr>
            <td width="6" style="background:#5865F2; border-top-left-radius:8px; border-bottom-left-radius:8px;"></td>
            <td style="padding:12px; vertical-align:top;">
                <div style="font-size:10pt; font-weight:700; color:#ffffff; letter-spacing:1px;">Lizard Bot</div>
                <div style="font-size:9pt; color:#b9bbbe; margin-top:4px;">just checked in — welcome <b>@%s</b></div>
            </td>
        </tr>
        <tr><td colspan="2" style="padding:10px 12px 6px 12px; color:#d8d8d8; font-size:10pt; line-height:1.35;">%s</td></tr>
""" % (safe_name, rendered)

            if banner_url:
                # responsive banner using max-width so it fits the preview widget
                html += f"<tr><td colspan=\"2\" style=\"padding:0 12px 12px 12px;\"><img src=\"{banner_url}\" style=\"width:100%; height:auto; border-radius:6px; display:block;\"/></td></tr>"

            # Add a caption row to mimic large title under banner (helps approximate Discord-style composition)
            html += "<tr><td colspan=\"2\" style=\"padding:6px 12px 12px 12px;\">"
            html += "<div style=\"font-size:18pt; font-weight:800; color:#ffffff; margin-bottom:4px;\">WELCOME</div>"
            html += f"<div style=\"font-size:12pt; color:#dcdcdc;\">{safe_name}</div>"
            html += "</td></tr>"

            html += "</table></div>"

            # set HTML into QTextBrowser
            try:
                self.pv_render.setHtml(html)
            except Exception:
                # fallback to plain text
                self.pv_render.setPlainText(_html.unescape(rendered))
        except Exception:
            pass

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
                try:
                    self.pv_render.setText("No welcome config found")
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
                        self.pv_banner.setPixmap(pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
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
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
