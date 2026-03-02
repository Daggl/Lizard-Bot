"""Controller mixin for per-guild Social Media configuration.

Uses the per-channel model: each platform has a CHANNELS list where every
entry maps a Discord text channel to one or more creators.  Channels are
displayed as individual cards in the UI.
"""

from config.config_io import (config_json_path, load_guild_config,
                              save_json)
from PySide6 import QtWidgets
from services.control_api_client import send_cmd


# ---------------------------------------------------------------------------
# Card helpers
# ---------------------------------------------------------------------------

def _read_channel_cards(cards: list[dict]) -> list[dict]:
    """Read card widgets → CHANNELS list for config."""
    channels: list[dict] = []
    for card in cards:
        creator_raw = (card["creator"].text() or "").strip()
        additional_raw = (card["additional_creators"].text() or "").strip()
        creators: list[str] = []
        if creator_raw:
            creators.append(creator_raw)
        if additional_raw:
            creators.extend([c.strip() for c in additional_raw.split(",") if c.strip()])
        ch_name = (card["channel_name"].text() or "").strip()
        ch_id_raw = (card["channel_id"].text() or "").strip()
        if not ch_id_raw or not ch_id_raw.isdigit():
            continue
        channels.append({
            "CREATORS": creators,
            "CHANNEL_NAME": ch_name,
            "CHANNEL_ID": int(ch_id_raw),
        })
    return channels


def _populate_channel_cards(clear_fn, add_fn, channels: list):
    """Clear existing cards and create new ones from config data."""
    clear_fn()
    if not isinstance(channels, list):
        return
    for entry in channels:
        if not isinstance(entry, dict):
            continue
        card_data = add_fn()
        creators = entry.get("CREATORS", [])
        if isinstance(creators, str):
            creators = [c.strip() for c in creators.split(",") if c.strip()]
        if creators:
            card_data["creator"].setText(creators[0])
            if len(creators) > 1:
                card_data["additional_creators"].setText(", ".join(creators[1:]))
        ch_name = str(entry.get("CHANNEL_NAME", "") or "")
        ch_id = str(entry.get("CHANNEL_ID", "") or "")
        if ch_id == "0":
            ch_id = ""
        card_data["channel_name"].setText(ch_name)
        card_data["channel_id"].setText(ch_id)


