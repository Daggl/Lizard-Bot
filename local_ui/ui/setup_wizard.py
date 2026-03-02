from config.config_io import (config_json_path, ensure_env_file, load_env_dict,
                              load_json_dict, save_env_merged,
                              save_json_deep_merged, save_json_merged)
from PySide6 import QtWidgets
from services.control_api_client import send_cmd

# Platform mapping for social channels
_SOCIAL_PLATFORMS = ["Twitch", "YouTube", "Twitter / X", "TikTok"]
_PLATFORM_KEY_MAP = {
    "Twitch": "TWITCH",
    "YouTube": "YOUTUBE",
    "Twitter / X": "TWITTER",
    "TikTok": "TIKTOK",
}

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


def _get_nested(d: dict, dotted_key: str, default=""):
    """Read a value from a nested dict using dot notation (e.g. TWITCH.CHANNEL_ID)."""
    parts = dotted_key.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.get(p, {}) if isinstance(cur, dict) else {}
    return cur.get(parts[-1], default) if isinstance(cur, dict) else default


def _set_nested(d: dict, dotted_key: str, value):
    """Set a value in a nested dict using dot notation (e.g. TWITCH.CHANNEL_ID)."""
    parts = dotted_key.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

# Determine the default channel type for "Create" based on field key
def _channel_type_for_key(key: str) -> str:
    key_upper = str(key).upper()
    if "CATEGORY" in key_upper:
        return "category"
    if "CREATE_CHANNEL" in key_upper:
        return "voice"
    return "text"


