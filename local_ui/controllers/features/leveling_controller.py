import os
import re

from config.config_io import config_json_path, load_json_dict, save_json_merged
from PySide6 import QtCore, QtWidgets


def _natural_sort_text_key(text: str) -> str:
    parts = re.split(r"(\d+)", str(text or ""))
    out = []
    for part in parts:
        if part.isdigit():
            out.append(f"{int(part):010d}")
        else:
            out.append(part.lower())
    return "".join(out)


class _SortableTableItem(QtWidgets.QTableWidgetItem):
    def __init__(self, text: str, sort_key=None):
        super().__init__(str(text))
        if sort_key is not None:
            self.setData(QtCore.Qt.UserRole, sort_key)

    def __lt__(self, other):
        try:
            left = self.data(QtCore.Qt.UserRole)
            right = other.data(QtCore.Qt.UserRole)
            if left is not None and right is not None:
                return left < right
        except Exception:
            pass
        return super().__lt__(other)


class LevelingControllerMixin:
    def _leveling_config_paths(self):
        return config_json_path(self._repo_root, "leveling.json", guild_id=getattr(self, '_active_guild_id', None))

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
        xp_per_message = int(cfg.get("XP_PER_MESSAGE", 15) or 15)
        voice_xp_per_minute = int(cfg.get("VOICE_XP_PER_MINUTE", 10) or 10)
        message_cooldown = int(cfg.get("MESSAGE_COOLDOWN", 30) or 30)
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
            self.lv_xp_per_message.setValue(max(1, xp_per_message))
            self.lv_voice_xp_per_minute.setValue(max(1, voice_xp_per_minute))
            self.lv_message_cooldown.setValue(max(0, message_cooldown))
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
            table.setSortingEnabled(False)
            table.setRowCount(0)
            for level, role in rows:
                row = table.rowCount()
                table.insertRow(row)
                level_item = _SortableTableItem(str(level), int(level))
                table.setItem(row, 0, level_item)
                table.setItem(row, 1, _SortableTableItem(role, str(role).lower()))
            table.setSortingEnabled(True)
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
                    image_value = ""
                    requirements = req
                    if "requirements" in req and isinstance(req.get("requirements"), dict):
                        requirements = req.get("requirements") or {}
                        image_value = str(req.get("image", "") or "").strip()
                    for req_type, req_value in requirements.items():
                        req_type_s = str(req_type or "").strip()
                        try:
                            req_int = int(req_value)
                        except Exception:
                            continue
                        if req_type_s and req_int > 0:
                            rows.append((name, req_type_s, req_int, image_value))
            rows.sort(key=lambda it: (_natural_sort_text_key(it[0]), it[1].lower()))
            table.setSortingEnabled(False)
            table.setRowCount(0)
            for ach_name, req_type, req_val, image_value in rows:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, _SortableTableItem(ach_name, _natural_sort_text_key(ach_name)))
                table.setItem(row, 1, _SortableTableItem(req_type, str(req_type).lower()))
                value_item = _SortableTableItem(str(req_val), int(req_val))
                table.setItem(row, 2, value_item)
                table.setItem(row, 3, _SortableTableItem(image_value, str(image_value).lower()))
            table.setSortingEnabled(True)
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
        grouped_requirements = {}
        grouped_images = {}
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            type_item = table.item(row, 1)
            value_item = table.item(row, 2)
            image_item = table.item(row, 3)
            ach_name = str(name_item.text() if name_item else "").strip()
            req_type = str(type_item.text() if type_item else "").strip()
            req_value_raw = str(value_item.text() if value_item else "").strip()
            image_raw = str(image_item.text() if image_item else "").strip()
            if not ach_name and not req_type and not req_value_raw and not image_raw:
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
            grouped_requirements.setdefault(ach_name, {})[req_type] = req_value
            if image_raw and ach_name not in grouped_images:
                grouped_images[ach_name] = image_raw

        out = {}
        for ach_name, reqs in grouped_requirements.items():
            image_value = str(grouped_images.get(ach_name, "") or "").strip()
            if image_value:
                out[ach_name] = {"requirements": reqs, "image": image_value}
            else:
                out[ach_name] = reqs
        return out

    def on_leveling_add_reward_row(self):
        table = getattr(self, "lv_rewards_table", None)
        if table is None:
            return
        row = table.rowCount()
        table.insertRow(row)
        level_item = _SortableTableItem("1", 1)
        table.setItem(row, 0, level_item)
        table.setItem(row, 1, _SortableTableItem("Role Name", "role name"))
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
        table.setItem(row, 0, _SortableTableItem("Achievement Name", _natural_sort_text_key("Achievement Name")))
        table.setItem(row, 1, _SortableTableItem("messages", "messages"))
        value_item = _SortableTableItem("100", 100)
        table.setItem(row, 2, value_item)
        table.setItem(row, 3, _SortableTableItem("", ""))
        table.setCurrentCell(row, 0)

    def on_leveling_remove_achievement_row(self):
        table = getattr(self, "lv_achievements_table", None)
        if table is None:
            return
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def on_leveling_choose_achievement_image(self):
        table = getattr(self, "lv_achievements_table", None)
        if table is None:
            return
        row = table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Leveling", "Please select an achievement row first.")
            return

        try:
            start_dir = os.path.join(self._repo_root, "assets")
            if not os.path.isdir(start_dir):
                start_dir = self._repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Choose achievement image",
                start_dir,
                "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)",
            )
            if not path:
                return

            try:
                rel = os.path.relpath(path, self._repo_root)
                if not str(rel).startswith(".."):
                    value = rel.replace("\\", "/")
                else:
                    value = path
            except Exception:
                value = path

            item = table.item(row, 3)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                table.setItem(row, 3, item)
            item.setText(value)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Leveling", f"Failed to choose image: {exc}")

    def _save_leveling_settings(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")

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
                "LEVEL_REWARDS": rewards_obj,
                "ACHIEVEMENTS": achievements_obj,
            }

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
