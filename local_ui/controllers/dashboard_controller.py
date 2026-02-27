import os

from PySide6 import QtWidgets


class DashboardControllerMixin:
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
