from config.config_io import (config_json_path, ensure_env_file, load_env_dict,
                              load_json_dict, save_env_merged,
                              save_json_merged)
from PySide6 import QtWidgets
from services.control_api_client import send_cmd

CHANNEL_FIELD_KEYS = [
    ("welcome", "WELCOME_CHANNEL_ID", "Welcome channel"),
    ("welcome", "VERIFY_CHANNEL_ID", "Verify channel"),
    ("welcome", "RULES_CHANNEL_ID", "Rules channel"),
    ("welcome", "ABOUTME_CHANNEL_ID", "About-me channel"),
    ("count", "COUNT_CHANNEL_ID", "Count channel"),
    ("birthdays", "CHANNEL_ID", "Birthday channel"),
    ("leveling", "ACHIEVEMENT_CHANNEL_ID", "Achievement channel"),
    ("tempvoice", "CREATE_CHANNEL_ID", "TempVoice create-join channel"),
    ("tempvoice", "CONTROL_CHANNEL_ID", "TempVoice control panel channel"),
    ("tempvoice", "CATEGORY_ID", "TempVoice category"),
    ("tickets", "TICKET_CATEGORY_ID", "Ticket category"),
    ("tickets", "TICKET_LOG_CHANNEL_ID", "Ticket log channel"),
    ("log_chat", "CHANNEL_ID", "Log chat channel"),
    ("log_member", "CHANNEL_ID", "Log member channel"),
    ("log_mod", "CHANNEL_ID", "Log moderation channel"),
    ("log_server", "CHANNEL_ID", "Log server channel"),
    ("log_voice", "CHANNEL_ID", "Log voice channel"),
    ("membercount", "CHANNEL_ID", "Member count channel"),
    ("freestuff", "CHANNEL_ID", "Free stuff channel"),
    ("social_media", "TWITCH.CHANNEL_ID", "Social: Twitch channel"),
    ("social_media", "YOUTUBE.CHANNEL_ID", "Social: YouTube channel"),
    ("social_media", "TWITTER.CHANNEL_ID", "Social: Twitter/X channel"),
    ("social_media", "TIKTOK.CHANNEL_ID", "Social: TikTok channel"),
]

ROLE_FIELD_KEYS = [
    ("welcome", "ROLE_ID", "Welcome role"),
    ("autorole", "STARTER_ROLE_ID", "Starter role"),
    ("autorole", "VERIFY_ROLE_ID", "Verify role"),
    ("autorole", "DEFAULT_ROLE_ID", "Default role"),
    ("tickets", "SUPPORT_ROLE_ID", "Support role"),
    ("birthdays", "ROLE_ID", "Birthday role"),
]

HIDDEN_WIZARD_ENV_KEYS = {"APP_ENV", "LOCAL_UI_ENABLE"}

