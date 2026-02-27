import json
import os

from PySide6 import QtWidgets, QtCore, QtGui

from config.config_io import config_json_path, load_json_dict, save_json_merged
from services.file_ops import open_tracked_writer, prune_backups, rotate_log_file


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
        return config_json_path(self._repo_root, "rank.json")

    def _ui_settings_path(self):
        return config_json_path(self._repo_root, "local_ui.json")

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
        cfg = load_json_dict(cfg_path)
        self._rank_config = cfg
        try:
            bg = cfg.get("BG_PATH")
            if bg and (not self.rk_bg_path.text()):
                self.rk_bg_path.setText(str(bg))
                try:
                    pix = QtGui.QPixmap(bg)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
            mode_val = str(cfg.get("BG_MODE", "cover") or "cover")
            idx = self.rk_bg_mode.findData(mode_val)
            self.rk_bg_mode.setCurrentIndex(idx if idx >= 0 else 0)
            self.rk_bg_zoom.setValue(int(cfg.get("BG_ZOOM", 100) or 100))
            self.rk_bg_x.setValue(int(cfg.get("BG_OFFSET_X", 0) or 0))
            self.rk_bg_y.setValue(int(cfg.get("BG_OFFSET_Y", 0) or 0))
            self._load_rank_name_font_choices(str(cfg.get("NAME_FONT", "assets/fonts/Poppins-Bold.ttf")))
            self._load_rank_info_font_choices(str(cfg.get("INFO_FONT", "assets/fonts/Poppins-Regular.ttf")))
            self.rk_name_size.setValue(int(cfg.get("NAME_FONT_SIZE", 60) or 60))
            self.rk_info_size.setValue(int(cfg.get("INFO_FONT_SIZE", 40) or 40))
            self.rk_name_color.setText(str(cfg.get("NAME_COLOR", "#FFFFFF") or "#FFFFFF"))
            self.rk_info_color.setText(str(cfg.get("INFO_COLOR", "#C8C8C8") or "#C8C8C8"))
            self.rk_text_x.setValue(int(cfg.get("TEXT_OFFSET_X", 0) or 0))
            self.rk_text_y.setValue(int(cfg.get("TEXT_OFFSET_Y", 0) or 0))
            name = cfg.get("EXAMPLE_NAME")
            if name and (not self.rk_name.text()):
                try:
                    self.rk_name.setText(str(name))
                except Exception:
                    pass
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
            data["NAME_FONT"] = self._selected_rank_name_font_path() or "assets/fonts/Poppins-Bold.ttf"
            data["INFO_FONT"] = self._selected_rank_info_font_path() or "assets/fonts/Poppins-Regular.ttf"
            data["NAME_FONT_SIZE"] = int(self.rk_name_size.value())
            data["INFO_FONT_SIZE"] = int(self.rk_info_size.value())
            data["NAME_COLOR"] = (self.rk_name_color.text() or "#FFFFFF").strip()
            data["INFO_COLOR"] = (self.rk_info_color.text() or "#C8C8C8").strip()
            data["TEXT_OFFSET_X"] = int(self.rk_text_x.value())
            data["TEXT_OFFSET_Y"] = int(self.rk_text_y.value())
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
        return self._resolve_font_combo_path(self.rk_name_font)

    def _selected_rank_info_font_path(self) -> str:
        return self._resolve_font_combo_path(self.rk_info_font)

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
        self._load_font_choices(self.rk_name_font, selected_path)

    def _load_rank_info_font_choices(self, selected_path: str = None):
        self._load_font_choices(self.rk_info_font, selected_path)

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
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as fh:
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
            banner_path_saved = banner_path_input
            try:
                if banner_path_input and os.path.exists(banner_path_input):
                    assets_dir = os.path.join(repo_root, "assets")
                    os.makedirs(assets_dir, exist_ok=True)
                    _, ext = os.path.splitext(banner_path_input)
                    ext = ext.lower() if ext else ".png"
                    if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
                        ext = ".png"
                    target_name = f"welcome_custom{ext}"
                    target_path = os.path.join(assets_dir, target_name)
                    import shutil

                    shutil.copy2(banner_path_input, target_path)
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
                    import shutil, time

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
        try:
            name = self.pv_name.text() or "NewMember"
            banner = self.pv_banner_path.text() or ""
            message = self.pv_message.toPlainText() or "Welcome {mention}!"

            banner_url = getattr(self, "_preview_banner_data_url", None) or ""
            if banner_url:
                pass
            else:
                if banner and os.path.exists(banner):
                    try:
                        pix = QtGui.QPixmap(banner)
                        try:
                            scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                            self.pv_banner.setPixmap(scaled)
                        except Exception:
                            self.pv_banner.setPixmap(pix)
                    except Exception:
                        try:
                            self.pv_banner.clear()
                        except Exception:
                            pass
                    banner_url = f"file:///{os.path.abspath(banner).replace('\\', '/')}"
                else:
                    try:
                        self.pv_banner.clear()
                    except Exception:
                        pass

            rendered = message.replace("{mention}", f"@{name}")
            try:
                self.pv_banner.setToolTip(rendered)
            except Exception:
                pass
        except Exception:
            pass

    def update_preview(self):
        try:
            repo_root = self._repo_root
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            if not os.path.exists(cfg_path):
                try:
                    self.status_label.setText("No welcome config found")
                    self.pv_banner.clear()
                except Exception:
                    pass
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception:
            cfg = {}

        banner = cfg.get("BANNER_PATH") or os.path.join(repo_root, "assets", "welcome.png")
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
                        self.pv_name.setText(str(cfg.get("EXAMPLE_NAME", "NewMember")))
                    if not self.pv_banner_path.hasFocus():
                        self.pv_banner_path.setText(str(cfg.get("BANNER_PATH", "")))
                    if not self.pv_bg_mode.hasFocus():
                        mode_val = str(cfg.get("BG_MODE", "cover") or "cover")
                        idx = self.pv_bg_mode.findData(mode_val)
                        self.pv_bg_mode.setCurrentIndex(idx if idx >= 0 else 0)
                    if not self.pv_bg_zoom.hasFocus():
                        self.pv_bg_zoom.setValue(int(cfg.get("BG_ZOOM", 100) or 100))
                    if not self.pv_bg_x.hasFocus():
                        self.pv_bg_x.setValue(int(cfg.get("BG_OFFSET_X", 0) or 0))
                    if not self.pv_bg_y.hasFocus():
                        self.pv_bg_y.setValue(int(cfg.get("BG_OFFSET_Y", 0) or 0))
                    if not self.pv_title.hasFocus():
                        self.pv_title.setText(str(cfg.get("BANNER_TITLE", "WELCOME")))
                    if not self.pv_title_font.hasFocus():
                        self._load_title_font_choices(str(cfg.get("FONT_WELCOME", "assets/fonts/Poppins-Bold.ttf")))
                    if not self.pv_user_font.hasFocus():
                        self._load_user_font_choices(str(cfg.get("FONT_USERNAME", "assets/fonts/Poppins-Regular.ttf")))
                    if not self.pv_title_size.hasFocus():
                        self.pv_title_size.setValue(int(cfg.get("TITLE_FONT_SIZE", 140) or 140))
                    if not self.pv_user_size.hasFocus():
                        self.pv_user_size.setValue(int(cfg.get("USERNAME_FONT_SIZE", 64) or 64))
                    if not self.pv_title_color.hasFocus():
                        self.pv_title_color.setText(str(cfg.get("TITLE_COLOR", "#FFFFFF")))
                    if not self.pv_user_color.hasFocus():
                        self.pv_user_color.setText(str(cfg.get("USERNAME_COLOR", "#E6E6E6")))
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

                    welcome_msg = cfg.get("WELCOME_MESSAGE")
                    if welcome_msg and not self.pv_message.hasFocus():
                        cur_text = self.pv_message.toPlainText()
                        if not cur_text or not cur_text.strip():
                            try:
                                self.pv_message.setPlainText(str(welcome_msg))
                            except Exception:
                                pass
                finally:
                    self._preview_syncing = False

            try:
                self._apply_live_preview()
            except Exception:
                pass
        except Exception:
            pass

    def _load_welcome_message_from_file(self):
        try:
            repo_root = self._repo_root
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            if not os.path.exists(cfg_path):
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            msg = str(cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", "Welcome {mention}!")))
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
