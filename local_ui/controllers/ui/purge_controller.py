"""Controller mixin for the Purge tab in the local UI.

Sends a ``purge`` action to the bot control API and displays results.
Polls ``purge_status`` in the background so the user sees live progress.
"""

from PySide6 import QtCore, QtWidgets


class PurgeControllerMixin:
    """Methods wired to Purge-tab widgets."""

    # ---- guild / channel loading ----

    def on_purge_refresh_guilds(self):
        """Fetch guild/channel snapshot from bot and populate combos."""
        try:
            self._set_status("Purge: fetching guilds…")
        except Exception:
            pass
        self.send_cmd_async(
            {"action": "guild_snapshot"},
            timeout=8.0,
            cb=self._on_purge_guild_snapshot,
        )

    def _on_purge_guild_snapshot(self, resp: dict):
        try:
            if not isinstance(resp, dict) or not resp.get("ok"):
                QtWidgets.QMessageBox.warning(self, "Purge", f"Guild snapshot failed: {resp}")
                return

            guilds = list(resp.get("guilds") or [])
            combo = getattr(self, "purge_guild_combo", None)
            if combo is None:
                return

            combo.blockSignals(True)
            combo.clear()
            combo.addItem("— select guild —", None)
            self._purge_guilds_data = guilds
            for g in guilds:
                combo.addItem(
                    f"{g.get('name', 'unknown')}  ({g.get('id', '')})",
                    str(g.get("id", "")),
                )
            combo.blockSignals(False)

            # auto-select first real guild
            if combo.count() > 1:
                combo.setCurrentIndex(1)
                self._on_purge_guild_changed(1)

            try:
                self._set_status("Purge: guilds loaded")
            except Exception:
                pass
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Purge", f"Error: {e}")

    def _on_purge_guild_changed(self, index: int):
        combo = getattr(self, "purge_guild_combo", None)
        ch_combo = getattr(self, "purge_channel_combo", None)
        if combo is None or ch_combo is None:
            return

        guild_id = combo.currentData()
        ch_combo.blockSignals(True)
        ch_combo.clear()
        ch_combo.addItem("— all text channels —", "__ALL__")

        guilds = getattr(self, "_purge_guilds_data", [])
        for g in guilds:
            if str(g.get("id")) == str(guild_id):
                channels = [
                    c for c in (g.get("channels") or [])
                    if str(c.get("type", "")).startswith("TextChannel") or "text" in str(c.get("type", "")).lower()
                ]
                for c in channels:
                    ch_combo.addItem(
                        f"#{c.get('name', 'unknown')}",
                        str(c.get("id", "")),
                    )
                break

        ch_combo.blockSignals(False)

    # ---- execute ----

    def on_purge_execute(self):
        """Validate inputs and send purge request to bot."""
        user_id_text = getattr(self, "purge_user_id", None)
        hours_spin = getattr(self, "purge_hours", None)
        guild_combo = getattr(self, "purge_guild_combo", None)
        channel_combo = getattr(self, "purge_channel_combo", None)

        if user_id_text is None or guild_combo is None:
            return

        user_id = str(user_id_text.text() or "").strip()
        if not user_id or not user_id.isdigit():
            QtWidgets.QMessageBox.warning(self, "Purge", "Please enter a valid numeric User ID.")
            return

        guild_id = guild_combo.currentData()
        if not guild_id:
            QtWidgets.QMessageBox.warning(self, "Purge", "Please select a guild first. Click 'Refresh Guilds'.")
            return

        hours = hours_spin.value() if hours_spin else 24
        channel_id = channel_combo.currentData() if channel_combo else "__ALL__"

        # Confirmation dialog
        scope = "all text channels" if channel_id == "__ALL__" else f"channel {channel_combo.currentText()}"
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Purge",
            f"Delete all messages from user {user_id}\n"
            f"in {scope}\n"
            f"from the last {hours} hour(s)?\n\n"
            "This cannot be undone!",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        req = {
            "action": "purge",
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "hours": int(hours),
        }
        if channel_id != "__ALL__":
            req["channel_id"] = str(channel_id)

        self._purge_set_progress("Starting purge…")
        self._purge_set_ui_enabled(False)
        self.send_cmd_async(req, timeout=10.0, cb=self._on_purge_started)

    def _on_purge_started(self, resp: dict):
        """Called when the bot acknowledges the purge start."""
        try:
            if resp.get("ok"):
                self._purge_set_progress("Purge running… polling for updates")
                self._start_purge_polling()
            else:
                error = resp.get("error", "unknown error")
                self._purge_set_progress(f"Failed: {error}")
                self._purge_set_ui_enabled(True)
                QtWidgets.QMessageBox.warning(self, "Purge", f"Purge failed to start: {error}")
        except Exception as e:
            self._purge_set_progress(f"Error: {e}")
            self._purge_set_ui_enabled(True)

    # ---- progress polling ----

    def _start_purge_polling(self):
        """Start a timer that polls purge_status every 2 seconds."""
        timer = getattr(self, "_purge_poll_timer", None)
        if timer is None:
            timer = QtCore.QTimer(self)
            timer.setInterval(2000)
            timer.timeout.connect(self._poll_purge_status)
            self._purge_poll_timer = timer
        timer.start()

    def _stop_purge_polling(self):
        timer = getattr(self, "_purge_poll_timer", None)
        if timer is not None:
            timer.stop()

    def _poll_purge_status(self):
        self.send_cmd_async(
            {"action": "purge_status"},
            timeout=3.0,
            cb=self._on_purge_status,
        )

    def _on_purge_status(self, resp: dict):
        try:
            if not resp.get("ok"):
                return

            running = resp.get("running", False)
            deleted = resp.get("deleted", 0)
            channel = resp.get("channel", "")
            elapsed = resp.get("elapsed_seconds", 0)
            finished = resp.get("finished", False)
            error = resp.get("error")

            # Format elapsed as mm:ss
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60

            if running:
                self._purge_set_progress(
                    f"🔄  Deleting… {deleted} messages so far  |  "
                    f"Channel: #{channel}  |  {mins:02d}:{secs:02d}"
                )
            elif finished:
                self._stop_purge_polling()
                self._purge_set_ui_enabled(True)
                if error:
                    self._purge_set_progress(f"❌  Error: {error}  ({deleted} deleted, {mins:02d}:{secs:02d})")
                    QtWidgets.QMessageBox.warning(self, "Purge", f"Purge error: {error}\n\n{deleted} messages deleted before error.")
                else:
                    self._purge_set_progress(f"✅  Done — {deleted} messages deleted  ({mins:02d}:{secs:02d})")
                    QtWidgets.QMessageBox.information(self, "Purge", f"Purge complete!\n\n{deleted} message(s) deleted in {mins}m {secs}s.")
                try:
                    self._set_status(f"Purge: {deleted} message(s) deleted")
                except Exception:
                    pass
        except Exception:
            pass

    # ---- UI helpers ----

    def _purge_set_progress(self, text: str):
        """Update the purge progress label."""
        lbl = getattr(self, "purge_progress_label", None)
        if lbl is not None:
            lbl.setText(text)
        try:
            self._set_status(text)
        except Exception:
            pass

    def _purge_set_ui_enabled(self, enabled: bool):
        """Enable/disable purge widgets during a running purge."""
        for name in ("purge_execute_btn", "purge_guild_combo", "purge_channel_combo",
                      "purge_user_id", "purge_hours", "purge_refresh_btn"):
            w = getattr(self, name, None)
            if w is not None:
                w.setEnabled(enabled)