class SetupWizardDialog(QtWidgets.QDialog):
    def __init__(self, repo_root: str, parent=None, read_only: bool = False):
        super().__init__(parent)
        self._repo_root = repo_root
        self._read_only = bool(read_only)
        self._fields = {}
        self._configs = {}
        self._env_values = None
        self._snapshot_cache = None  # cached guild_snapshot response
        self._name_labels = {}  # (file_name, key) -> QLabel for channel/role name
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
        self.resize(920, 680)

        root = QtWidgets.QVBoxLayout(self)
        self.step_label = QtWidgets.QLabel()
        self.step_label.setObjectName("sectionLabel")
        root.addWidget(self.step_label)

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
        self.stack.currentChanged.connect(lambda _i: self._update_nav())

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
            path = config_json_path(self._repo_root, f"{name}.json", guild_id=self._guild_id)
            cfg = load_json_dict(path)
            self._configs[name] = cfg
        return self._configs[name]

    def _add_id_row(self, layout, file_name: str, key: str, label: str,
                    is_role: bool = False):
        """Build a row:  [Create]  Label  [Channel Name]  [Channel ID]  [Pick...]"""
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)

        # Create button
        create_btn = QtWidgets.QPushButton("Create")
        create_btn.setFixedWidth(64)
        if is_role:
            create_btn.setToolTip("Create this role on the Discord server")
            create_btn.clicked.connect(
                lambda _c=False, fn=file_name, k=key, lbl=label: self._on_create_role(fn, k, lbl)
            )
        else:
            create_btn.setToolTip("Create this channel on the Discord server")
            create_btn.clicked.connect(
                lambda _c=False, fn=file_name, k=key, lbl=label: self._on_create_channel(fn, k, lbl)
            )
        row.addWidget(create_btn)

        # Label
        lbl_widget = QtWidgets.QLabel(label)
        lbl_widget.setFixedWidth(190)
        row.addWidget(lbl_widget)

        # Channel/Role Name (read-only display)
        name_label = QtWidgets.QLineEdit()
        name_label.setReadOnly(True)
        name_label.setPlaceholderText("Channel Name" if not is_role else "Role Name")
        name_label.setMinimumWidth(140)
        self._name_labels[(file_name, key)] = name_label
        row.addWidget(name_label, 1)

        # Channel/Role ID
        line = QtWidgets.QLineEdit()
        line.setPlaceholderText("Channel Id" if not is_role else "Role Id")
        line.setMinimumWidth(160)
        self._fields[(file_name, key)] = (line, "int")
        row.addWidget(line, 2)

        # Pick button
        pick_btn = QtWidgets.QPushButton("Pick...")
        pick_btn.setFixedWidth(64)
        pick_btn.clicked.connect(
            lambda _c=False, fn=file_name, k=key, role=is_role: self._on_pick(fn, k, role)
        )
        row.addWidget(pick_btn)

        layout.addLayout(row)

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
            "Use Pick... to select an existing channel/role, or Create to make a new one."
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

        # Determine which fields are roles
        _ROLE_KEYS = {(f, k) for f, k, _l in ROLE_FIELD_KEYS}

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
                ("tempvoice", "CONTROL_CHANNEL_ID", "Control panel channel"),
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
            group_vbox = QtWidgets.QVBoxLayout(group_box)
            group_vbox.setSpacing(6)
            for file_name, key, label in visible:
                is_role = (file_name, key) in _ROLE_KEYS
                self._add_id_row(group_vbox, file_name, key, label, is_role=is_role)

            scroll_layout.addWidget(group_box)

        # --- Social Media section (per-channel card model) ---
        if self._is_field_visible("social_media", enabled_features):
            self._social_channel_cards = {}   # platform_key -> list[dict]
            self._social_cards_layouts = {}   # platform_key -> QVBoxLayout
            sm_box = QtWidgets.QGroupBox("Social Media")
            sm_vbox = QtWidgets.QVBoxLayout(sm_box)
            sm_vbox.setSpacing(8)

            sm_desc = QtWidgets.QLabel(
                "Each platform has channel entries. Each entry maps one "
                "Discord channel to one or more creators.\n"
                "Use 'Additional … Channel' to add a new entry."
            )
            sm_desc.setWordWrap(True)
            sm_desc.setStyleSheet("color:#9aa0a6; font-size: 11px;")
            sm_vbox.addWidget(sm_desc)

            for platform_name, platform_key in _PLATFORM_KEY_MAP.items():
                pbox = QtWidgets.QGroupBox(platform_name)
                pvbox = QtWidgets.QVBoxLayout(pbox)
                pvbox.setSpacing(4)

                cards_list: list[dict] = []
                cards_vbox = QtWidgets.QVBoxLayout()
                cards_vbox.setSpacing(6)
                cards_vbox.addStretch()
                pvbox.addLayout(cards_vbox)

                self._social_channel_cards[platform_key] = cards_list
                self._social_cards_layouts[platform_key] = cards_vbox

                add_btn = QtWidgets.QPushButton(f"Additional {platform_name} Channel")
                add_btn.setFixedWidth(220)
                add_btn.clicked.connect(
                    lambda _=False, pn=platform_name, pk=platform_key,
                           cl=cards_list, cv=cards_vbox:
                        self._add_social_card(pn, pk, cl, cv)
                )
                pvbox.addWidget(add_btn)

                sm_vbox.addWidget(pbox)

            scroll_layout.addWidget(sm_box)

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

    def _fetch_snapshot(self) -> dict | None:
        """Fetch and cache the guild snapshot from the bot."""
        if self._snapshot_cache is not None:
            return self._snapshot_cache
        try:
            resp = send_cmd({"action": "guild_snapshot"}, timeout=8.0)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Snapshot", f"Bot nicht erreichbar: {exc}")
            return None
        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(self, "Snapshot", f"Fehler: {resp}")
            return None
        self._snapshot_cache = resp
        return resp

    def _get_guild_from_snapshot(self, snapshot: dict) -> dict | None:
        """Return the guild dict matching the active guild, or the first one."""
        guilds = list(snapshot.get("guilds") or [])
        if not guilds:
            return None
        if self._guild_id:
            for g in guilds:
                if str(g.get("id")) == str(self._guild_id):
                    return g
        return guilds[0]

    def _on_pick(self, file_name: str, key: str, is_role: bool):
        """Show a popup menu to pick a channel or role from the snapshot."""
        snapshot = self._fetch_snapshot()
        if not snapshot:
            return
        guild = self._get_guild_from_snapshot(snapshot)
        if not guild:
            QtWidgets.QMessageBox.warning(self, "Pick", "Keine Guild-Daten verfügbar.")
            return

        menu = QtWidgets.QMenu(self)
        if is_role:
            roles = list(guild.get("roles") or [])
            if not roles:
                menu.addAction("(keine Rollen gefunden)").setEnabled(False)
            for role in roles:
                rid = role.get("id")
                rname = role.get("name", "unknown")
                action = menu.addAction(f"@ {rname}")
                action.setData((rid, rname))
        else:
            channels = list(guild.get("channels") or [])
            key_upper = str(key).upper()
            if "CATEGORY" in key_upper:
                filtered = [c for c in channels if "category" in str(c.get("type") or "").lower()]
            else:
                filtered = [c for c in channels if "category" not in str(c.get("type") or "").lower()]
            if not filtered:
                menu.addAction("(keine Channels gefunden)").setEnabled(False)
            for channel in filtered:
                cid = channel.get("id")
                cname = channel.get("name", "unknown")
                action = menu.addAction(f"# {cname}")
                action.setData((cid, cname))

        chosen = menu.exec(self.cursor().pos())
        if chosen and chosen.data():
            chosen_id, chosen_name = chosen.data()
            widget_meta = self._fields.get((file_name, key))
            if widget_meta:
                widget_meta[0].setText(str(chosen_id))
            name_lbl = self._name_labels.get((file_name, key))
            if name_lbl:
                name_lbl.setText(chosen_name)
            # Immediately persist the picked ID to the guild config
            self._auto_save_field(file_name, key, chosen_id)

    def _on_create_channel(self, file_name: str, key: str, label: str):
        """Create a new channel on the Discord server and fill in the ID."""
        if not self._guild_id:
            QtWidgets.QMessageBox.warning(
                self, "Create Channel",
                "Keine aktive Guild. Bitte zuerst eine Guild im Dashboard auswählen.",
            )
            return

        ch_type = _channel_type_for_key(key)
        # Suggest a sensible default name from the label
        default_name = label.lower().replace(" ", "-").replace("(", "").replace(")", "")

        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create Channel",
            f"Channel-Name für '{label}':",
            text=default_name,
        )
        if not ok or not name.strip():
            return

        try:
            resp = send_cmd({
                "action": "create_channel",
                "guild_id": str(self._guild_id),
                "channel_name": name.strip(),
                "channel_type": ch_type,
            }, timeout=10.0)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Create Channel", f"Fehler: {exc}")
            return

        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(
                self, "Create Channel",
                f"Channel konnte nicht erstellt werden:\n{resp.get('error', resp)}",
            )
            return

        ch_data = resp.get("channel", {})
        ch_id = ch_data.get("id")
        ch_name = ch_data.get("name", name.strip())

        widget_meta = self._fields.get((file_name, key))
        if widget_meta:
            widget_meta[0].setText(str(ch_id))
        name_lbl = self._name_labels.get((file_name, key))
        if name_lbl:
            name_lbl.setText(ch_name)

        # Immediately persist the new ID to the guild config
        self._auto_save_field(file_name, key, ch_id)

        # Invalidate snapshot cache so new channel appears on next Pick
        self._snapshot_cache = None

        QtWidgets.QMessageBox.information(
            self, "Create Channel",
            f"✅ Channel '{ch_name}' erstellt und gespeichert (ID: {ch_id})",
        )

    def _on_create_role(self, file_name: str, key: str, label: str):
        """Create a new role on the Discord server and fill in the ID."""
        if not self._guild_id:
            QtWidgets.QMessageBox.warning(
                self, "Create Role",
                "Keine aktive Guild. Bitte zuerst eine Guild im Dashboard auswählen.",
            )
            return

        default_name = label.replace("(", "").replace(")", "").strip()

        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create Role",
            f"Rollen-Name für '{label}':",
            text=default_name,
        )
        if not ok or not name.strip():
            return

        try:
            resp = send_cmd({
                "action": "create_role",
                "guild_id": str(self._guild_id),
                "role_name": name.strip(),
            }, timeout=10.0)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Create Role", f"Fehler: {exc}")
            return

        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(
                self, "Create Role",
                f"Rolle konnte nicht erstellt werden:\n{resp.get('error', resp)}",
            )
            return

        role_data = resp.get("role", {})
        role_id = role_data.get("id")
        role_name = role_data.get("name", name.strip())

        widget_meta = self._fields.get((file_name, key))
        if widget_meta:
            widget_meta[0].setText(str(role_id))
        name_lbl = self._name_labels.get((file_name, key))
        if name_lbl:
            name_lbl.setText(role_name)

        # Immediately persist the new ID to the guild config
        self._auto_save_field(file_name, key, role_id)

        # Invalidate snapshot cache so new role appears on next Pick
        self._snapshot_cache = None

        QtWidgets.QMessageBox.information(
            self, "Create Role",
            f"✅ Rolle '{role_name}' erstellt und gespeichert (ID: {role_id})",
        )

    def _add_social_card(self, platform_name: str, platform_key: str,
                         cards_list: list, cards_layout):
        """Create a channel card for the wizard and append it."""
        idx = len(cards_list) + 1

        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.StyledPanel)
        card.setFrameShadow(QtWidgets.QFrame.Raised)
        grid = QtWidgets.QGridLayout(card)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        lbl = QtWidgets.QLabel(f"{platform_name}\nchannel {idx}")
        lbl.setFixedWidth(80)
        lbl.setStyleSheet("font-weight: bold;")
        grid.addWidget(lbl, 0, 0, 2, 1)

        creator_edit = QtWidgets.QLineEdit()
        creator_edit.setPlaceholderText("Creator")
        add_edit = QtWidgets.QLineEdit()
        add_edit.setPlaceholderText("Additional Creator(s)")
        remove_btn = QtWidgets.QPushButton("\u00d7")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setToolTip("Remove this channel entry")
        grid.addWidget(creator_edit, 0, 1)
        grid.addWidget(add_edit, 0, 2, 1, 3)
        grid.addWidget(remove_btn, 0, 5)

        ch_name_edit = QtWidgets.QLineEdit()
        ch_name_edit.setPlaceholderText("Channel Name")
        ch_name_edit.setReadOnly(True)
        ch_id_edit = QtWidgets.QLineEdit()
        ch_id_edit.setPlaceholderText("Channel ID")
        create_btn = QtWidgets.QPushButton("Create")
        create_btn.setFixedWidth(64)
        pick_btn = QtWidgets.QPushButton("Pick...")
        pick_btn.setFixedWidth(64)
        grid.addWidget(ch_name_edit, 1, 1)
        grid.addWidget(ch_id_edit, 1, 2)
        grid.addWidget(create_btn, 1, 3)
        grid.addWidget(pick_btn, 1, 4)

        card_data = {
            "frame": card,
            "label": lbl,
            "creator": creator_edit,
            "additional_creators": add_edit,
            "channel_name": ch_name_edit,
            "channel_id": ch_id_edit,
        }
        cards_list.append(card_data)
        cards_layout.insertWidget(cards_layout.count() - 1, card)

        def _on_remove():
            if card_data in cards_list:
                cards_list.remove(card_data)
            card.setParent(None)
            card.deleteLater()
            for i, c in enumerate(cards_list, 1):
                c["label"].setText(f"{platform_name}\nchannel {i}")
        remove_btn.clicked.connect(_on_remove)

        create_btn.clicked.connect(
            lambda _=False, pk=platform_key, cd=card_data:
                self._on_social_create_channel(pk, cd)
        )
        pick_btn.clicked.connect(
            lambda _=False, pk=platform_key, cd=card_data:
                self._on_social_pick_channel(pk, cd)
        )
        return card_data

    def _on_social_create_channel(self, platform_key: str, card_data: dict):
        """Create a Discord channel and fill the card fields."""
        if not self._guild_id:
            QtWidgets.QMessageBox.warning(
                self, "Create Channel",
                "Keine aktive Guild. Bitte zuerst eine Guild im Dashboard auswählen.",
            )
            return

        creator = (card_data["creator"].text() or "").strip()
        default_name = (
            f"{platform_key.lower()}-{creator.lower()}"
            if creator else f"{platform_key.lower()}-feed"
        )
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create Channel",
            f"Channel-Name:",
            text=default_name,
        )
        if not ok or not name.strip():
            return

        try:
            resp = send_cmd({
                "action": "create_channel",
                "guild_id": str(self._guild_id),
                "channel_name": name.strip(),
                "channel_type": "text",
            }, timeout=10.0)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Create Channel", f"Fehler: {exc}")
            return

        if not resp.get("ok"):
            QtWidgets.QMessageBox.warning(
                self, "Create Channel",
                f"Channel konnte nicht erstellt werden:\n{resp.get('error', resp)}",
            )
            return

        ch_data = resp.get("channel", {})
        ch_id = ch_data.get("id")
        ch_name = ch_data.get("name", name.strip())

        self._snapshot_cache = None
        card_data["channel_name"].setText(ch_name)
        card_data["channel_id"].setText(str(ch_id))

        # Persist immediately
        self._save_social_channels(platform_key)

        QtWidgets.QMessageBox.information(
            self, "Create Channel",
            f"\u2705 Channel '{ch_name}' erstellt und gespeichert (ID: {ch_id})",
        )

    def _on_social_pick_channel(self, platform_key: str, card_data: dict):
        """Pick an existing channel and fill the card fields."""
        if not self._guild_id:
            QtWidgets.QMessageBox.warning(
                self, "Pick Channel",
                "Keine aktive Guild. Bitte zuerst eine Guild im Dashboard auswählen.",
            )
            return

        snapshot = self._fetch_snapshot()
        if not snapshot:
            return
        guild = self._get_guild_from_snapshot(snapshot)
        if not guild:
            QtWidgets.QMessageBox.warning(self, "Pick", "Keine Guild-Daten verfügbar.")
            return

        channels = list(guild.get("channels") or [])
        filtered = [c for c in channels if "category" not in str(c.get("type") or "").lower()]
        menu = QtWidgets.QMenu(self)
        if not filtered:
            menu.addAction("(keine Channels gefunden)").setEnabled(False)
        for ch in filtered:
            action = menu.addAction(f"# {ch.get('name', 'unknown')}")
            action.setData((ch.get("id"), ch.get("name", "unknown")))

        chosen = menu.exec(self.cursor().pos())
        if not chosen or not chosen.data():
            return

        ch_id, ch_name = chosen.data()
        card_data["channel_name"].setText(ch_name)
        card_data["channel_id"].setText(str(ch_id))

        # Persist immediately
        self._save_social_channels(platform_key)

    def _save_social_channels(self, platform_key: str):
        """Persist the CHANNELS list for a platform from the card widgets."""
        try:
            if not hasattr(self, "_social_channel_cards"):
                return
            cards = self._social_channel_cards.get(platform_key, [])
            path = config_json_path(self._repo_root, "social_media.json",
                                    guild_id=self._guild_id)
            cfg = load_json_dict(path)
            if not isinstance(cfg.get(platform_key), dict):
                cfg[platform_key] = {}
            channels = []
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
                if not ch_id_raw:
                    continue
                channels.append({
                    "CREATORS": creators,
                    "CHANNEL_NAME": ch_name,
                    "CHANNEL_ID": int(ch_id_raw) if ch_id_raw.isdigit() else 0,
                })
            cfg[platform_key]["CHANNELS"] = channels
            save_json_deep_merged(path, cfg)
            self._configs.pop("social_media", None)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self, "Save", f"Channels konnten nicht gespeichert werden: {exc}",
            )

    def _auto_save_field(self, file_name: str, key: str, value):
        """Immediately persist a single field value to the guild config file."""
        try:
            path = config_json_path(self._repo_root, f"{file_name}.json",
                                    guild_id=self._guild_id)
            if not path:
                return
            data = {}
            if "." in key:
                _set_nested(data, key, int(value) if value else 0)
            else:
                data[key] = int(value) if value else 0
            # Use deep merge so nested keys like TWITCH.CHANNEL_ID don't
            # destroy sibling keys (ENABLED, USERNAMES, etc.)
            save_json_deep_merged(path, data)
            # Invalidate cached config so next read picks up the change
            self._configs.pop(file_name, None)
        except Exception:
            pass

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
            elif "." in key:
                current = _get_nested(self._cfg(file_name), key)
            else:
                current = self._cfg(file_name).get(key, "")
            if current is None:
                current = ""
            if field_type == "text":
                widget.setPlainText(str(current))
            else:
                widget.setText(str(current))
        # Try to resolve names for existing channel/role IDs
        self._resolve_names_from_snapshot()
        # Load existing social media channel configs
        self._load_existing_social_channels()

    def _resolve_names_from_snapshot(self):
        """Try to resolve channel/role names for IDs already in input fields."""
        try:
            snapshot = self._fetch_snapshot()
        except Exception:
            return
        if not snapshot:
            return
        guild = self._get_guild_from_snapshot(snapshot)
        if not guild:
            return

        channels = {str(c.get("id")): c.get("name", "") for c in (guild.get("channels") or [])}
        roles = {str(r.get("id")): r.get("name", "") for r in (guild.get("roles") or [])}
        all_items = {**channels, **roles}

        for (file_name, key), name_lbl in self._name_labels.items():
            widget_meta = self._fields.get((file_name, key))
            if not widget_meta:
                continue
            current_id = str(widget_meta[0].text() or "").strip()
            if current_id and current_id != "0":
                resolved = all_items.get(current_id, "")
                if resolved:
                    name_lbl.setText(resolved)

    def _load_existing_social_channels(self):
        """Load existing CHANNELS entries and display them as cards."""
        if not hasattr(self, "_social_channel_cards"):
            return
        try:
            cfg = self._cfg("social_media")
        except Exception:
            return
        if not isinstance(cfg, dict):
            return

        # Resolve channel names from snapshot if available
        ch_names: dict[str, str] = {}
        try:
            snapshot = self._fetch_snapshot()
            if snapshot:
                guild = self._get_guild_from_snapshot(snapshot)
                if guild:
                    ch_names = {str(c.get("id")): c.get("name", "")
                                for c in (guild.get("channels") or [])}
        except Exception:
            pass

        for platform_key, cards_list in self._social_channel_cards.items():
            section = cfg.get(platform_key, {})
            if not isinstance(section, dict):
                continue
            channels = section.get("CHANNELS", [])
            if not isinstance(channels, list):
                continue
            cards_layout = self._social_cards_layouts.get(platform_key)
            if cards_layout is None:
                continue
            # Find platform_name from key
            platform_name = {v: k for k, v in _PLATFORM_KEY_MAP.items()}.get(platform_key, platform_key)
            for entry in channels:
                if not isinstance(entry, dict):
                    continue
                card_data = self._add_social_card(
                    platform_name, platform_key, cards_list, cards_layout,
                )
                creators = entry.get("CREATORS", [])
                if isinstance(creators, str):
                    creators = [c.strip() for c in creators.split(",") if c.strip()]
                if creators:
                    card_data["creator"].setText(creators[0])
                    if len(creators) > 1:
                        card_data["additional_creators"].setText(", ".join(creators[1:]))
                ch_id = str(entry.get("CHANNEL_ID", "") or "")
                ch_name = str(entry.get("CHANNEL_NAME", "") or "")
                if ch_id and not ch_name:
                    ch_name = ch_names.get(ch_id, "")
                if ch_id == "0":
                    ch_id = ""
                card_data["channel_name"].setText(ch_name)
                card_data["channel_id"].setText(ch_id)

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

            if "." in key and file_name != "__env__":
                # Nested key — build the nested dict structure
                updates.setdefault(file_name, {})
                _set_nested(updates[file_name], key, value)
            else:
                updates.setdefault(file_name, {})[key] = value
        return updates

    def _save_and_close(self):
        try:
            updates = self._collect_updates()
            env_updates = updates.pop("__env__", None)
            if not self._validate_env_before_save(env_updates):
                return
            # Files with nested keys (dot-notation) need deep merge to
            # preserve sibling keys like ENABLED, CHANNELS, etc.
            _NESTED_FILES = {"social_media"}
            for file_name, data in updates.items():
                path = config_json_path(self._repo_root, f"{file_name}.json", guild_id=self._guild_id)
                if file_name in _NESTED_FILES:
                    save_json_deep_merged(path, data)
                else:
                    save_json_merged(path, data)
            if env_updates is not None:
                save_env_merged(self._repo_root, env_updates)
            # Persist social channel cards (they are not in self._fields)
            if hasattr(self, "_social_channel_cards"):
                for platform_key in self._social_channel_cards:
                    self._save_social_channels(platform_key)
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
                "- APP_ORIGIN / APP_ENV: Frontend-URL und Umgebung (z. B. production)\n"
                "- TWITCH_CLIENT_ID / TWITCH_OAUTH_TOKEN: Twitch Developer Console → App\n"
                "- TWITTER_BEARER_TOKEN: Twitter/X Developer Portal → Bearer Token\n\n"
                "Hinweis: Ohne DISCORD_TOKEN bleibt der Bot offline.\n\n"
                "Discord-Hilfe-Kommandos:\n"
                "- /help (Aliases: /tutorial, /hilfe)\n"
                "- /admin_help (Aliases: /adminhelp, /ahelp)",
            )

        if page_index == 1:
            return (
                "Help • Channels & Roles",
                "Hier setzt du Channel- und Rollen-IDs, gruppiert nach Feature.\n\n"
                "Jede Zeile hat drei Aktionen:\n"
                "• Create — erstellt den Channel/Rolle auf dem Discord Server und speichert die ID sofort\n"
                "• Channel Name / ID — zeigt den aktuell gesetzten Channel\n"
                "• Pick... — wähle einen bestehenden Channel/Rolle und speichert die ID sofort\n\n"
                "Social Media — Pro-Channel + Creator Modell:\n"
                "• Jede Plattform (Twitch, YouTube, Twitter/X, TikTok) hat Channel-Karten.\n"
                "• Jede Karte = ein Discord-Channel + Creator + zusätzliche Creator(s).\n"
                "• 'Additional … Channel' — neue Karte hinzufügen\n"
                "• × — Karte entfernen\n"
                "• Create — neuen Discord-Channel erstellen und in die Karte eintragen\n"
                "• Pick — bestehenden Discord-Channel wählen und eintragen\n\n"
                "Feature-Gruppen:\n"
                "• Welcome & Verification: Channels + Rollen für Begrüßung\n"
                "• Community: Count, Birthdays, Leveling Channels\n"
                "• TempVoice: Join-to-create Hub, Control Panel, Kategorie\n"
                "• Tickets: Kategorie, Log Channel, Support Rolle\n"
                "• Logging: Chat/Member/Mod/Server/Voice Log Channels\n"
                "• Member Count: Voice-Channel für Mitglieder-Anzeige\n"
                "• Notifications: Free Stuff Channel\n"
                "• Social Media: Per-Channel Creator-Zuordnung\n\n"
                "Alle IDs werden sofort beim Create/Pick gespeichert.",
            )

        return (
            "Help",
            "Keine Hilfe für diese Seite verfügbar.",
        )
