from PySide6 import QtWidgets, QtCore, QtGui


class PreviewApiControllerMixin:
    def on_refresh_preview(self):
        try:
            try:
                self._set_status("Preview: requesting...")
            except Exception:
                pass
            overrides = {
                "BANNER_PATH": self.pv_banner_path.text() or None,
                "BG_MODE": self.pv_bg_mode.currentData() or "cover",
                "BG_ZOOM": int(self.pv_bg_zoom.value()),
                "BG_OFFSET_X": int(self.pv_bg_x.value()),
                "BG_OFFSET_Y": int(self.pv_bg_y.value()),
                "BANNER_TITLE": self.pv_title.text() or "WELCOME",
                "FONT_WELCOME": self._selected_title_font_path(),
                "FONT_USERNAME": self._selected_user_font_path(),
                "TITLE_FONT_SIZE": int(self.pv_title_size.value()),
                "USERNAME_FONT_SIZE": int(self.pv_user_size.value()),
                "TITLE_COLOR": self.pv_title_color.text() or "#FFFFFF",
                "USERNAME_COLOR": self.pv_user_color.text() or "#E6E6E6",
                "TITLE_OFFSET_X": int(self.pv_title_x.value()),
                "TITLE_OFFSET_Y": int(self.pv_title_y.value()),
                "USERNAME_OFFSET_X": int(self.pv_user_x.value()),
                "USERNAME_OFFSET_Y": int(self.pv_user_y.value()),
                "TEXT_OFFSET_X": int(self.pv_text_x.value()),
                "TEXT_OFFSET_Y": int(self.pv_text_y.value()),
                "OFFSET_X": int(self.pv_avatar_x.value()),
                "OFFSET_Y": int(self.pv_avatar_y.value()),
            }
            self.send_cmd_async(
                {"action": "ping"},
                timeout=0.6,
                cb=lambda ping, overrides=overrides: self._on_preview_ping_result(ping, overrides),
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Preview error", str(e))

    def _on_preview_ping_result(self, ping: dict, overrides: dict):
        try:
            if not ping.get("ok"):
                QtWidgets.QMessageBox.warning(self, "Preview", f"Control API not available, using local banner ({ping.get('error')})")
                try:
                    self.update_preview()
                except Exception:
                    pass
                return
            self.send_cmd_async(
                {"action": "banner_preview", "overrides": overrides},
                timeout=5.0,
                cb=self._on_preview_banner_result,
            )
        except Exception:
            pass

    def _on_preview_banner_result(self, r: dict):
        try:
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        scaled = pix.scaled(self.pv_banner.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        self.pv_banner.setPixmap(scaled)
                    except Exception:
                        self.pv_banner.setPixmap(pix)
                    self._preview_banner_data_url = f"data:image/png;base64,{b64}"
                    try:
                        self._apply_live_preview()
                    except Exception:
                        pass
                    return
            QtWidgets.QMessageBox.warning(self, "Preview", f"Failed to get banner from bot: {r}")
            try:
                self.update_preview()
            except Exception:
                pass
        except Exception:
            pass

    def on_refresh_rankpreview(self):
        try:
            try:
                self._set_status("Rank Preview: requesting...")
            except Exception:
                pass
            bg = self.rk_bg_path.text() or self._rank_config.get("BG_PATH") if getattr(self, "_rank_config", None) is not None else None
            req = {"action": "rank_preview"}
            if bg:
                req["bg_path"] = bg
            req["bg_mode"] = self.rk_bg_mode.currentData() or "cover"
            req["bg_zoom"] = int(self.rk_bg_zoom.value())
            req["bg_offset_x"] = int(self.rk_bg_x.value())
            req["bg_offset_y"] = int(self.rk_bg_y.value())
            req["name_font"] = self._selected_rank_name_font_path()
            req["info_font"] = self._selected_rank_info_font_path()
            req["name_font_size"] = int(self.rk_name_size.value())
            req["info_font_size"] = int(self.rk_info_size.value())
            req["name_color"] = self.rk_name_color.text() or "#FFFFFF"
            req["info_color"] = self.rk_info_color.text() or "#C8C8C8"
            req["text_offset_x"] = int(self.rk_text_x.value())
            req["text_offset_y"] = int(self.rk_text_y.value())
            self.send_cmd_async(req, timeout=3.0, cb=self._on_rankpreview_result)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Rank Preview error", str(e))

    def _on_rankpreview_result(self, r: dict):
        try:
            if r.get("ok") and r.get("png_base64"):
                b64 = r.get("png_base64")
                data = QtCore.QByteArray.fromBase64(b64.encode())
                pix = QtGui.QPixmap()
                if pix.loadFromData(data):
                    try:
                        self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                    except Exception:
                        self.rk_image.setPixmap(pix)
                    self._rank_preview_data_url = f"data:image/png;base64,{b64}"
                    return
            QtWidgets.QMessageBox.warning(self, "Rank Preview", f"Failed to get rank image from bot: {r}")
        except Exception:
            pass