class SocialsControllerMixin:
    """Mixin that adds Social Media config load/save to the main window."""

    def _socials_config_path(self):
        return config_json_path(
            self._repo_root, "social_media.json",
            guild_id=getattr(self, "_active_guild_id", None),
        )

    def _load_socials_config(self):
        gid = getattr(self, "_active_guild_id", None)
        cfg = load_guild_config(self._repo_root, "social_media.json", guild_id=gid)
        if not isinstance(cfg, dict):
            cfg = {}

        def _load_platform(section_key, prefix, extra_fields=None):
            """Load one platform section into the UI widgets."""
            try:
                section = cfg.get(section_key, {})
                if not isinstance(section, dict):
                    section = {}

                enabled_chk = getattr(self, f"{prefix}_enabled", None)
                if enabled_chk is not None:
                    enabled_chk.setChecked(bool(section.get("ENABLED", False)))

                clear_fn = getattr(self, f"{prefix}_clear_cards", None)
                add_fn = getattr(self, f"{prefix}_add_card", None)
                if clear_fn and add_fn:
                    _populate_channel_cards(
                        clear_fn, add_fn, section.get("CHANNELS", []),
                    )

                for field_key, widget_attr in (extra_fields or []):
                    widget = getattr(self, widget_attr, None)
                    if widget is None:
                        continue
                    if hasattr(widget, "setText") and not widget.hasFocus():
                        widget.setText(str(section.get(field_key, "") or ""))
            except Exception:
                pass

        _load_platform("TWITCH", "sm_twitch", [])
        _load_platform("YOUTUBE", "sm_youtube", [])
        _load_platform("TWITTER", "sm_twitter", [])
        _load_platform("TIKTOK", "sm_tiktok", [])

    def _save_socials_config(self, data: dict):
        path = self._socials_config_path()
        if not path:
            return
        save_json(path, data or {})

    def _on_reload_after_save_socials(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_socials_config()
                except Exception:
                    pass
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg += "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Create / Pick for channel cards (used by UI tab buttons)
    # -----------------------------------------------------------------

    def _on_social_card_create(self, platform_key: str, card_data: dict):
        """Create a Discord channel via the bot API and fill the card."""
        try:
            gid = getattr(self, "_active_guild_id", None)
            if not gid:
                QtWidgets.QMessageBox.warning(
                    self, "Create Channel",
                    "Keine aktive Guild. Bitte zuerst eine Guild auswählen.",
                )
                return

            creator = (card_data["creator"].text() or "").strip()
            default_name = (
                f"{platform_key.lower()}-{creator.lower()}"
                if creator else f"{platform_key.lower()}-feed"
            )
            name, ok = QtWidgets.QInputDialog.getText(
                self, "Create Channel", "Channel-Name:", text=default_name,
            )
            if not ok or not name.strip():
                return

            resp = send_cmd({
                "action": "create_channel",
                "guild_id": str(gid),
                "channel_name": name.strip(),
                "channel_type": "text",
            }, timeout=10.0)

            if not resp.get("ok"):
                QtWidgets.QMessageBox.warning(
                    self, "Create Channel",
                    f"Channel konnte nicht erstellt werden:\n"
                    f"{resp.get('error', resp)}",
                )
                return

            ch = resp.get("channel", {})
            card_data["channel_name"].setText(ch.get("name", name.strip()))
            card_data["channel_id"].setText(str(ch.get("id", "")))
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self, "Create Channel", f"Fehler: {exc}",
            )

    def _on_social_card_pick(self, platform_key: str, card_data: dict):
        """Pick an existing Discord channel and fill the card."""
        try:
            gid = getattr(self, "_active_guild_id", None)
            if not gid:
                QtWidgets.QMessageBox.warning(
                    self, "Pick Channel",
                    "Keine aktive Guild. Bitte zuerst eine Guild auswählen.",
                )
                return

            resp = send_cmd({"action": "guild_snapshot"}, timeout=8.0)
            if not resp.get("ok"):
                QtWidgets.QMessageBox.warning(self, "Pick", f"Fehler: {resp}")
                return

            guild = None
            for g in (resp.get("guilds") or []):
                if str(g.get("id")) == str(gid):
                    guild = g
                    break
            if not guild:
                guilds = list(resp.get("guilds") or [])
                guild = guilds[0] if guilds else None
            if not guild:
                QtWidgets.QMessageBox.warning(
                    self, "Pick", "Keine Guild-Daten.",
                )
                return

            channels = [
                c for c in (guild.get("channels") or [])
                if "category" not in str(c.get("type", "")).lower()
            ]
            menu = QtWidgets.QMenu(self)
            if not channels:
                menu.addAction("(keine Channels gefunden)").setEnabled(False)
            for ch in channels:
                action = menu.addAction(f"# {ch.get('name', 'unknown')}")
                action.setData((ch.get("id"), ch.get("name", "unknown")))

            chosen = menu.exec(self.cursor().pos())
            if not chosen or not chosen.data():
                return

            ch_id, ch_name = chosen.data()
            card_data["channel_name"].setText(ch_name)
            card_data["channel_id"].setText(str(ch_id))
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self, "Pick Channel", f"Fehler: {exc}",
            )

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------

    def _save_socials_settings(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(
                    self, "Safe Mode",
                    "Nur lesen ist aktiv: Speichern ist deaktiviert.",
                )
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(
                    self, "Safe Mode",
                    "Auto reload ist aus: Speichern ohne Reload.",
                )

            payload = {
                "TWITCH": {
                    "ENABLED": self.sm_twitch_enabled.isChecked(),
                    "CHANNELS": _read_channel_cards(self.sm_twitch_cards),
                },
                "YOUTUBE": {
                    "ENABLED": self.sm_youtube_enabled.isChecked(),
                    "CHANNELS": _read_channel_cards(self.sm_youtube_cards),
                },
                "TWITTER": {
                    "ENABLED": self.sm_twitter_enabled.isChecked(),
                    "CHANNELS": _read_channel_cards(self.sm_twitter_cards),
                },
                "TIKTOK": {
                    "ENABLED": self.sm_tiktok_enabled.isChecked(),
                    "CHANNELS": _read_channel_cards(self.sm_tiktok_cards),
                },
                "CUSTOM": {
                    "ENABLED": False,
                    "CHANNELS": [],
                },
            }
            self._save_socials_config(payload)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_socials,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Save error", str(e))
