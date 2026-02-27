from PySide6 import QtWidgets

from dialogs.emoji_picker import GuildEmojiPickerDialog


class EmojiControllerMixin:
    def on_open_birthday_emoji_picker(self):
        self._open_server_emoji_picker_for(self.bd_embed_description)

    def on_open_welcome_emoji_picker(self):
        self._open_server_emoji_picker_for(self.pv_message)

    def on_open_leveling_levelup_emoji_picker(self):
        self._open_server_emoji_picker_for(self.lv_levelup_msg)

    def on_open_leveling_achievement_emoji_picker(self):
        self._open_server_emoji_picker_for(self.lv_achievement_msg)

    def on_open_leveling_leading_emoji_picker(self):
        self._open_server_emoji_picker_for(self.lv_emoji_win, replace_text=True)

    def on_open_leveling_trailing_emoji_picker(self):
        self._open_server_emoji_picker_for(self.lv_emoji_heart, replace_text=True)

    def _open_server_emoji_picker_for(self, target_widget, replace_text: bool = False):
        try:
            self._emoji_picker_target = target_widget
            self._emoji_picker_replace_text = bool(replace_text)
            self.send_cmd_async({"action": "guild_snapshot"}, timeout=8.0, cb=self._on_server_emoji_snapshot)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Emoji Picker", f"Failed to request guild snapshot: {e}")

    def _on_server_emoji_snapshot(self, resp: dict):
        try:
            if not isinstance(resp, dict) or not resp.get("ok"):
                QtWidgets.QMessageBox.warning(self, "Emoji Picker", f"Guild snapshot failed: {resp}")
                return

            guilds = list(resp.get("guilds") or [])
            if not guilds:
                QtWidgets.QMessageBox.information(self, "Emoji Picker", "No guilds found from bot snapshot.")
                return

            has_emojis = any(bool(list(g.get("emojis") or [])) for g in guilds)
            if not has_emojis:
                QtWidgets.QMessageBox.information(self, "Emoji Picker", "No custom server emojis found in connected guilds.")
                return

            dlg = GuildEmojiPickerDialog(resp, self)
            if dlg.exec() != QtWidgets.QDialog.Accepted:
                return

            selected = dlg.selected_emoji()
            if not selected:
                return

            target = getattr(self, "_emoji_picker_target", None)
            if target is None:
                target = getattr(self, "bd_embed_description", None)
            if bool(getattr(self, "_emoji_picker_replace_text", False)) and isinstance(target, QtWidgets.QLineEdit):
                target.setText(selected)
            else:
                self._insert_text_into_target(target, selected)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Emoji Picker", f"Failed to open picker: {e}")
        finally:
            self._emoji_picker_replace_text = False
