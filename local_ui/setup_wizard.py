from PySide6 import QtWidgets

from config_io import config_json_path, load_json_dict, save_json_merged
from control_api_client import send_cmd


CHANNEL_FIELD_KEYS = [
    ("welcome", "WELCOME_CHANNEL_ID", "Welcome channel"),
    ("welcome", "VERIFY_CHANNEL_ID", "Verify channel"),
    ("welcome", "RULES_CHANNEL_ID", "Rules channel"),
    ("welcome", "ABOUTME_CHANNEL_ID", "About-me channel"),
    ("count", "COUNT_CHANNEL_ID", "Count channel"),
    ("birthdays", "CHANNEL_ID", "Birthday channel"),
    ("leveling", "ACHIEVEMENT_CHANNEL_ID", "Achievement channel"),
    ("tickets", "TICKET_CATEGORY_ID", "Ticket category"),
    ("tickets", "TICKET_LOG_CHANNEL_ID", "Ticket log channel"),
    ("log_chat", "CHANNEL_ID", "Log chat channel"),
    ("log_member", "CHANNEL_ID", "Log member channel"),
    ("log_mod", "CHANNEL_ID", "Log moderation channel"),
    ("log_server", "CHANNEL_ID", "Log server channel"),
    ("log_voice", "CHANNEL_ID", "Log voice channel"),
]

ROLE_FIELD_KEYS = [
    ("welcome", "ROLE_ID", "Welcome role"),
    ("autorole", "STARTER_ROLE_ID", "Starter role"),
    ("autorole", "VERIFY_ROLE_ID", "Verify role"),
    ("autorole", "DEFAULT_ROLE_ID", "Default role"),
    ("tickets", "SUPPORT_ROLE_ID", "Support role"),
]


class GuildSnapshotPickerDialog(QtWidgets.QDialog):
    def __init__(self, snapshot_payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guild Snapshot Picker")
        self.resize(860, 720)
        self._payload = snapshot_payload or {}
        self._guilds = list(self._payload.get("guilds") or [])
        self._channel_combos = {}
        self._role_combos = {}

        root = QtWidgets.QVBoxLayout(self)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("Guild:"))
        self.guild_combo = QtWidgets.QComboBox()
        for idx, guild in enumerate(self._guilds):
            gid = guild.get("id")
            gname = guild.get("name") or str(gid)
            self.guild_combo.addItem(f"{gname} ({gid})", idx)
        top_row.addWidget(self.guild_combo, 1)
        root.addLayout(top_row)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)

        ch_box = QtWidgets.QGroupBox("Channel mappings")
        ch_form = QtWidgets.QFormLayout(ch_box)
        for file_name, key, label in CHANNEL_FIELD_KEYS:
            combo = QtWidgets.QComboBox()
            combo.addItem("(keep current)", None)
            self._channel_combos[(file_name, key)] = combo
            ch_form.addRow(label, combo)
        content_layout.addWidget(ch_box)

        role_box = QtWidgets.QGroupBox("Role mappings")
        role_form = QtWidgets.QFormLayout(role_box)
        for file_name, key, label in ROLE_FIELD_KEYS:
            combo = QtWidgets.QComboBox()
            combo.addItem("(keep current)", None)
            self._role_combos[(file_name, key)] = combo
            role_form.addRow(label, combo)
        content_layout.addWidget(role_box)

        content_layout.addStretch()
        self.scroll.setWidget(content)
        root.addWidget(self.scroll, 1)

        buttons = QtWidgets.QHBoxLayout()
        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        buttons.addStretch()
        buttons.addWidget(self.apply_btn)
        buttons.addWidget(self.cancel_btn)
        root.addLayout(buttons)

        self.guild_combo.currentIndexChanged.connect(self._populate_current_guild)
        self.apply_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self._populate_current_guild()

    def _populate_current_guild(self):
        idx = int(self.guild_combo.currentData() or 0)
        if idx < 0 or idx >= len(self._guilds):
            return
        guild = self._guilds[idx]
        channels = list(guild.get("channels") or [])
        roles = list(guild.get("roles") or [])

        for (file_name, key), combo in self._channel_combos.items():
            combo.clear()
            combo.addItem("(keep current)", None)
            key_upper = str(key).upper()
            if "CATEGORY" in key_upper:
                filtered = [c for c in channels if "category" in str(c.get("type") or "").lower()]
            else:
                filtered = [c for c in channels if "category" not in str(c.get("type") or "").lower()]
            for channel in filtered:
                cid = channel.get("id")
                ctype = channel.get("type")
                cname = channel.get("name")
                combo.addItem(f"{cname} [{ctype}] ({cid})", cid)

        for _field_key, combo in self._role_combos.items():
            combo.clear()
            combo.addItem("(keep current)", None)
            for role in roles:
                rid = role.get("id")
                rname = role.get("name")
                combo.addItem(f"{rname} ({rid})", rid)

    def selected_mapping(self) -> dict:
        out = {}
        for field_key, combo in self._channel_combos.items():
            value = combo.currentData()
            if value:
                out[field_key] = int(value)
        for field_key, combo in self._role_combos.items():
            value = combo.currentData()
            if value:
                out[field_key] = int(value)
        return out


