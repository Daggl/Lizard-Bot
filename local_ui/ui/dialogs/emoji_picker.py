from PySide6 import QtWidgets, QtCore, QtGui, QtNetwork


class GuildEmojiPickerDialog(QtWidgets.QDialog):
    TILE_SIZE = 56
    GRID_SIZE = 72

    def __init__(self, snapshot_payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server Emoji Picker")
        self.resize(860, 680)
        self._payload = snapshot_payload or {}
        self._guilds = list(self._payload.get("guilds") or [])
        self._selected_emoji = None
        self._emoji_icon_cache = {}
        self._emoji_labels_by_id = {}
        self._emoji_bytes_cache = {}
        self._current_load_token = 0
        self._net = QtNetwork.QNetworkAccessManager(self)
        self._net.finished.connect(self._on_icon_reply)

        root = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Guild:"))
        self.guild_combo = QtWidgets.QComboBox()
        for idx, guild in enumerate(self._guilds):
            gid = guild.get("id")
            gname = guild.get("name") or str(gid)
            emojis = list(guild.get("emojis") or [])
            self.guild_combo.addItem(f"{gname} ({gid}) — {len(emojis)} emojis", idx)
        top.addWidget(self.guild_combo, 1)
        root.addLayout(top)

        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(QtWidgets.QLabel("Search:"))
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Emoji name contains...")
        search_row.addWidget(self.search_edit, 1)
        root.addLayout(search_row)

        self.emoji_list = QtWidgets.QListWidget()
        self.emoji_list.setViewMode(QtWidgets.QListView.IconMode)
        self.emoji_list.setFlow(QtWidgets.QListView.LeftToRight)
        self.emoji_list.setResizeMode(QtWidgets.QListView.Adjust)
        self.emoji_list.setWrapping(True)
        self.emoji_list.setUniformItemSizes(True)
        self.emoji_list.setIconSize(QtCore.QSize(self.TILE_SIZE, self.TILE_SIZE))
        self.emoji_list.setGridSize(QtCore.QSize(self.GRID_SIZE, self.GRID_SIZE))
        self.emoji_list.setWordWrap(False)
        self.emoji_list.setSpacing(6)
        self.emoji_list.setMovement(QtWidgets.QListView.Static)
        self.emoji_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        root.addWidget(self.emoji_list, 1)

        preview_row = QtWidgets.QHBoxLayout()
        self.preview_icon = QtWidgets.QLabel()
        self.preview_icon.setFixedSize(56, 56)
        self.preview_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_icon.setStyleSheet("border: 1px solid #334258; border-radius: 6px;")
        preview_row.addWidget(self.preview_icon, 0)
        self.preview_label = QtWidgets.QLabel("Selected: —")
        preview_row.addWidget(self.preview_label, 1)
        root.addLayout(preview_row)

        buttons = QtWidgets.QHBoxLayout()
        self.insert_btn = QtWidgets.QPushButton("Insert")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        buttons.addStretch()
        buttons.addWidget(self.insert_btn)
        buttons.addWidget(self.cancel_btn)
        root.addLayout(buttons)

        self.guild_combo.currentIndexChanged.connect(self._populate_current_guild)
        self.search_edit.textChanged.connect(self._populate_current_guild)
        self.emoji_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.emoji_list.itemDoubleClicked.connect(lambda _item: self._accept_if_valid())
        self.insert_btn.clicked.connect(self._accept_if_valid)
        self.cancel_btn.clicked.connect(self.reject)

        self._populate_current_guild()

    def _selected_guild(self) -> dict:
        idx = int(self.guild_combo.currentData() or 0)
        if idx < 0 or idx >= len(self._guilds):
            return {}
        return self._guilds[idx] or {}

    @staticmethod
    def _emoji_markup(emoji_entry: dict) -> str:
        emoji_name = str(emoji_entry.get("name") or "").strip()
        emoji_id = emoji_entry.get("id")
        animated = bool(emoji_entry.get("animated", False))
        prefix = "a" if animated else ""
        return f"<{prefix}:{emoji_name}:{emoji_id}>" if emoji_name and emoji_id else ""

    @staticmethod
    def _emoji_url(emoji_entry: dict, ext: str) -> str:
        emoji_id = emoji_entry.get("id")
        if not emoji_id:
            return ""
        animated = bool(emoji_entry.get("animated", False))
        if animated:
            return f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=64&quality=lossless&animated=true"
        return f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=64&quality=lossless"

    @staticmethod
    def _emoji_url_candidates(emoji_entry: dict) -> list[str]:
        animated = bool(emoji_entry.get("animated", False))
        if animated:
            exts = ("gif", "webp", "png")
        else:
            exts = ("png", "webp", "jpg")
        urls = []
        for ext in exts:
            try:
                u = GuildEmojiPickerDialog._emoji_url(emoji_entry, ext)
                if u:
                    urls.append(u)
            except Exception:
                pass
        return urls

    def _emoji_icon(self, emoji_entry: dict) -> QtGui.QIcon:
        emoji_id = emoji_entry.get("id")
        if not emoji_id:
            return QtGui.QIcon()
        cache_key = int(emoji_id)
        cached = self._emoji_icon_cache.get(cache_key)
        if cached is not None:
            return cached
        return QtGui.QIcon()

    @staticmethod
    def _clear_label_media(label: QtWidgets.QLabel):
        try:
            movie = getattr(label, "_emoji_movie", None)
            if movie is not None:
                movie.stop()
        except Exception:
            pass
        try:
            label._emoji_movie = None
            label._emoji_movie_buf = None
        except Exception:
            pass
        try:
            label.setMovie(None)
        except Exception:
            pass

    def _set_label_media(self, label: QtWidgets.QLabel, image_bytes: bytes, animated: bool, size: int):
        if not image_bytes:
            return
        self._clear_label_media(label)

        if animated:
            try:
                ba = QtCore.QByteArray(image_bytes)
                buf = QtCore.QBuffer(label)
                buf.setData(ba)
                if buf.open(QtCore.QIODevice.ReadOnly):
                    movie = QtGui.QMovie(buf, b"", label)
                    if movie.isValid():
                        movie.setScaledSize(QtCore.QSize(size, size))
                        label._emoji_movie = movie
                        label._emoji_movie_buf = buf
                        label.setMovie(movie)
                        movie.start()
                        return
            except Exception:
                pass

        pix = QtGui.QPixmap()
        if pix.loadFromData(image_bytes):
            label.setPixmap(pix.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    @staticmethod
    def _emoji_name(emoji_entry: dict) -> str:
        return str(emoji_entry.get("name") or "").strip()

    def _create_emoji_list_item(self, emoji_entry: dict, markup: str, emoji_id: int) -> QtWidgets.QListWidgetItem:
        name = self._emoji_name(emoji_entry)
        item = QtWidgets.QListWidgetItem("")
        item.setData(QtCore.Qt.UserRole, markup)
        item.setData(QtCore.Qt.UserRole + 1, emoji_entry)
        item.setData(QtCore.Qt.UserRole + 2, emoji_id)
        item.setToolTip(f":{name}:\n{markup}")
        item.setSizeHint(QtCore.QSize(self.TILE_SIZE + 4, self.TILE_SIZE + 4))
        return item

    def _create_emoji_tile(self, emoji_entry: dict, markup: str) -> QtWidgets.QLabel:
        name = self._emoji_name(emoji_entry)
        tile = QtWidgets.QLabel()
        tile.setFixedSize(self.TILE_SIZE, self.TILE_SIZE)
        tile.setAlignment(QtCore.Qt.AlignCenter)
        tile.setStyleSheet("border: 1px solid #334258; border-radius: 6px;")
        tile.setToolTip(f":{name}:\n{markup}")
        return tile

    def _queue_icon_load(self, emoji_entry: dict, load_token: int, attempt_index: int = 0):
        emoji_id = emoji_entry.get("id")
        if not emoji_id:
            return
        try:
            cache_key = int(emoji_id)
        except Exception:
            return
        if cache_key in self._emoji_icon_cache:
            return
        candidates = self._emoji_url_candidates(emoji_entry)
        if not candidates:
            return
        if attempt_index < 0 or attempt_index >= len(candidates):
            return
        url = candidates[attempt_index]
        req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        req.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        reply = self._net.get(req)
        reply.setProperty("emoji_id", cache_key)
        reply.setProperty("load_token", int(load_token))
        reply.setProperty("attempt_index", int(attempt_index))
        reply.setProperty("is_animated", bool(emoji_entry.get("animated", False)))

    def _on_icon_reply(self, reply: QtNetwork.QNetworkReply):
        try:
            try:
                load_token = int(reply.property("load_token") or 0)
                emoji_id = int(reply.property("emoji_id") or 0)
                attempt_index = int(reply.property("attempt_index") or 0)
                is_animated = bool(reply.property("is_animated") or False)
            except Exception:
                return

            if load_token != self._current_load_token or emoji_id <= 0:
                return

            pix = QtGui.QPixmap()
            loaded_ok = False
            try:
                if reply.error() == QtNetwork.QNetworkReply.NoError:
                    data = reply.readAll()
                    loaded_ok = pix.loadFromData(bytes(data))
            except Exception:
                loaded_ok = False

            if not loaded_ok:
                fallback_entry = {"id": emoji_id, "animated": is_animated}
                candidates = self._emoji_url_candidates(fallback_entry)
                next_attempt = attempt_index + 1
                if next_attempt < len(candidates):
                    self._queue_icon_load(fallback_entry, load_token, attempt_index=next_attempt)
                return

            icon = QtGui.QIcon(pix)
            self._emoji_icon_cache[emoji_id] = icon
            self._emoji_bytes_cache[emoji_id] = bytes(data)

            labels = list(self._emoji_labels_by_id.get(emoji_id) or [])
            for label in labels:
                try:
                    self._set_label_media(label, self._emoji_bytes_cache.get(emoji_id) or b"", is_animated, self.TILE_SIZE)
                except Exception:
                    pass

            current = self.emoji_list.currentItem()
            if current is not None:
                try:
                    current_id = int(current.data(QtCore.Qt.UserRole + 2) or 0)
                except Exception:
                    current_id = 0
                if current_id == emoji_id:
                    self._set_preview_icon(current.data(QtCore.Qt.UserRole + 1) or None)
        finally:
            try:
                reply.deleteLater()
            except Exception:
                pass

    def _set_preview_icon(self, emoji_entry: dict | None):
        try:
            if not emoji_entry:
                self._clear_label_media(self.preview_icon)
                self.preview_icon.clear()
                return

            try:
                emoji_id = int(emoji_entry.get("id") or 0)
            except Exception:
                emoji_id = 0
            animated = bool(emoji_entry.get("animated", False))

            raw = self._emoji_bytes_cache.get(emoji_id)
            if raw:
                self._set_label_media(self.preview_icon, raw, animated, 48)
                return

            icon = self._emoji_icon(emoji_entry)
            pix = icon.pixmap(48, 48)
            if pix.isNull():
                self._clear_label_media(self.preview_icon)
                self.preview_icon.clear()
                return
            self._clear_label_media(self.preview_icon)
            self.preview_icon.setPixmap(pix)
        except Exception:
            self._clear_label_media(self.preview_icon)
            self.preview_icon.clear()

    def _populate_current_guild(self):
        guild = self._selected_guild()
        search_text = (self.search_edit.text() or "").strip().lower()
        emojis = list(guild.get("emojis") or [])
        self.emoji_list.clear()
        self._selected_emoji = None
        self._emoji_labels_by_id = {}
        self._current_load_token += 1
        current_token = self._current_load_token

        for emoji in emojis:
            name = self._emoji_name(emoji)
            if search_text and search_text not in name.lower():
                continue
            markup = self._emoji_markup(emoji)
            if not markup:
                continue
            try:
                emoji_id = int(emoji.get("id") or 0)
            except Exception:
                emoji_id = 0
            item = self._create_emoji_list_item(emoji, markup, emoji_id)
            self.emoji_list.addItem(item)

            tile = self._create_emoji_tile(emoji, markup)
            self.emoji_list.setItemWidget(item, tile)

            if emoji_id > 0:
                self._emoji_labels_by_id.setdefault(emoji_id, []).append(tile)
                raw = self._emoji_bytes_cache.get(emoji_id)
                if raw:
                    self._set_label_media(tile, raw, bool(emoji.get("animated", False)), self.TILE_SIZE)
                self._queue_icon_load(emoji, current_token)

        if self.emoji_list.count() > 0:
            self.emoji_list.setCurrentRow(0)
            self._on_selection_changed()
        else:
            self.preview_label.setText("Selected: —")
            self._set_preview_icon(None)

    def _on_selection_changed(self):
        item = self.emoji_list.currentItem()
        if not item:
            self._selected_emoji = None
            self.preview_label.setText("Selected: —")
            self._set_preview_icon(None)
            return
        value = str(item.data(QtCore.Qt.UserRole) or "").strip()
        self._selected_emoji = value or None
        emoji_entry = item.data(QtCore.Qt.UserRole + 1)
        self._set_preview_icon(emoji_entry if isinstance(emoji_entry, dict) else None)
        if isinstance(emoji_entry, dict):
            label = str(emoji_entry.get("name") or "").strip() or "unknown"
            animated_txt = " [animated]" if bool(emoji_entry.get("animated", False)) else ""
            self.preview_label.setText(f"Selected: :{label}:{animated_txt}  {value}" if value else "Selected: —")
        else:
            self.preview_label.setText(f"Selected: {value}" if value else "Selected: —")

    def _accept_if_valid(self):
        if not self._selected_emoji:
            QtWidgets.QMessageBox.information(self, "Emoji Picker", "Please select an emoji first.")
            return
        self.accept()

    def selected_emoji(self) -> str:
        return str(self._selected_emoji or "").strip()
