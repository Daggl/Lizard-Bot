"""Dashboard controller mixin — bot status monitoring, language controls and console polling."""

import os
from urllib import request as _urllib_request

from PySide6 import QtCore, QtGui, QtWidgets


class DashboardControllerMixin:
    """Provides bot status refresh, language guild/language combo management and console polling."""
    def _update_window_icon_from_avatar(self, avatar_url: str):
        try:
            url = str(avatar_url or "").strip()
            if not url:
                return

            if getattr(self, "_window_icon_avatar_url", "") == url:
                return

            req = _urllib_request.Request(url, headers={"User-Agent": "Lizard-UI/1.0"})
            with _urllib_request.urlopen(req, timeout=5) as resp:
                raw = resp.read()

            pix = QtGui.QPixmap()
            if not pix.loadFromData(raw):
                return

            self.setWindowIcon(QtGui.QIcon(pix))
            self._window_icon_avatar_url = url
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
                avatar_url = r.get("avatar_url")
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
                try:
                    self._update_window_icon_from_avatar(avatar_url)
                except Exception:
                    pass
            else:
                self.status_label.setText(f"Status: offline ({(r or {}).get('error')})")
                self._set_monitor_offline()
        finally:
            self._status_inflight = False

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

    def _log_language_event(self, message: str):
        """Write language debug info when UI_DEBUG=1."""
        try:
            self._debug_log(f"[lang] {message}")
        except Exception:
            pass

    # ==================================================
    # LANGUAGE CONTROLS
    # ==================================================

    def request_language_overview(self):
        """Request the language overview from the bot control API."""
        try:
            try:
                if hasattr(self, "_set_status"):
                    self._set_status("Loading languages...")
            except Exception:
                pass
            self._log_language_event("request_language_overview -> languages_get")
            self.send_cmd_async({"action": "languages_get"}, timeout=2.0, cb=self._on_language_overview)
        except Exception:
            self._log_language_event("request_language_overview FAILED to dispatch")
            pass

    def _ensure_language_state(self):
        if not hasattr(self, "_language_overview") or not isinstance(getattr(self, "_language_overview"), dict):
            self._language_overview = {}
        return self._language_overview

    def _on_language_overview(self, resp: dict):
        """Handle the languages_get response — populate combos or schedule retry."""
        self._log_language_event(
            f"_on_language_overview ok={resp.get('ok')} guilds={len(resp.get('guild_details') or [])}"
        )
        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(self, "Languages", f"Failed to load languages: {resp}")
            return
        self._language_overview = resp or {}
        self._populate_language_controls()
        guild_details = self._language_overview.get("guild_details") or []
        if guild_details:
            try:
                self._language_overview_attempts = 0
                if hasattr(self, "_set_status"):
                    self._set_status("Languages loaded")
            except Exception:
                pass
            return

        attempts = int(getattr(self, "_language_overview_attempts", 0) or 0)
        warning_threshold = 5
        if attempts >= warning_threshold and not getattr(self, "_language_overview_warned", False):
            try:
                QtWidgets.QMessageBox.information(
                    self,
                    "Languages",
                    "No guild data available. Make sure the bot is online and try again.",
                )
            except Exception:
                pass
            self._language_overview_warned = True

        delay_ms = min(8000, 1000 * (attempts + 1))
        self._language_overview_attempts = attempts + 1
        self._log_language_event(f"guild list empty; scheduling retry {self._language_overview_attempts} in {delay_ms}ms")
        try:
            QtCore.QTimer.singleShot(delay_ms, self.request_language_overview)
        except Exception:
            try:
                self._log_language_event("QtCore.QTimer.singleShot failed; retrying immediately")
                self.request_language_overview()
            except Exception:
                self._log_language_event("request_language_overview retry failed")
                pass

    def _populate_language_controls(self):
        guild_combo = getattr(self, "language_guild_combo", None)
        lang_combo = getattr(self, "language_combo", None)
        if guild_combo is None or lang_combo is None:
            return
        overview = self._ensure_language_state()
        guild_details = overview.get("guild_details") or []
        self._log_language_event(f"_populate_language_controls guild_count={len(guild_details)}")
        with QtCore.QSignalBlocker(guild_combo):
            guild_combo.clear()
            for guild in guild_details:
                gid = str(guild.get("id") or "")
                if not gid:
                    continue
                name = guild.get("name") or gid
                guild_combo.addItem(f"{name} ({gid})", gid)
        if guild_combo.count() == 0:
            guild_combo.addItem("—", None)
            lang_combo.setEnabled(False)
            with QtCore.QSignalBlocker(lang_combo):
                lang_combo.clear()
                lang_combo.addItem("—", None)
            self._log_language_event("_populate_language_controls found no guilds; added placeholder")
            return
        guild_combo.setCurrentIndex(0)
        self._populate_language_combo()

    def _selected_language_guild_id(self) -> str:
        combo = getattr(self, "language_guild_combo", None)
        if combo is None:
            return ""
        data = combo.currentData()
        return str(data or "").strip()

    def _populate_language_combo(self):
        lang_combo = getattr(self, "language_combo", None)
        if lang_combo is None:
            return
        overview = self._ensure_language_state()
        languages = overview.get("languages") or []
        guild_map = overview.get("guilds") or {}
        default_lang = overview.get("default") or "en"
        selected_guild = self._selected_language_guild_id()
        with QtCore.QSignalBlocker(lang_combo):
            lang_combo.clear()
            for entry in languages:
                code = entry.get("code")
                label = entry.get("label") or code
                if not code:
                    continue
                lang_combo.addItem(label, code)
            if lang_combo.count() == 0:
                lang_combo.addItem("—", None)
                lang_combo.setEnabled(False)
                return
            lang_combo.setEnabled(bool(selected_guild))
            current = guild_map.get(selected_guild, default_lang)
            idx = lang_combo.findData(current)
            if idx < 0:
                idx = 0
            lang_combo.setCurrentIndex(idx)

    def on_language_guild_changed(self, *_args):
        guild_id = self._selected_language_guild_id()
        self._active_guild_id = guild_id
        self._populate_language_combo()
        if hasattr(self, "_reload_guild_configs"):
            self._reload_guild_configs()

    def on_language_selection_changed(self, *_args):
        lang_combo = getattr(self, "language_combo", None)
        if lang_combo is None or not lang_combo.isEnabled():
            return
        guild_id = self._selected_language_guild_id()
        code = lang_combo.currentData()
        if not guild_id or not code:
            return
        try:
            self._set_status(f"Updating language for guild {guild_id}...")
        except Exception:
            pass
        self.send_cmd_async(
            {"action": "languages_set", "guild_id": guild_id, "language": code},
            timeout=2.0,
            cb=lambda resp, gid=guild_id, lang=code: self._on_language_set(gid, lang, resp),
        )

    def _on_language_set(self, guild_id: str, language_code: str, resp: dict):
        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(self, "Languages", f"Failed to update language: {resp}")
            return
        overview = self._ensure_language_state()
        guild_map = overview.get("guilds") or {}
        guild_map[str(guild_id)] = language_code
        overview["guilds"] = guild_map
        try:
            self._set_status("Language updated")
        except Exception:
            pass