class SetupWizardDialog(QtWidgets.QDialog):
    def __init__(self, repo_root: str, parent=None, read_only: bool = False):
        super().__init__(parent)
        self._repo_root = repo_root
        self._read_only = bool(read_only)
        self._fields = {}
        self._configs = {}

        self.setWindowTitle("Setup Wizard")
        self.resize(860, 640)

        root = QtWidgets.QVBoxLayout(self)
        self.step_label = QtWidgets.QLabel()
        self.step_label.setObjectName("sectionLabel")
        root.addWidget(self.step_label)

        top_actions = QtWidgets.QHBoxLayout()
        self.snapshot_btn = QtWidgets.QPushButton("Guild Snapshot Picker")
        top_actions.addWidget(self.snapshot_btn)
        top_actions.addStretch()
        root.addLayout(top_actions)

        self.stack = QtWidgets.QStackedWidget()
        root.addWidget(self.stack, 1)

        nav = QtWidgets.QHBoxLayout()
        self.back_btn = QtWidgets.QPushButton("Back")
        self.next_btn = QtWidgets.QPushButton("Next")
        self.finish_btn = QtWidgets.QPushButton("Finish")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        nav.addStretch()
        nav.addWidget(self.back_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.finish_btn)
        nav.addWidget(self.cancel_btn)
        root.addLayout(nav)

        self.back_btn.clicked.connect(self._go_back)
        self.next_btn.clicked.connect(self._go_next)
        self.finish_btn.clicked.connect(self._save_and_close)
        self.cancel_btn.clicked.connect(self.reject)
        self.snapshot_btn.clicked.connect(self._open_snapshot_picker)

        self._build_pages()
        self._load_existing_values()
        self._apply_read_only_mode()
        self._update_nav()

    def _apply_read_only_mode(self):
        if not self._read_only:
            return
        self.snapshot_btn.setEnabled(False)
        for _, (widget, _field_type) in self._fields.items():
            try:
                if hasattr(widget, "setReadOnly"):
                    widget.setReadOnly(True)
                if hasattr(widget, "setEnabled"):
                    widget.setEnabled(False)
            except Exception:
                pass
        self.finish_btn.setEnabled(False)
        self.step_label.setText("Read-only mode active")

    def _cfg(self, name: str) -> dict:
        if name not in self._configs:
            path = config_json_path(self._repo_root, f"{name}.json")
            self._configs[name] = load_json_dict(path)
        return self._configs[name]

    def _add_id_row(self, layout: QtWidgets.QFormLayout, file_name: str, key: str, label: str):
        line = QtWidgets.QLineEdit()
        line.setPlaceholderText("Discord ID (digits)")
        self._fields[(file_name, key)] = (line, "int")
        layout.addRow(label, line)

    def _add_text_row(self, layout: QtWidgets.QFormLayout, file_name: str, key: str, label: str, placeholder: str = ""):
        line = QtWidgets.QLineEdit()
        if placeholder:
            line.setPlaceholderText(placeholder)
        self._fields[(file_name, key)] = (line, "str")
        layout.addRow(label, line)

    def _add_multiline_row(self, layout: QtWidgets.QFormLayout, file_name: str, key: str, label: str):
        text = QtWidgets.QPlainTextEdit()
        text.setMinimumHeight(130)
        self._fields[(file_name, key)] = (text, "text")
        layout.addRow(label, text)

    def _make_page(self, title: str, subtitle: str = ""):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        outer.addWidget(title_lbl)
        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setStyleSheet("color:#9aa0a6;")
            outer.addWidget(sub)
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        outer.addLayout(form)
        outer.addStretch()
        self.stack.addWidget(page)
        return form

    def _build_pages(self):
        form_channels = self._make_page(
            "1/4 • Channel IDs",
            "Set key channels used by welcome, logs, counting, birthdays, leveling and tickets.",
        )
        for file_name, key, label in CHANNEL_FIELD_KEYS:
            self._add_id_row(form_channels, file_name, key, label)

        form_roles = self._make_page(
            "2/4 • Role IDs",
            "Configure verification/default/support roles used by autorole and tickets.",
        )
        for file_name, key, label in ROLE_FIELD_KEYS:
            self._add_id_row(form_roles, file_name, key, label)

        form_welcome = self._make_page(
            "3/4 • Welcome Defaults",
            "Define the welcome banner title, example name and default welcome message.",
        )
        self._add_text_row(form_welcome, "welcome", "EXAMPLE_NAME", "Example name", "NewMember")
        self._add_text_row(form_welcome, "welcome", "BANNER_TITLE", "Banner title", "WELCOME")
        self._add_multiline_row(form_welcome, "welcome", "WELCOME_MESSAGE", "Welcome message")

        form_rank = self._make_page(
            "4/4 • Rank Defaults",
            "Set initial rank card appearance defaults.",
        )
        self._add_text_row(form_rank, "rank", "EXAMPLE_NAME", "Rank example name", "NewMember")
        self._add_text_row(form_rank, "rank", "NAME_COLOR", "Name color", "#FFFFFF")
        self._add_text_row(form_rank, "rank", "INFO_COLOR", "Info color", "#C8C8C8")
        self._add_text_row(form_rank, "rank", "NAME_FONT_SIZE", "Name font size", "60")
        self._add_text_row(form_rank, "rank", "INFO_FONT_SIZE", "Info font size", "40")

    def _open_snapshot_picker(self):
        try:
            resp = send_cmd({"action": "guild_snapshot"}, timeout=8.0)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Guild Snapshot", f"Request failed: {exc}")
            return

        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(self, "Guild Snapshot", f"Failed: {resp}")
            return

        guilds = list(resp.get("guilds") or [])
        if not guilds:
            QtWidgets.QMessageBox.warning(self, "Guild Snapshot", "No guild data returned from bot.")
            return

        dlg = GuildSnapshotPickerDialog(resp, self)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return

        mapping = dlg.selected_mapping()
        for field_key, value in mapping.items():
            widget_meta = self._fields.get(field_key)
            if not widget_meta:
                continue
            widget, field_type = widget_meta
            if field_type != "int":
                continue
            try:
                widget.setText(str(int(value)))
            except Exception:
                continue

    def _load_existing_values(self):
        for (file_name, key), (widget, field_type) in self._fields.items():
            current = self._cfg(file_name).get(key, "")
            if current is None:
                current = ""
            if field_type == "text":
                widget.setPlainText(str(current))
            else:
                widget.setText(str(current))

    def _coerce_int(self, value: str, label: str) -> int:
        raw = str(value or "").strip()
        if not raw:
            raise ValueError(f"{label}: empty value")
        if not raw.isdigit():
            raise ValueError(f"{label}: must contain only digits")
        return int(raw)

    def _collect_updates(self):
        updates = {}
        for (file_name, key), (widget, field_type) in self._fields.items():
            label = f"{file_name}.{key}"
            if field_type == "text":
                raw = widget.toPlainText()
            else:
                raw = widget.text()
            raw = str(raw or "").strip()

            if field_type == "int":
                if not raw:
                    continue
                value = self._coerce_int(raw, label)
            elif field_type == "str":
                if not raw:
                    continue
                value = raw
            else:
                value = raw

            updates.setdefault(file_name, {})[key] = value
        return updates

    def _save_and_close(self):
        try:
            updates = self._collect_updates()
            for file_name, data in updates.items():
                path = config_json_path(self._repo_root, f"{file_name}.json")
                save_json_merged(path, data)
            QtWidgets.QMessageBox.information(
                self,
                "Setup Wizard",
                "Setup saved successfully.",
            )
            self.accept()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Setup Wizard", f"Failed to save setup: {exc}")

    def _go_back(self):
        i = self.stack.currentIndex()
        if i > 0:
            self.stack.setCurrentIndex(i - 1)
            self._update_nav()

    def _go_next(self):
        i = self.stack.currentIndex()
        if i < self.stack.count() - 1:
            self.stack.setCurrentIndex(i + 1)
            self._update_nav()

    def _update_nav(self):
        i = self.stack.currentIndex()
        total = self.stack.count()
        if not self._read_only:
            self.step_label.setText(f"Step {i + 1} of {total}")
        self.back_btn.setEnabled(i > 0)
        self.next_btn.setEnabled(i < total - 1)
        self.finish_btn.setEnabled((i == total - 1) and (not self._read_only))