# Mapping from wizard config file name to feature key.
# Fields whose feature is disabled will be hidden in the wizard.
_WIZARD_FILE_TO_FEATURE = {
    "welcome": "welcome",
    "autorole": "welcome",
    "count": "counting",
    "birthdays": "birthdays",
    "leveling": "leveling",
    "tempvoice": "tempvoice",
    "tickets": "tickets",
    "log_chat": "logging",
    "log_member": "logging",
    "log_mod": "logging",
    "log_server": "logging",
    "log_voice": "logging",
    "membercount": "membercount",
    "freestuff": "freestuff",
    "social_media": "socials",
}

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
        self._env_values = None
        self._load_env_values()

        # Inherit active guild from parent window
        self._guild_id = None
        try:
            if parent is not None:
                gid = getattr(parent, "_active_guild_id", None)
                if gid:
                    self._guild_id = str(gid)
        except Exception:
            pass

        guild_label = f" (Guild {self._guild_id})" if self._guild_id else ""
        self.setWindowTitle(f"Setup Wizard{guild_label}")
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
        self.help_btn = QtWidgets.QPushButton("Help")
        self.help_btn.setFlat(True)
        self.help_btn.setToolTip("Show help for the current setup step")
        self.finish_btn = QtWidgets.QPushButton("Finish")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        nav.addWidget(self.help_btn)
        nav.addStretch()
        nav.addWidget(self.back_btn)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.finish_btn)
        nav.addWidget(self.cancel_btn)
        root.addLayout(nav)

        self.back_btn.clicked.connect(self._go_back)
        self.next_btn.clicked.connect(self._go_next)
        self.help_btn.clicked.connect(self._show_current_page_help)
        self.finish_btn.clicked.connect(self._save_and_close)
        self.cancel_btn.clicked.connect(self.reject)
        self.snapshot_btn.clicked.connect(self._open_snapshot_picker)
        self.stack.currentChanged.connect(lambda _i: self._update_nav())

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
            path = config_json_path(self._repo_root, f"{name}.json", guild_id=self._guild_id)
            cfg = load_json_dict(path)
            self._configs[name] = cfg
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

    def _add_env_row(self, layout: QtWidgets.QFormLayout, key: str, label: str, placeholder: str = ""):
        line = QtWidgets.QLineEdit()
        if placeholder:
            line.setPlaceholderText(placeholder)
        self._fields[("__env__", key)] = (line, "env")
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
        # Load enabled features for the active guild
        enabled_features = self._load_enabled_features()

        # --- Page 1: Environment ---
        form_env = self._make_page(
            "Step 1 — Environment",
            "Configure runtime tokens saved to .env in the repository root.\n"
            "Without DISCORD_TOKEN the bot stays offline.",
        )
        for key in self._env_keys_for_wizard():
            self._add_env_row(form_env, key, key)

        # --- Page 2: Channels & Roles grouped by feature ---
        page2 = QtWidgets.QWidget()
        page2_outer = QtWidgets.QVBoxLayout(page2)
        title2 = QtWidgets.QLabel("Step 2 — Channels & Roles")
        title2.setStyleSheet("font-size: 16px; font-weight: 700;")
        page2_outer.addWidget(title2)
        sub2 = QtWidgets.QLabel(
            "Set channels and roles per feature. Only enabled features are shown.\n"
            "Right-click a channel/role in Discord (developer mode) to copy its ID."
        )
        sub2.setWordWrap(True)
        sub2.setStyleSheet("color:#9aa0a6;")
        page2_outer.addWidget(sub2)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        # Feature groups: (group_label, [(file, key, label), ...])
        _GROUPS = [
            ("Welcome & Verification", [
                ("welcome", "WELCOME_CHANNEL_ID", "Welcome channel"),
                ("welcome", "VERIFY_CHANNEL_ID", "Verify channel"),
                ("welcome", "RULES_CHANNEL_ID", "Rules channel"),
                ("welcome", "ABOUTME_CHANNEL_ID", "About-me channel"),
                ("welcome", "ROLE_ID", "Welcome role"),
                ("autorole", "STARTER_ROLE_ID", "Starter role"),
                ("autorole", "VERIFY_ROLE_ID", "Verify role"),
                ("autorole", "DEFAULT_ROLE_ID", "Default role"),
            ]),
            ("Community", [
                ("count", "COUNT_CHANNEL_ID", "Count channel"),
                ("birthdays", "CHANNEL_ID", "Birthday channel"),
                ("birthdays", "ROLE_ID", "Birthday role"),
                ("leveling", "ACHIEVEMENT_CHANNEL_ID", "Achievement channel"),
            ]),
            ("TempVoice", [
                ("tempvoice", "CREATE_CHANNEL_ID", "Create-join channel (Voice)"),
                ("tempvoice", "CONTROL_CHANNEL_ID", "Control panel channel (Text)"),
                ("tempvoice", "CATEGORY_ID", "TempVoice category"),
            ]),
            ("Tickets", [
                ("tickets", "TICKET_CATEGORY_ID", "Ticket category"),
                ("tickets", "TICKET_LOG_CHANNEL_ID", "Ticket log channel"),
                ("tickets", "SUPPORT_ROLE_ID", "Support role"),
            ]),
            ("Logging", [
                ("log_chat", "CHANNEL_ID", "Chat log channel"),
                ("log_member", "CHANNEL_ID", "Member log channel"),
                ("log_mod", "CHANNEL_ID", "Moderation log channel"),
                ("log_server", "CHANNEL_ID", "Server log channel"),
                ("log_voice", "CHANNEL_ID", "Voice log channel"),
            ]),
            ("Member Count", [
                ("membercount", "CHANNEL_ID", "Member count channel"),
            ]),
            ("Notifications", [
                ("freestuff", "CHANNEL_ID", "Free stuff channel"),
                ("social_media", "TWITCH.CHANNEL_ID", "Social: Twitch channel"),
                ("social_media", "YOUTUBE.CHANNEL_ID", "Social: YouTube channel"),
                ("social_media", "TWITTER.CHANNEL_ID", "Social: Twitter/X channel"),
                ("social_media", "TIKTOK.CHANNEL_ID", "Social: TikTok channel"),
            ]),
        ]

        for group_label, fields in _GROUPS:
            visible = [
                (f, k, l) for f, k, l in fields
                if self._is_field_visible(f, enabled_features)
            ]
            if not visible:
                continue
            group_box = QtWidgets.QGroupBox(group_label)
            group_form = QtWidgets.QFormLayout(group_box)
            group_form.setHorizontalSpacing(12)
            group_form.setVerticalSpacing(8)
            for file_name, key, label in visible:
                self._add_id_row(group_form, file_name, key, label)
            scroll_layout.addWidget(group_box)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        page2_outer.addWidget(scroll, 1)
        self.stack.addWidget(page2)

    def _load_enabled_features(self) -> dict:
        """Load features.json for the active guild.

        Returns a dict of feature_key -> bool.  If no guild or file,
        returns empty dict (meaning everything is visible).
        """
        import json as _json
        import os as _os

        gid = self._guild_id
        if not gid:
            return {}
        features_path = _os.path.join(
            self._repo_root, "config", "guilds", str(gid), "features.json"
        )
        try:
            with open(features_path, "r", encoding="utf-8") as fh:
                data = _json.load(fh)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _is_field_visible(self, file_name: str, features: dict) -> bool:
        """Check if a wizard field should be visible given enabled features."""
        if not features:
            return True  # No features → show everything
        feature_key = _WIZARD_FILE_TO_FEATURE.get(file_name)
        if feature_key is None:
            return True  # Not mapped → always show
        return bool(features.get(feature_key, True))

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

    def _load_env_values(self):
        env_path, _created = ensure_env_file(self._repo_root)
        self._env_values = load_env_dict(env_path)

    def _env_keys_for_wizard(self) -> list[str]:
        keys = [
            str(k).strip()
            for k in (self._env_values or {}).keys()
            if str(k).strip() and str(k).strip() not in HIDDEN_WIZARD_ENV_KEYS
        ]
        if keys:
            return keys
        return ["DISCORD_TOKEN", "CONTROL_API_TOKEN", "WEB_INTERNAL_TOKEN"]

    def _load_existing_values(self):
        for (file_name, key), (widget, field_type) in self._fields.items():
            if file_name == "__env__":
                current = (self._env_values or {}).get(key, "")
            else:
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
            elif field_type == "env":
                value = raw
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
            env_updates = updates.pop("__env__", None)
            if not self._validate_env_before_save(env_updates):
                return
            for file_name, data in updates.items():
                path = config_json_path(self._repo_root, f"{file_name}.json", guild_id=self._guild_id)
                save_json_merged(path, data)
            if env_updates is not None:
                save_env_merged(self._repo_root, env_updates)
            guild_label = f" for guild {self._guild_id}" if self._guild_id else ""
            QtWidgets.QMessageBox.information(
                self,
                "Setup Wizard",
                f"Setup saved successfully{guild_label}.",
            )
            self.accept()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Setup Wizard", f"Failed to save setup: {exc}")

    def _validate_env_before_save(self, env_updates: dict | None) -> bool:
        env_data = dict(self._env_values or {})
        if isinstance(env_updates, dict):
            env_data.update(env_updates)

        token = str(env_data.get("DISCORD_TOKEN", "") or "").strip()
        if token:
            return True

        result = QtWidgets.QMessageBox.warning(
            self,
            "Setup Wizard",
            "DISCORD_TOKEN ist leer.\n\n"
            "Die UI startet trotzdem, aber der Bot bleibt offline bis ein Token gesetzt ist.\n\n"
            "Trotzdem speichern?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes

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

    def _show_current_page_help(self):
        page = self.stack.currentIndex()
        title, text = self._help_text_for_page(page)
        QtWidgets.QMessageBox.information(self, title, text)

    def _help_text_for_page(self, page_index: int) -> tuple[str, str]:
        if page_index == 0:
            return (
                "Help • Environment",
                "Diese Seite bearbeitet deine .env Variablen für Tokens und Integrationen.\n\n"
                "Wo bekommst du die Werte?\n"
                "- DISCORD_TOKEN: Discord Developer Portal → Bot → Token\n"
                "- CONTROL_API_TOKEN: frei wählbarer geheimer Wert; muss in Bot und UI gleich sein\n"
                "- WEB_INTERNAL_TOKEN: frei wählbarer geheimer Wert für Bot↔Web Backend\n"
                "- SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET: Spotify Developer Dashboard\n"
                "- DISCORD_CLIENT_ID / DISCORD_CLIENT_SECRET: Discord OAuth2 App\n"
                "- OAUTH_REDIRECT_URI: OAuth Callback URL deines Web-Backends\n"
                "- APP_ORIGIN / APP_ENV: Frontend-URL und Umgebung (z. B. production)\n\n"
                "Hinweis: Ohne DISCORD_TOKEN bleibt der Bot offline.\n\n"
                "Discord-Hilfe-Kommandos:\n"
                "- /help (Aliases: /tutorial, /hilfe)\n"
                "- /admin_help (Aliases: /adminhelp, /ahelp)",
            )

        if page_index == 1:
            return (
                "Help • Channels & Roles",
                "Hier setzt du Channel- und Rollen-IDs, gruppiert nach Feature.\n\n"
                "Woher bekommst du die IDs?\n"
                "- In Discord Entwicklermodus aktivieren\n"
                "- Rechtsklick auf Kanal/Rolle → ID kopieren\n"
                "- Nur Zahlen eintragen (keine #, keine Namen)\n\n"
                "Feature-Gruppen:\n"
                "• Welcome & Verification: Channels + Rollen für Begrüßung\n"
                "• Community: Count, Birthdays, Leveling Channels\n"
                "• TempVoice: Join-to-create Hub, Control Panel, Kategorie\n"
                "• Tickets: Kategorie, Log Channel, Support Rolle\n"
                "• Logging: Chat/Member/Mod/Server/Voice Log Channels\n"
                "• Notifications: Free Stuff + Social Media Channels\n\n"
                "Tipp: Über 'Guild Snapshot Picker' kannst du viele IDs automatisch übernehmen.",
            )

        return (
            "Help",
            "Keine Hilfe für diese Seite verfügbar.",
        )
