from PySide6 import QtWidgets

from config_io import config_json_path, load_json_dict, save_json_merged


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

        self._build_pages()
        self._load_existing_values()
        self._apply_read_only_mode()
        self._update_nav()

    def _apply_read_only_mode(self):
        if not self._read_only:
            return
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
        self._add_id_row(form_channels, "welcome", "WELCOME_CHANNEL_ID", "Welcome channel")
        self._add_id_row(form_channels, "welcome", "VERIFY_CHANNEL_ID", "Verify channel")
        self._add_id_row(form_channels, "welcome", "RULES_CHANNEL_ID", "Rules channel")
        self._add_id_row(form_channels, "welcome", "ABOUTME_CHANNEL_ID", "About-me channel")
        self._add_id_row(form_channels, "count", "COUNT_CHANNEL_ID", "Count channel")
        self._add_id_row(form_channels, "birthdays", "CHANNEL_ID", "Birthday channel")
        self._add_id_row(form_channels, "leveling", "ACHIEVEMENT_CHANNEL_ID", "Achievement channel")
        self._add_id_row(form_channels, "tickets", "TICKET_CATEGORY_ID", "Ticket category")
        self._add_id_row(form_channels, "tickets", "TICKET_LOG_CHANNEL_ID", "Ticket log channel")
        self._add_id_row(form_channels, "log_chat", "CHANNEL_ID", "Log chat channel")
        self._add_id_row(form_channels, "log_member", "CHANNEL_ID", "Log member channel")
        self._add_id_row(form_channels, "log_mod", "CHANNEL_ID", "Log moderation channel")
        self._add_id_row(form_channels, "log_server", "CHANNEL_ID", "Log server channel")
        self._add_id_row(form_channels, "log_voice", "CHANNEL_ID", "Log voice channel")

        form_roles = self._make_page(
            "2/4 • Role IDs",
            "Configure verification/default/support roles used by autorole and tickets.",
        )
        self._add_id_row(form_roles, "welcome", "ROLE_ID", "Welcome role")
        self._add_id_row(form_roles, "autorole", "STARTER_ROLE_ID", "Starter role")
        self._add_id_row(form_roles, "autorole", "VERIFY_ROLE_ID", "Verify role")
        self._add_id_row(form_roles, "autorole", "DEFAULT_ROLE_ID", "Default role")
        self._add_id_row(form_roles, "tickets", "SUPPORT_ROLE_ID", "Support role")

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
