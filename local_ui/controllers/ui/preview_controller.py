import json
import os
import sys

from config.config_io import (config_json_path, global_config_path,
                              load_guild_config, load_json_dict,
                              save_json_merged)
from PySide6 import QtCore, QtGui, QtWidgets
from services.file_ops import (open_tracked_writer, prune_backups,
                               rotate_log_file)

# Add src to path so we can import from the cogs
_src_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from mybot.cogs.welcome.welcome import render_welcome_banner
from mybot.cogs.leveling.rank import render_rankcard


class PreviewControllerMixin:
    def _choose_banner(self):
        try:
            try:
                self._set_status("Banner: choosing image...")
            except Exception:
                pass
            repo_root = self._repo_root
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose banner image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.pv_banner_path.setText(path)
                pix = QtGui.QPixmap(path)
                try:
                    scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    self.pv_banner.setPixmap(scaled)
                except Exception:
                    self.pv_banner.setPixmap(pix)
        except Exception:
            pass

    def _choose_rank_bg(self):
        try:
            try:
                self._set_status("Rank: choosing background...")
            except Exception:
                pass
            repo_root = self._repo_root
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose rank background image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.rk_bg_path.setText(path)
                try:
                    pix = QtGui.QPixmap(path)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
                try:
                    self._save_rank_config({"BG_PATH": path})
                except Exception:
                    pass
        except Exception:
            pass

    def _rank_config_paths(self):
        return config_json_path(self._repo_root, "rank.json", guild_id=getattr(self, '_active_guild_id', None))

    def _welcome_config_path(self):
        """Return the welcome config path, guild-scoped when a guild is selected."""
        return config_json_path(self._repo_root, "welcome.json", guild_id=getattr(self, '_active_guild_id', None))

    def _welcome_config_path_existing(self):
        """Return the welcome config path for the active guild.

        When a guild is selected, returns the guild-specific path (even if
        the file does not exist yet — the caller must handle that).
        When no guild is selected, returns an empty string so the caller
        treats it as "no config".
        """
        gid = getattr(self, '_active_guild_id', None)
        if gid:
            return config_json_path(self._repo_root, "welcome.json", guild_id=gid)
        return ""

    def _ui_settings_path(self):
        return global_config_path(self._repo_root, "local_ui.json")

    def _load_ui_settings(self):
        path = self._ui_settings_path()
        cfg = load_json_dict(path)
        self._ui_settings = cfg if isinstance(cfg, dict) else {}
        channel_id = str(self._ui_settings.get("event_test_channel_id", "") or "").strip()
        try:
            if hasattr(self, "event_test_channel_id"):
                self.event_test_channel_id.setText(channel_id)
        except Exception:
            pass
        try:
            read_only = bool(self._ui_settings.get("safe_read_only", False))
            debug_on = bool(self._ui_settings.get("safe_debug_logging", False))
            auto_reload_off = bool(self._ui_settings.get("safe_auto_reload_off", False))
            for attr, value in (
                ("safe_read_only_chk", read_only),
                ("safe_debug_logging_chk", debug_on),
                ("safe_auto_reload_off_chk", auto_reload_off),
            ):
                chk = getattr(self, attr, None)
                if chk is None:
                    continue
                try:
                    chk.blockSignals(True)
                    chk.setChecked(value)
                finally:
                    chk.blockSignals(False)
            self._apply_safe_debug_logging()
        except Exception:
            pass

    def _save_ui_settings(self, data: dict):
        path = self._ui_settings_path()
        merged = save_json_merged(path, data or {})
        self._ui_settings = merged if isinstance(merged, dict) else dict(data or {})

    def _load_rank_config(self):
        cfg_path = self._rank_config_paths()
        self._rank_config_path = cfg_path
        gid = getattr(self, '_active_guild_id', None)
        cfg = load_guild_config(self._repo_root, "rank.json", guild_id=gid)
        self._rank_config = cfg
        try:
            default_pos = {
                "AVATAR_X": 75,
                "AVATAR_Y": 125,
                "USERNAME_X": 400,
                "USERNAME_Y": 80,
                "LEVEL_X": 400,
                "LEVEL_Y": 200,
                "XP_X": 1065,
                "XP_Y": 270,
                "MESSAGES_X": 400,
                "MESSAGES_Y": 400,
                "VOICE_X": 680,
                "VOICE_Y": 400,
                "ACHIEVEMENTS_X": 980,
                "ACHIEVEMENTS_Y": 400,
                "BAR_X": 400,
                "BAR_Y": 330,
            }

            def g(key, default):
                val = cfg.get(key)
                return default if val is None else val

            text_off_x = int(cfg.get("TEXT_OFFSET_X", 0) or 0)
            text_off_y = int(cfg.get("TEXT_OFFSET_Y", 0) or 0)
            avatar_off_x = int(cfg.get("AVATAR_OFFSET_X", 0) or 0)
            avatar_off_y = int(cfg.get("AVATAR_OFFSET_Y", 0) or 0)

            bg = str(cfg.get("BG_PATH", "") or "")
            if not self.rk_bg_path.hasFocus():
                self.rk_bg_path.setText(bg)
            # Resolve relative paths against repo root
            bg_resolved = bg
            if bg and not os.path.isabs(bg):
                bg_resolved = os.path.join(self._repo_root, bg)
            if bg_resolved and os.path.exists(bg_resolved):
                try:
                    pix = QtGui.QPixmap(bg_resolved)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
            else:
                try:
                    self.rk_image.clear()
                except Exception:
                    pass
            mode_val = str(cfg.get("BG_MODE", "") or "")
            idx = self.rk_bg_mode.findData(mode_val) if mode_val else -1
            self.rk_bg_mode.setCurrentIndex(idx if idx >= 0 else 0)
            self.rk_bg_zoom.setValue(int(cfg.get("BG_ZOOM", 100) or 100))
            self.rk_bg_x.setValue(int(cfg.get("BG_OFFSET_X", 0) or 0))
            self.rk_bg_y.setValue(int(cfg.get("BG_OFFSET_Y", 0) or 0))

            username_font = str(g("USERNAME_FONT", cfg.get("NAME_FONT", "assets/fonts/Poppins-Bold.ttf")) or "")
            info_font = str(cfg.get("INFO_FONT", "assets/fonts/Poppins-Regular.ttf") or "assets/fonts/Poppins-Regular.ttf")
            self._load_font_choices(self.rk_username_font, username_font)
            self._load_font_choices(self.rk_level_font, str(g("LEVEL_FONT", info_font) or info_font))
            self._load_font_choices(self.rk_xp_font, str(g("XP_FONT", info_font) or info_font))
            self._load_font_choices(self.rk_messages_font, str(g("MESSAGES_FONT", info_font) or info_font))
            self._load_font_choices(self.rk_voice_font, str(g("VOICE_FONT", info_font) or info_font))
            self._load_font_choices(self.rk_achievements_font, str(g("ACHIEVEMENTS_FONT", info_font) or info_font))

            self.rk_username_size.setValue(int(g("USERNAME_FONT_SIZE", cfg.get("NAME_FONT_SIZE", 90)) or 90))
            self.rk_level_size.setValue(int(g("LEVEL_FONT_SIZE", cfg.get("INFO_FONT_SIZE", 60)) or 60))
            self.rk_xp_size.setValue(int(g("XP_FONT_SIZE", 33) or 33))
            self.rk_messages_size.setValue(int(g("MESSAGES_FONT_SIZE", 33) or 33))
            self.rk_voice_size.setValue(int(g("VOICE_FONT_SIZE", 33) or 33))
            self.rk_achievements_size.setValue(int(g("ACHIEVEMENTS_FONT_SIZE", 33) or 33))

            self.rk_username_color.setText(str(g("USERNAME_COLOR", cfg.get("NAME_COLOR", "#FFFFFF")) or "#FFFFFF"))
            info_col = str(cfg.get("INFO_COLOR", "#C8C8C8") or "#C8C8C8")
            self.rk_level_color.setText(str(g("LEVEL_COLOR", info_col) or info_col))
            self.rk_xp_color.setText(str(g("XP_COLOR", info_col) or info_col))
            self.rk_messages_color.setText(str(g("MESSAGES_COLOR", info_col) or info_col))
            self.rk_voice_color.setText(str(g("VOICE_COLOR", info_col) or info_col))
            self.rk_achievements_color.setText(str(g("ACHIEVEMENTS_COLOR", info_col) or info_col))

            self.rk_username_x.setValue(int(g("USERNAME_X", default_pos["USERNAME_X"] + text_off_x) or 0))
            self.rk_username_y.setValue(int(g("USERNAME_Y", default_pos["USERNAME_Y"] + text_off_y) or 0))
            self.rk_level_x.setValue(int(g("LEVEL_X", default_pos["LEVEL_X"] + text_off_x) or 0))
            self.rk_level_y.setValue(int(g("LEVEL_Y", default_pos["LEVEL_Y"] + text_off_y) or 0))
            self.rk_xp_x.setValue(int(g("XP_X", default_pos["XP_X"] + text_off_x) or 0))
            self.rk_xp_y.setValue(int(g("XP_Y", default_pos["XP_Y"] + text_off_y) or 0))
            self.rk_messages_x.setValue(int(g("MESSAGES_X", default_pos["MESSAGES_X"] + text_off_x) or 0))
            self.rk_messages_y.setValue(int(g("MESSAGES_Y", default_pos["MESSAGES_Y"] + text_off_y) or 0))
            self.rk_voice_x.setValue(int(g("VOICE_X", default_pos["VOICE_X"] + text_off_x) or 0))
            self.rk_voice_y.setValue(int(g("VOICE_Y", default_pos["VOICE_Y"] + text_off_y) or 0))
            self.rk_achievements_x.setValue(int(g("ACHIEVEMENTS_X", default_pos["ACHIEVEMENTS_X"] + text_off_x) or 0))
            self.rk_achievements_y.setValue(int(g("ACHIEVEMENTS_Y", default_pos["ACHIEVEMENTS_Y"] + text_off_y) or 0))

            self.rk_avatar_x.setValue(int(g("AVATAR_X", default_pos["AVATAR_X"] + avatar_off_x) or 0))
            self.rk_avatar_y.setValue(int(g("AVATAR_Y", default_pos["AVATAR_Y"] + avatar_off_y) or 0))
            self.rk_avatar_size.setValue(int(cfg.get("AVATAR_SIZE", 300) or 300))
            self.rk_bar_x.setValue(int(g("BAR_X", default_pos["BAR_X"]) or default_pos["BAR_X"]))
            self.rk_bar_y.setValue(int(g("BAR_Y", default_pos["BAR_Y"]) or default_pos["BAR_Y"]))
            self.rk_bar_width.setValue(int(cfg.get("BAR_WIDTH", 900) or 900))
            self.rk_bar_height.setValue(int(cfg.get("BAR_HEIGHT", 38) or 38))
            self.rk_bar_bg_color.setText(str(cfg.get("BAR_BG_COLOR", "#323232") or "#323232"))
            self.rk_bar_fill_color.setText(str(cfg.get("BAR_FILL_COLOR", cfg.get("BAR_COLOR", "#8C6EFF")) or "#8C6EFF"))

            name = str(cfg.get("EXAMPLE_NAME", "") or "")
            if not self.rk_name.hasFocus():
                self.rk_name.setText(name)
        except Exception:
            pass

    def _save_rank_config(self, data: dict):
        cfg_path = self._rank_config_paths()
        self._rank_config = save_json_merged(cfg_path, data or {})

    def _save_rank_preview(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")
            data = {}
            name = self.rk_name.text() or None
            bg = self.rk_bg_path.text() or None
            if name:
                data["EXAMPLE_NAME"] = name
            if bg:
                data["BG_PATH"] = bg
            data["BG_MODE"] = self.rk_bg_mode.currentData() or "cover"
            data["BG_ZOOM"] = int(self.rk_bg_zoom.value())
            data["BG_OFFSET_X"] = int(self.rk_bg_x.value())
            data["BG_OFFSET_Y"] = int(self.rk_bg_y.value())

            data["USERNAME_FONT"] = self._resolve_font_combo_path(self.rk_username_font) or "assets/fonts/Poppins-Bold.ttf"
            data["LEVEL_FONT"] = self._resolve_font_combo_path(self.rk_level_font) or "assets/fonts/Poppins-Regular.ttf"
            data["XP_FONT"] = self._resolve_font_combo_path(self.rk_xp_font) or "assets/fonts/Poppins-Regular.ttf"
            data["MESSAGES_FONT"] = self._resolve_font_combo_path(self.rk_messages_font) or "assets/fonts/Poppins-Regular.ttf"
            data["VOICE_FONT"] = self._resolve_font_combo_path(self.rk_voice_font) or "assets/fonts/Poppins-Regular.ttf"
            data["ACHIEVEMENTS_FONT"] = self._resolve_font_combo_path(self.rk_achievements_font) or "assets/fonts/Poppins-Regular.ttf"

            data["USERNAME_FONT_SIZE"] = int(self.rk_username_size.value())
            data["LEVEL_FONT_SIZE"] = int(self.rk_level_size.value())
            data["XP_FONT_SIZE"] = int(self.rk_xp_size.value())
            data["MESSAGES_FONT_SIZE"] = int(self.rk_messages_size.value())
            data["VOICE_FONT_SIZE"] = int(self.rk_voice_size.value())
            data["ACHIEVEMENTS_FONT_SIZE"] = int(self.rk_achievements_size.value())

            data["USERNAME_COLOR"] = (self.rk_username_color.text() or "#FFFFFF").strip()
            data["LEVEL_COLOR"] = (self.rk_level_color.text() or "#C8C8C8").strip()
            data["XP_COLOR"] = (self.rk_xp_color.text() or "#C8C8C8").strip()
            data["MESSAGES_COLOR"] = (self.rk_messages_color.text() or "#C8C8C8").strip()
            data["VOICE_COLOR"] = (self.rk_voice_color.text() or "#C8C8C8").strip()
            data["ACHIEVEMENTS_COLOR"] = (self.rk_achievements_color.text() or "#C8C8C8").strip()

            data["USERNAME_X"] = int(self.rk_username_x.value())
            data["USERNAME_Y"] = int(self.rk_username_y.value())
            data["LEVEL_X"] = int(self.rk_level_x.value())
            data["LEVEL_Y"] = int(self.rk_level_y.value())
            data["XP_X"] = int(self.rk_xp_x.value())
            data["XP_Y"] = int(self.rk_xp_y.value())
            data["MESSAGES_X"] = int(self.rk_messages_x.value())
            data["MESSAGES_Y"] = int(self.rk_messages_y.value())
            data["VOICE_X"] = int(self.rk_voice_x.value())
            data["VOICE_Y"] = int(self.rk_voice_y.value())
            data["ACHIEVEMENTS_X"] = int(self.rk_achievements_x.value())
            data["ACHIEVEMENTS_Y"] = int(self.rk_achievements_y.value())

            data["AVATAR_X"] = int(self.rk_avatar_x.value())
            data["AVATAR_Y"] = int(self.rk_avatar_y.value())
            data["AVATAR_SIZE"] = int(self.rk_avatar_size.value())
            data["BAR_X"] = int(self.rk_bar_x.value())
            data["BAR_Y"] = int(self.rk_bar_y.value())
            data["BAR_WIDTH"] = int(self.rk_bar_width.value())
            data["BAR_HEIGHT"] = int(self.rk_bar_height.value())
            data["BAR_BG_COLOR"] = (self.rk_bar_bg_color.text() or "#323232").strip()
            data["BAR_FILL_COLOR"] = (self.rk_bar_fill_color.text() or "#8C6EFF").strip()
            if data:
                self._save_rank_config(data)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_rank,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Rankcard settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save rankcard settings: {e}")

    def _insert_placeholder(self, text: str):
        self._insert_placeholder_into(self.pv_message, text)

    def _insert_placeholder_into(self, target: QtWidgets.QPlainTextEdit, text: str):
        self._insert_text_into_target(target, text)

    def _insert_text_into_target(self, target, text: str):
        try:
            if isinstance(target, QtWidgets.QPlainTextEdit):
                cur = target.textCursor()
                cur.insertText(text)
                target.setTextCursor(cur)
            elif isinstance(target, QtWidgets.QLineEdit):
                cur_pos = target.cursorPosition()
                cur_txt = target.text() or ""
                target.setText(cur_txt[:cur_pos] + text + cur_txt[cur_pos:])
                target.setCursorPosition(cur_pos + len(text))
            else:
                return
            try:
                self._preview_debounce.start()
            except Exception:
                pass
        except Exception:
            pass

    def _pick_color(self, target: QtWidgets.QLineEdit, title: str = "Choose color"):
        try:
            initial = QtGui.QColor((target.text() or "").strip())
            if not initial.isValid():
                initial = QtGui.QColor("#FFFFFF")
            chosen = QtWidgets.QColorDialog.getColor(initial, self, title)
            if chosen.isValid():
                target.setText(chosen.name().upper())
                try:
                    self._preview_debounce.start()
                except Exception:
                    pass
                try:
                    self._mark_preview_dirty()
                except Exception:
                    pass
        except Exception:
            pass

    def _mark_preview_dirty(self, *_args):
        try:
            if getattr(self, "_preview_syncing", False):
                return
            self._preview_dirty = True
        except Exception:
            pass

    def _selected_title_font_path(self) -> str:
        return self._resolve_font_combo_path(self.pv_title_font)

    def _selected_user_font_path(self) -> str:
        return self._resolve_font_combo_path(self.pv_user_font)

    def _selected_rank_name_font_path(self) -> str:
        return self._resolve_font_combo_path(self.rk_username_font)

    def _selected_rank_info_font_path(self) -> str:
        return self._resolve_font_combo_path(self.rk_level_font)

    def _resolve_font_combo_path(self, combo: QtWidgets.QComboBox) -> str:
        try:
            txt = (combo.currentText() or "").strip()
            txt_l = txt.lower()
            looks_like_path = (
                "/" in txt
                or "\\" in txt
                or txt_l.endswith(".ttf")
                or txt_l.endswith(".otf")
                or txt_l.endswith(".ttc")
            )
            if txt and looks_like_path:
                return txt
        except Exception:
            pass
        try:
            data = combo.currentData()
            if isinstance(data, str) and data.strip():
                return data.strip()
        except Exception:
            pass
        try:
            return (combo.currentText() or "").strip()
        except Exception:
            return ""

    def _load_font_choices(self, combo: QtWidgets.QComboBox, selected_path: str = None):
        try:
            repo_root = self._repo_root
            assets_fonts = os.path.join(repo_root, "assets", "fonts")
            sys_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
            exts = (".ttf", ".otf", ".ttc")

            font_paths = []
            for base_dir, source in ((assets_fonts, "assets"), (sys_fonts, "system")):
                if not os.path.isdir(base_dir):
                    continue
                try:
                    for name in os.listdir(base_dir):
                        if not name.lower().endswith(exts):
                            continue
                        full = os.path.join(base_dir, name)
                        if os.path.isfile(full):
                            font_paths.append((full, source))
                except Exception:
                    pass

            dedup = {}
            for full, source in font_paths:
                key = os.path.abspath(full).lower()
                if key not in dedup:
                    dedup[key] = (full, source)

            items = []
            for _, (full, source) in dedup.items():
                label = f"{os.path.splitext(os.path.basename(full))[0]} ({source})"
                items.append((label, full))

            items.sort(key=lambda it: it[0].lower())

            current_text = ""
            try:
                current_text = combo.currentText() or ""
            except Exception:
                pass

            desired = (selected_path or "").strip() or current_text.strip()

            self._preview_syncing = True
            try:
                combo.blockSignals(True)
                combo.clear()
                self._title_font_lookup = {}
                for label, full in items:
                    combo.addItem(label, full)
                    self._title_font_lookup[label] = full

                if desired:
                    idx = combo.findData(desired)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    else:
                        combo.setEditText(desired)
            finally:
                try:
                    combo.blockSignals(False)
                except Exception:
                    pass
                self._preview_syncing = False
        except Exception:
            pass

    def _load_title_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.pv_title_font, selected_path)

    def _load_user_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.pv_user_font, selected_path)

    def _load_rank_name_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.rk_username_font, selected_path)

    def _load_rank_info_font_choices(self, selected_path: str = None):
        for combo in (
            self.rk_level_font,
            self.rk_xp_font,
            self.rk_messages_font,
            self.rk_voice_font,
            self.rk_achievements_font,
        ):
            self._load_font_choices(combo, selected_path)

    def _prune_backups(self, target_path: str, keep: int = 5):
        prune_backups(target_path, keep=keep)

    def _rotate_log_file(self, log_path: str, max_bytes: int = 2_000_000, keep: int = 5):
        rotate_log_file(log_path, max_bytes=max_bytes, keep=keep)

    def _open_tracked_writer(self, header: str):
        self._tracked_fp = open_tracked_writer(
            self._repo_root,
            getattr(self, "_tracked_fp", None),
            header,
        )

    def _save_preview(self, reload_after: bool = False):
        try:
            if self._is_safe_read_only():
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Nur lesen ist aktiv: Speichern ist deaktiviert.")
                return
            if reload_after and self._is_safe_auto_reload_off():
                reload_after = False
                QtWidgets.QMessageBox.information(self, "Safe Mode", "Auto reload ist aus: Speichern ohne Reload.")
            try:
                self._set_status("Preview: saving...")
            except Exception:
                pass
            repo_root = self._repo_root
            cfg_path = self._welcome_config_path()
            # Read existing config from guild-specific file or fall back to global
            existing_path = self._welcome_config_path_existing()
            try:
                with open(existing_path, "r", encoding="utf-8") as fh:
                    cfg = json.load(fh)
            except Exception:
                cfg = {}

            cfg["EXAMPLE_NAME"] = self.pv_name.text() or cfg.get("EXAMPLE_NAME", "NewMember")
            cfg["BG_MODE"] = self.pv_bg_mode.currentData() or cfg.get("BG_MODE", "cover")
            cfg["BG_ZOOM"] = int(self.pv_bg_zoom.value())
            cfg["BG_OFFSET_X"] = int(self.pv_bg_x.value())
            cfg["BG_OFFSET_Y"] = int(self.pv_bg_y.value())
            cfg["BANNER_TITLE"] = self.pv_title.text() or cfg.get("BANNER_TITLE", "WELCOME")
            cfg["OFFSET_X"] = int(self.pv_avatar_x.value())
            cfg["OFFSET_Y"] = int(self.pv_avatar_y.value())
            cfg["AVATAR_SIZE"] = int(self.pv_avatar_size.value())
            cfg["TITLE_FONT_SIZE"] = int(self.pv_title_size.value())
            cfg["USERNAME_FONT_SIZE"] = int(self.pv_user_size.value())
            cfg["TITLE_COLOR"] = (self.pv_title_color.text() or cfg.get("TITLE_COLOR", "#FFFFFF")).strip()
            cfg["USERNAME_COLOR"] = (self.pv_user_color.text() or cfg.get("USERNAME_COLOR", "#E6E6E6")).strip()
            cfg["TITLE_OFFSET_X"] = int(self.pv_title_x.value())
            cfg["TITLE_OFFSET_Y"] = int(self.pv_title_y.value())
            cfg["USERNAME_OFFSET_X"] = int(self.pv_user_x.value())
            cfg["USERNAME_OFFSET_Y"] = int(self.pv_user_y.value())
            cfg["TEXT_OFFSET_X"] = int(self.pv_text_x.value())
            cfg["TEXT_OFFSET_Y"] = int(self.pv_text_y.value())

            selected_title_font = self._selected_title_font_path() or cfg.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")
            saved_title_font = selected_title_font
            try:
                if selected_title_font and os.path.exists(selected_title_font):
                    assets_fonts = os.path.join(repo_root, "assets", "fonts")
                    os.makedirs(assets_fonts, exist_ok=True)
                    base_name = os.path.basename(selected_title_font)
                    target_path = os.path.join(assets_fonts, base_name)
                    import shutil

                    if os.path.abspath(selected_title_font) != os.path.abspath(target_path):
                        shutil.copy2(selected_title_font, target_path)
                    saved_title_font = os.path.join("assets", "fonts", base_name).replace("\\", "/")
            except Exception:
                pass

            cfg["FONT_WELCOME"] = saved_title_font

            selected_user_font = self._selected_user_font_path() or cfg.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")
            saved_user_font = selected_user_font
            try:
                if selected_user_font and os.path.exists(selected_user_font):
                    assets_fonts = os.path.join(repo_root, "assets", "fonts")
                    os.makedirs(assets_fonts, exist_ok=True)
                    base_name = os.path.basename(selected_user_font)
                    target_path = os.path.join(assets_fonts, base_name)
                    import shutil

                    if os.path.abspath(selected_user_font) != os.path.abspath(target_path):
                        shutil.copy2(selected_user_font, target_path)
                    saved_user_font = os.path.join("assets", "fonts", base_name).replace("\\", "/")
            except Exception:
                pass

            cfg["FONT_USERNAME"] = saved_user_font

            banner_path_input = self.pv_banner_path.text() or cfg.get("BANNER_PATH", "assets/welcome.png")
            # Resolve relative path for existence check
            banner_path_check = banner_path_input
            if banner_path_input and not os.path.isabs(banner_path_input):
                banner_path_check = os.path.join(repo_root, banner_path_input)
            banner_path_saved = banner_path_input
            try:
                if banner_path_check and os.path.exists(banner_path_check):
                    assets_dir = os.path.join(repo_root, "assets")
                    os.makedirs(assets_dir, exist_ok=True)
                    _, ext = os.path.splitext(banner_path_input)
                    ext = ext.lower() if ext else ".png"
                    if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
                        ext = ".png"
                    target_name = f"welcome_custom{ext}"
                    target_path = os.path.join(assets_dir, target_name)
                    import shutil

                    shutil.copy2(banner_path_check, target_path)
                    banner_path_saved = os.path.join("assets", target_name).replace("\\", "/")
                    self.pv_banner_path.setText(banner_path_saved)
            except Exception:
                pass

            cfg["BANNER_PATH"] = banner_path_saved or cfg.get("BANNER_PATH", "assets/welcome.png")
            new_msg = self.pv_message.toPlainText()
            if new_msg and new_msg.strip():
                cfg["WELCOME_MESSAGE"] = new_msg
            else:
                cfg["WELCOME_MESSAGE"] = cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", ""))

            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            try:
                if os.path.exists(cfg_path):
                    import shutil
                    import time

                    bak = cfg_path + ".bak." + str(int(time.time()))
                    shutil.copy2(cfg_path, bak)
                    self._prune_backups(cfg_path, keep=5)
            except Exception:
                pass
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2, ensure_ascii=False)

            self._preview_dirty = False

            try:
                self.update_preview()
            except Exception:
                pass

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_preview,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Preview settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save preview settings: {e}")

    def _apply_live_preview(self):
        """Render full welcome banner and rankcard preview locally."""
        # Welcome banner preview - full local rendering
        try:
            name = self.pv_name.text() or "NewMember"
            banner_path = self.pv_banner_path.text() or ""
            message = self.pv_message.toPlainText() or "Welcome {mention}!"

            # Resolve relative paths
            if banner_path and not os.path.isabs(banner_path):
                banner_path = os.path.join(self._repo_root, banner_path)

            # Get font paths
            title_font = self._selected_title_font_path() or os.path.join(self._repo_root, "assets/fonts/Poppins-Bold.ttf")
            user_font = self._selected_user_font_path() or os.path.join(self._repo_root, "assets/fonts/Poppins-Regular.ttf")

            # Render full welcome banner
            png_data = render_welcome_banner(
                banner_path=banner_path,
                username=name,
                title=self.pv_title.text() or "WELCOME",
                avatar_bytes=None,
                bg_mode=self.pv_bg_mode.currentData() or "cover",
                bg_zoom=int(self.pv_bg_zoom.value()),
                bg_offset_x=int(self.pv_bg_x.value()),
                bg_offset_y=int(self.pv_bg_y.value()),
                font_welcome_path=title_font,
                font_username_path=user_font,
                title_font_size=int(self.pv_title_size.value()) or 140,
                username_font_size=int(self.pv_user_size.value()) or 64,
                title_color=self.pv_title_color.text() or "#FFFFFF",
                username_color=self.pv_user_color.text() or "#E6E6E6",
                title_offset_x=int(self.pv_title_x.value()),
                title_offset_y=int(self.pv_title_y.value()),
                username_offset_x=int(self.pv_user_x.value()),
                username_offset_y=int(self.pv_user_y.value()),
                text_offset_x=int(self.pv_text_x.value()),
                text_offset_y=int(self.pv_text_y.value()),
                offset_x=int(self.pv_avatar_x.value()),
                offset_y=int(self.pv_avatar_y.value()),
                avatar_size=int(self.pv_avatar_size.value()) if hasattr(self, 'pv_avatar_size') else 360,
            )

            # Display the rendered banner
            pix = QtGui.QPixmap()
            if pix.loadFromData(png_data):
                scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.pv_banner.setPixmap(scaled)
            else:
                self.pv_banner.clear()

            # Update tooltip with rendered message
            rendered = message.replace("{mention}", f"@{name}")
            self.pv_banner.setToolTip(rendered)
        except Exception as e:
            # Fallback: just show raw image
            try:
                banner_path = self.pv_banner_path.text() or ""
                if banner_path and not os.path.isabs(banner_path):
                    banner_path = os.path.join(self._repo_root, banner_path)
                if banner_path and os.path.exists(banner_path):
                    pix = QtGui.QPixmap(banner_path)
                    scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    self.pv_banner.setPixmap(scaled)
                else:
                    self.pv_banner.clear()
            except Exception:
                self.pv_banner.clear()

        # Rankcard preview - full local rendering
        try:
            rk_name = self.rk_name.text() or "NewMember"
            rk_bg = self.rk_bg_path.text() or ""

            if rk_bg and not os.path.isabs(rk_bg):
                rk_bg = os.path.join(self._repo_root, rk_bg)

            # Get font paths
            username_font = self._resolve_font_combo_path(self.rk_username_font) or "assets/fonts/Poppins-Bold.ttf"
            level_font = self._resolve_font_combo_path(self.rk_level_font) or "assets/fonts/Poppins-Regular.ttf"
            xp_font = self._resolve_font_combo_path(self.rk_xp_font) or "assets/fonts/Poppins-Regular.ttf"
            messages_font = self._resolve_font_combo_path(self.rk_messages_font) or "assets/fonts/Poppins-Regular.ttf"
            voice_font = self._resolve_font_combo_path(self.rk_voice_font) or "assets/fonts/Poppins-Regular.ttf"
            achievements_font = self._resolve_font_combo_path(self.rk_achievements_font) or "assets/fonts/Poppins-Regular.ttf"

            # Render full rankcard
            png_data = render_rankcard(
                bg_path=rk_bg,
                username=rk_name,
                level=5,  # Example values for preview
                xp=350,
                xp_needed=500,
                messages=128,
                voice_minutes=45,
                achievements_count=3,
                avatar_bytes=None,
                bg_mode=self.rk_bg_mode.currentData() or "cover",
                bg_zoom=int(self.rk_bg_zoom.value()),
                bg_offset_x=int(self.rk_bg_x.value()),
                bg_offset_y=int(self.rk_bg_y.value()),
                avatar_x=int(self.rk_avatar_x.value()) if hasattr(self, 'rk_avatar_x') else 75,
                avatar_y=int(self.rk_avatar_y.value()) if hasattr(self, 'rk_avatar_y') else 125,
                avatar_size=int(self.rk_avatar_size.value()) if hasattr(self, 'rk_avatar_size') else 300,
                username_x=int(self.rk_username_x.value()) if hasattr(self, 'rk_username_x') else 400,
                username_y=int(self.rk_username_y.value()) if hasattr(self, 'rk_username_y') else 80,
                username_font=username_font,
                username_font_size=int(self.rk_username_size.value()) if hasattr(self, 'rk_username_size') else 90,
                username_color=self.rk_username_color.text() if hasattr(self, 'rk_username_color') else "#FFFFFF",
                level_x=int(self.rk_level_x.value()) if hasattr(self, 'rk_level_x') else 400,
                level_y=int(self.rk_level_y.value()) if hasattr(self, 'rk_level_y') else 200,
                level_font=level_font,
                level_font_size=int(self.rk_level_size.value()) if hasattr(self, 'rk_level_size') else 60,
                level_color=self.rk_level_color.text() if hasattr(self, 'rk_level_color') else "#C8C8C8",
                xp_x=int(self.rk_xp_x.value()) if hasattr(self, 'rk_xp_x') else 1065,
                xp_y=int(self.rk_xp_y.value()) if hasattr(self, 'rk_xp_y') else 270,
                xp_font=xp_font,
                xp_font_size=int(self.rk_xp_size.value()) if hasattr(self, 'rk_xp_size') else 33,
                xp_color=self.rk_xp_color.text() if hasattr(self, 'rk_xp_color') else "#C8C8C8",
                bar_x=int(self.rk_bar_x.value()) if hasattr(self, 'rk_bar_x') else 400,
                bar_y=int(self.rk_bar_y.value()) if hasattr(self, 'rk_bar_y') else 330,
                bar_width=int(self.rk_bar_width.value()) if hasattr(self, 'rk_bar_width') else 900,
                bar_height=int(self.rk_bar_height.value()) if hasattr(self, 'rk_bar_height') else 38,
                bar_bg_color=self.rk_bar_bg_color.text() if hasattr(self, 'rk_bar_bg_color') else "#323232",
                bar_fill_color=self.rk_bar_fill_color.text() if hasattr(self, 'rk_bar_fill_color') else "#8C6EFF",
                messages_x=int(self.rk_messages_x.value()) if hasattr(self, 'rk_messages_x') else 400,
                messages_y=int(self.rk_messages_y.value()) if hasattr(self, 'rk_messages_y') else 400,
                messages_font=messages_font,
                messages_font_size=int(self.rk_messages_size.value()) if hasattr(self, 'rk_messages_size') else 33,
                messages_color=self.rk_messages_color.text() if hasattr(self, 'rk_messages_color') else "#C8C8C8",
                voice_x=int(self.rk_voice_x.value()) if hasattr(self, 'rk_voice_x') else 680,
                voice_y=int(self.rk_voice_y.value()) if hasattr(self, 'rk_voice_y') else 400,
                voice_font=voice_font,
                voice_font_size=int(self.rk_voice_size.value()) if hasattr(self, 'rk_voice_size') else 33,
                voice_color=self.rk_voice_color.text() if hasattr(self, 'rk_voice_color') else "#C8C8C8",
                achievements_x=int(self.rk_achievements_x.value()) if hasattr(self, 'rk_achievements_x') else 980,
                achievements_y=int(self.rk_achievements_y.value()) if hasattr(self, 'rk_achievements_y') else 400,
                achievements_font=achievements_font,
                achievements_font_size=int(self.rk_achievements_size.value()) if hasattr(self, 'rk_achievements_size') else 33,
                achievements_color=self.rk_achievements_color.text() if hasattr(self, 'rk_achievements_color') else "#C8C8C8",
            )

            # Display the rendered rankcard
            pix = QtGui.QPixmap()
            if pix.loadFromData(png_data):
                scaled = pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.rk_image.setPixmap(scaled)
            else:
                self.rk_image.clear()
        except Exception as e:
            # Fallback: just show raw background
            try:
                rk_bg = self.rk_bg_path.text() or ""
                if rk_bg and not os.path.isabs(rk_bg):
                    rk_bg = os.path.join(self._repo_root, rk_bg)
                if rk_bg and os.path.exists(rk_bg):
                    pix = QtGui.QPixmap(rk_bg)
                    scaled = pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    self.rk_image.setPixmap(scaled)
                else:
                    self.rk_image.clear()
            except Exception:
                self.rk_image.clear()

    def on_refresh_preview_local(self):
        """Refresh preview using local rendering (no bot required)."""
        try:
            self._set_status("Refreshing preview locally...")
        except Exception:
            pass
        self._apply_live_preview()
        try:
            self._set_status("Preview refreshed")
        except Exception:
            pass

    def update_preview(self):
        try:
            repo_root = self._repo_root
            gid = getattr(self, '_active_guild_id', None)
            cfg_path = self._welcome_config_path_existing()
            if not cfg_path or not os.path.exists(cfg_path):
                try:
                    if gid:
                        self.status_label.setText(f"Keine Welcome-Config für diese Guild — speichere, um eine zu erstellen")
                    else:
                        self.status_label.setText("No welcome config found")
                    self.pv_banner.clear()
                except Exception:
                    pass
                # Clear all welcome fields so the user sees empty state
                try:
                    self._preview_syncing = True
                    self.pv_name.setText("")
                    self.pv_banner_path.setText("")
                    self.pv_title.setText("")
                    self.pv_title_size.setValue(0)
                    self.pv_user_size.setValue(0)
                    self.pv_title_color.setText("")
                    self.pv_user_color.setText("")
                    self.pv_bg_zoom.setValue(0)
                    self.pv_bg_x.setValue(0)
                    self.pv_bg_y.setValue(0)
                    self.pv_title_x.setValue(0)
                    self.pv_title_y.setValue(0)
                    self.pv_user_x.setValue(0)
                    self.pv_user_y.setValue(0)
                    self.pv_text_x.setValue(0)
                    self.pv_text_y.setValue(0)
                    self.pv_avatar_x.setValue(0)
                    self.pv_avatar_y.setValue(0)
                    self.pv_message.setPlainText("")
                finally:
                    self._preview_syncing = False
                    try:
                        self._preview_debounce.stop()
                    except Exception:
                        pass
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception:
            cfg = {}

        banner = cfg.get("BANNER_PATH") or os.path.join(repo_root, "assets", "welcome.png")
        # Resolve relative banner paths against repo root
        if banner and not os.path.isabs(banner):
            banner = os.path.join(repo_root, banner)
        try:
            if getattr(self, "_preview_banner_data_url", None):
                pass
            else:
                if banner and os.path.exists(banner):
                    pix = QtGui.QPixmap(banner)
                    try:
                        scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
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

        try:
            if not getattr(self, "_preview_dirty", False):
                self._preview_syncing = True
                try:
                    if not self.pv_name.hasFocus():
                        self.pv_name.setText(str(cfg.get("EXAMPLE_NAME", "") or ""))
                    if not self.pv_banner_path.hasFocus():
                        self.pv_banner_path.setText(str(cfg.get("BANNER_PATH", "") or ""))
                    if not self.pv_bg_mode.hasFocus():
                        mode_val = str(cfg.get("BG_MODE", "") or "")
                        idx = self.pv_bg_mode.findData(mode_val) if mode_val else -1
                        self.pv_bg_mode.setCurrentIndex(idx if idx >= 0 else 0)
                    if not self.pv_bg_zoom.hasFocus():
                        self.pv_bg_zoom.setValue(int(cfg.get("BG_ZOOM", 0) or 0))
                    if not self.pv_bg_x.hasFocus():
                        self.pv_bg_x.setValue(int(cfg.get("BG_OFFSET_X", 0) or 0))
                    if not self.pv_bg_y.hasFocus():
                        self.pv_bg_y.setValue(int(cfg.get("BG_OFFSET_Y", 0) or 0))
                    if not self.pv_title.hasFocus():
                        self.pv_title.setText(str(cfg.get("BANNER_TITLE", "") or ""))
                    if not self.pv_title_font.hasFocus():
                        self._load_title_font_choices(str(cfg.get("FONT_WELCOME", "") or ""))
                    if not self.pv_user_font.hasFocus():
                        self._load_user_font_choices(str(cfg.get("FONT_USERNAME", "") or ""))
                    if not self.pv_title_size.hasFocus():
                        self.pv_title_size.setValue(int(cfg.get("TITLE_FONT_SIZE", 0) or 0))
                    if not self.pv_user_size.hasFocus():
                        self.pv_user_size.setValue(int(cfg.get("USERNAME_FONT_SIZE", 0) or 0))
                    if not self.pv_title_color.hasFocus():
                        self.pv_title_color.setText(str(cfg.get("TITLE_COLOR", "") or ""))
                    if not self.pv_user_color.hasFocus():
                        self.pv_user_color.setText(str(cfg.get("USERNAME_COLOR", "") or ""))
                    if not self.pv_title_x.hasFocus():
                        self.pv_title_x.setValue(int(cfg.get("TITLE_OFFSET_X", 0) or 0))
                    if not self.pv_title_y.hasFocus():
                        self.pv_title_y.setValue(int(cfg.get("TITLE_OFFSET_Y", 0) or 0))
                    if not self.pv_user_x.hasFocus():
                        self.pv_user_x.setValue(int(cfg.get("USERNAME_OFFSET_X", 0) or 0))
                    if not self.pv_user_y.hasFocus():
                        self.pv_user_y.setValue(int(cfg.get("USERNAME_OFFSET_Y", 0) or 0))
                    if not self.pv_text_x.hasFocus():
                        self.pv_text_x.setValue(int(cfg.get("TEXT_OFFSET_X", 0) or 0))
                    if not self.pv_text_y.hasFocus():
                        self.pv_text_y.setValue(int(cfg.get("TEXT_OFFSET_Y", 0) or 0))
                    if not self.pv_avatar_x.hasFocus():
                        self.pv_avatar_x.setValue(int(cfg.get("OFFSET_X", 0) or 0))
                    if not self.pv_avatar_y.hasFocus():
                        self.pv_avatar_y.setValue(int(cfg.get("OFFSET_Y", 0) or 0))
                    if not self.pv_avatar_size.hasFocus():
                        self.pv_avatar_size.setValue(int(cfg.get("AVATAR_SIZE", 360) or 360))

                    welcome_msg = cfg.get("WELCOME_MESSAGE")
                    if not self.pv_message.hasFocus():
                        msg_text = str(welcome_msg) if welcome_msg else ""
                        try:
                            self.pv_message.setPlainText(msg_text)
                        except Exception:
                            pass
                finally:
                    self._preview_syncing = False
                    # Cancel any debounce timer that was started by widget
                    # textChanged signals during the sync — we already called
                    # _apply_live_preview below so there is nothing to debounce.
                    try:
                        self._preview_debounce.stop()
                    except Exception:
                        pass

            try:
                self._apply_live_preview()
            except Exception:
                pass
        except Exception:
            pass

    def _load_welcome_message_from_file(self):
        try:
            repo_root = self._repo_root
            cfg_path = self._welcome_config_path_existing()
            if not os.path.exists(cfg_path):
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            msg = str(cfg.get("WELCOME_MESSAGE", "") or "")
            try:
                self._preview_syncing = True
                self.pv_message.setPlainText(msg)
            except Exception:
                pass
            finally:
                self._preview_syncing = False
            self._preview_dirty = False
            try:
                self._apply_live_preview()
            except Exception:
                pass
        except Exception:
            pass
