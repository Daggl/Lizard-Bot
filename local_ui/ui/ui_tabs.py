from controllers.features.features_controller import FEATURE_DEFS, FEATURE_ORDER
from PySide6 import QtGui, QtWidgets


def build_dashboard_tab(window, tabs: QtWidgets.QTabWidget):
    dash = QtWidgets.QWidget()
    dash_layout = QtWidgets.QVBoxLayout(dash)

    window.status_label = QtWidgets.QLabel("Status: unknown")
    window.status_label.setObjectName("statusLabel")
    dash_layout.addWidget(window.status_label)

    monitor_box = QtWidgets.QGroupBox("Bot Monitor")
    monitor_grid = QtWidgets.QGridLayout(monitor_box)
    monitor_grid.setHorizontalSpacing(12)
    monitor_grid.setVerticalSpacing(6)

    window.mon_ready = QtWidgets.QLabel("—")
    window.mon_user = QtWidgets.QLabel("—")
    window.mon_ping = QtWidgets.QLabel("—")
    window.mon_uptime = QtWidgets.QLabel("—")
    window.mon_cpu = QtWidgets.QLabel("—")
    window.mon_mem = QtWidgets.QLabel("—")
    window.mon_cogs = QtWidgets.QLabel("—")

    monitor_grid.addWidget(QtWidgets.QLabel("Ready:"), 0, 0)
    monitor_grid.addWidget(window.mon_ready, 0, 1)
    monitor_grid.addWidget(QtWidgets.QLabel("User:"), 0, 2)
    monitor_grid.addWidget(window.mon_user, 0, 3)
    monitor_grid.addWidget(QtWidgets.QLabel("Ping:"), 1, 0)
    monitor_grid.addWidget(window.mon_ping, 1, 1)
    monitor_grid.addWidget(QtWidgets.QLabel("Uptime:"), 1, 2)
    monitor_grid.addWidget(window.mon_uptime, 1, 3)
    monitor_grid.addWidget(QtWidgets.QLabel("CPU:"), 2, 0)
    monitor_grid.addWidget(window.mon_cpu, 2, 1)
    monitor_grid.addWidget(QtWidgets.QLabel("Memory:"), 2, 2)
    monitor_grid.addWidget(window.mon_mem, 2, 3)
    monitor_grid.addWidget(QtWidgets.QLabel("Cogs:"), 3, 0)
    monitor_grid.addWidget(window.mon_cogs, 3, 1)

    console_box = QtWidgets.QGroupBox("Live Console")
    console_layout = QtWidgets.QVBoxLayout(console_box)
    window.dash_console = QtWidgets.QPlainTextEdit()
    window.dash_console.setReadOnly(True)
    window.dash_console.setMaximumBlockCount(1200)
    window.dash_console.setPlaceholderText("Start the app via start_all.bat/start_all.py to see terminal output here.")
    console_layout.addWidget(window.dash_console)

    btn_row = QtWidgets.QHBoxLayout()
    window.refresh_btn = QtWidgets.QPushButton("Refresh Status")
    window.reload_btn = QtWidgets.QPushButton("Reload Cogs")
    window.shutdown_btn = QtWidgets.QPushButton("Shutdown Bot")
    window.restart_btn = QtWidgets.QPushButton("Restart Bot + UI")
    window.setup_wizard_btn = QtWidgets.QPushButton("Setup Wizard")

    for w in (window.refresh_btn, window.reload_btn, window.shutdown_btn):
        btn_row.addWidget(w)
    btn_row.addWidget(window.restart_btn)

    tools_box = QtWidgets.QGroupBox("Tools")
    tools_layout = QtWidgets.QHBoxLayout(tools_box)
    tools_layout.addLayout(btn_row)

    # Backup / Restore buttons
    backup_layout = QtWidgets.QHBoxLayout()
    window.backup_configs_btn = QtWidgets.QPushButton("Backup Configs")
    window.restore_configs_btn = QtWidgets.QPushButton("Restore Configs")
    backup_layout.addWidget(window.backup_configs_btn)
    backup_layout.addWidget(window.restore_configs_btn)
    tools_layout.addLayout(backup_layout)

    tools_layout.addStretch()

    language_layout = QtWidgets.QHBoxLayout()
    language_layout.setSpacing(8)
    language_layout.addWidget(QtWidgets.QLabel("Guild:"))
    window.language_guild_combo = QtWidgets.QComboBox()
    window.language_guild_combo.setMinimumWidth(180)
    window.language_guild_combo.addItem("—", None)
    language_layout.addWidget(window.language_guild_combo)
    language_layout.addWidget(QtWidgets.QLabel("Language:"))
    window.language_combo = QtWidgets.QComboBox()
    window.language_combo.setEnabled(False)
    window.language_combo.setMinimumWidth(140)
    window.language_combo.addItem("—", None)
    language_layout.addWidget(window.language_combo)
    tools_layout.addLayout(language_layout)
    dash_layout.addWidget(tools_box)

    test_box = QtWidgets.QGroupBox("Event Tester")
    test_layout = QtWidgets.QHBoxLayout(test_box)
    window.event_test_combo = QtWidgets.QComboBox()
    window.event_test_combo.addItem("--- Test All ---", "testall")
    # --- Test Commands ---
    window.event_test_combo.addItem("Ping (testping)", "testping")
    window.event_test_combo.addItem("Rank (testrank)", "testrank")
    window.event_test_combo.addItem("Count (testcount)", "testcount")
    window.event_test_combo.addItem("Birthday (testbirthday)", "testbirthday")
    window.event_test_combo.addItem("Free Stuff (testfreestuff)", "testfreestuff")
    window.event_test_combo.addItem("Poll (testpoll)", "testpoll")
    window.event_test_combo.addItem("Music (testmusic)", "testmusic")
    window.event_test_combo.addItem("Say (testsay)", "testsay")
    window.event_test_combo.addItem("Level (testlevel)", "testlevel")
    window.event_test_combo.addItem("Level Up (testlevelup)", "testlevelup")
    window.event_test_combo.addItem("Achievement (testachievement)", "testachievement")
    window.event_test_combo.addItem("Log (testlog)", "testlog")
    window.event_test_combo.addItem("Welcome (testwelcome)", "testwelcome")
    window.event_test_combo.addItem("Ticket Panel (testticketpanel)", "testticketpanel")
    window.event_test_combo.addItem("Social Media (testsocials)", "testsocials")
    # --- Regular Commands ---
    window.event_test_combo.addItem("─── Regular Commands ───", "")
    window.event_test_combo.addItem("Rank Card (rank)", "rank")
    window.event_test_combo.addItem("Rank User (rankuser)", "rankuser")
    window.event_test_combo.addItem("Leaderboard", "leaderboard")
    window.event_test_combo.addItem("Give XP (givexp)", "givexp")
    window.event_test_combo.addItem("Add XP (addxp)", "addxp")
    window.event_test_combo.addItem("Give Achievement", "giveachievement")
    window.event_test_combo.addItem("Say", "say")
    window.event_test_combo.addItem("Count Stats", "countstats")
    window.event_test_combo.addItem("Count Top", "counttop")
    window.event_test_combo.addItem("Birthday", "birthday")
    window.event_test_combo.addItem("Birthday Panel", "birthdaypanel")
    window.event_test_combo.addItem("Free Stuff Sources", "freestuffsources")
    window.event_test_combo.addItem("Social Media Sources", "socialsources")
    window.event_test_combo.addItem("Help", "help")
    window.event_test_channel_id = QtWidgets.QLineEdit()
    window.event_test_channel_id.setPlaceholderText("Channel ID (optional)")
    window.event_test_channel_id.setMaximumWidth(220)
    window.run_event_test_btn = QtWidgets.QPushButton("Run Test")
    test_layout.addWidget(QtWidgets.QLabel("Admin Test:"))
    test_layout.addWidget(window.event_test_combo)
    test_layout.addWidget(QtWidgets.QLabel("Channel ID:"))
    test_layout.addWidget(window.event_test_channel_id)
    test_layout.addWidget(window.run_event_test_btn)
    test_layout.addStretch()
    dash_layout.addWidget(monitor_box)
    dash_layout.addWidget(test_box)

    # Compact row: Safe Mode + Help & Links
    compact_footer = QtWidgets.QHBoxLayout()

    safe_box = QtWidgets.QGroupBox("Safe Mode")
    safe_layout = QtWidgets.QHBoxLayout(safe_box)
    window.safe_read_only_chk = QtWidgets.QCheckBox("Nur lesen")
    window.safe_debug_logging_chk = QtWidgets.QCheckBox("Debug logging an")
    window.safe_auto_reload_off_chk = QtWidgets.QCheckBox("Auto reload aus")
    safe_layout.addWidget(window.safe_read_only_chk)
    safe_layout.addWidget(window.safe_debug_logging_chk)
    safe_layout.addWidget(window.safe_auto_reload_off_chk)
    safe_layout.addStretch()
    compact_footer.addWidget(safe_box)

    help_box = QtWidgets.QGroupBox("Help & Links")
    help_layout = QtWidgets.QHBoxLayout(help_box)
    window.tutorial_btn = QtWidgets.QPushButton("Bot Tutorial")
    window.commands_btn = QtWidgets.QPushButton("Commands")
    window.tutorial_btn.setToolTip("Discord help: /help (aliases: /tutorial, /hilfe)")
    window.commands_btn.setToolTip("Admin help: /admin_help (aliases: /adminhelp, /ahelp)")
    help_layout.addWidget(window.setup_wizard_btn)
    help_layout.addWidget(window.tutorial_btn)
    help_layout.addWidget(window.commands_btn)
    help_layout.addStretch()
    compact_footer.addWidget(help_box)

    dash_layout.addLayout(compact_footer)
    dash_layout.addWidget(console_box, 1)

    window.refresh_btn.clicked.connect(window.on_refresh)
    window.reload_btn.clicked.connect(window.on_reload)
    window.tutorial_btn.clicked.connect(window.on_open_bot_tutorial)
    window.commands_btn.clicked.connect(window.on_open_commands_guide)
    window.shutdown_btn.clicked.connect(window.on_shutdown)
    window.restart_btn.clicked.connect(window.on_restart_and_restart_ui)
    window.setup_wizard_btn.clicked.connect(window.on_open_setup_wizard)
    window.run_event_test_btn.clicked.connect(window.on_run_admin_test_command)
    window.backup_configs_btn.clicked.connect(window.on_backup_configs)
    window.restore_configs_btn.clicked.connect(window.on_restore_configs)
    window.event_test_channel_id.editingFinished.connect(window.on_event_test_channel_changed)
    window.safe_read_only_chk.stateChanged.connect(window.on_safe_mode_flags_changed)
    window.safe_debug_logging_chk.stateChanged.connect(window.on_safe_mode_flags_changed)
    window.safe_auto_reload_off_chk.stateChanged.connect(window.on_safe_mode_flags_changed)
    window.language_guild_combo.currentIndexChanged.connect(window.on_language_guild_changed)
    window.language_combo.currentIndexChanged.connect(window.on_language_selection_changed)

    tabs.addTab(dash, "Dashboard")


def build_logs_tab(window, tabs: QtWidgets.QTabWidget):
    logs = QtWidgets.QWidget()
    logs_layout = QtWidgets.QVBoxLayout(logs)
    top_row = QtWidgets.QHBoxLayout()
    window.choose_log_btn = QtWidgets.QPushButton("Choose Log...")
    top_row.addWidget(window.choose_log_btn)
    top_row.addStretch()
    logs_layout.addLayout(top_row)

    # Filter row
    filter_row = QtWidgets.QHBoxLayout()
    filter_row.addWidget(QtWidgets.QLabel("Filter:"))
    window.log_filter_input = QtWidgets.QLineEdit()
    window.log_filter_input.setPlaceholderText("Text filter (e.g. voice, join, message, error...)")
    window.log_filter_input.setMinimumWidth(260)
    filter_row.addWidget(window.log_filter_input, 1)
    window.log_filter_category = QtWidgets.QComboBox()
    window.log_filter_category.setMinimumWidth(160)
    window.log_filter_category.addItem("All Categories", "")
    window.log_filter_category.addItem("Voice", "voice")
    window.log_filter_category.addItem("Message / Chat", "message")
    window.log_filter_category.addItem("Member", "member")
    window.log_filter_category.addItem("Moderation", "mod")
    window.log_filter_category.addItem("Server", "server")
    window.log_filter_category.addItem("Ticket", "ticket")
    window.log_filter_category.addItem("Leveling", "level")
    window.log_filter_category.addItem("Error", "error")
    filter_row.addWidget(window.log_filter_category)
    window.log_filter_apply_btn = QtWidgets.QPushButton("Apply")
    window.log_filter_clear_btn = QtWidgets.QPushButton("Reset")
    filter_row.addWidget(window.log_filter_apply_btn)
    filter_row.addWidget(window.log_filter_clear_btn)
    logs_layout.addLayout(filter_row)

    window.log_text = QtWidgets.QPlainTextEdit()
    window.log_text.setReadOnly(True)
    try:
        window.log_text.setFont(QtGui.QFont("Consolas", 10))
    except Exception:
        pass
    logs_layout.addWidget(window.log_text)

    window.choose_log_btn.clicked.connect(window._choose_log_file)
    window.log_filter_apply_btn.clicked.connect(window._apply_log_filter)
    window.log_filter_clear_btn.clicked.connect(window._clear_log_filter)
    window.log_filter_input.returnPressed.connect(window._apply_log_filter)
    tabs.addTab(logs, "Logs")


def build_configs_tab(window, tabs: QtWidgets.QTabWidget, config_editor_cls):
    window.cfg_editor = config_editor_cls(window)
    tabs.addTab(window.cfg_editor, "Configs")


def build_welcome_and_rank_tabs(window, tabs: QtWidgets.QTabWidget, QtCore):
    def _section_label(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    preview_w = QtWidgets.QWidget()
    pv_layout = QtWidgets.QVBoxLayout(preview_w)
    pv_layout.setContentsMargins(8, 8, 10, 8)
    pv_layout.setSpacing(10)

    pv_top = QtWidgets.QHBoxLayout()
    pv_top.setSpacing(12)
    pv_left = QtWidgets.QVBoxLayout()
    pv_lbl_preview = QtWidgets.QLabel("Preview")
    pv_lbl_preview.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    pv_lbl_preview.setStyleSheet("font-weight:700; font-size:14px; margin-bottom:6px;")
    pv_left.addWidget(pv_lbl_preview)
    window.pv_banner = QtWidgets.QLabel()
    window.pv_banner.setFixedSize(520, 191)
    window.pv_banner.setScaledContents(False)
    pv_left.addWidget(window.pv_banner)
    pv_left.addStretch()
    pv_top.addLayout(pv_left, 0)

    pv_form = QtWidgets.QFormLayout()
    pv_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    pv_form.setFormAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    pv_form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    pv_form.setHorizontalSpacing(10)
    pv_form.setVerticalSpacing(8)
    pv_form.setContentsMargins(0, 0, 18, 0)

    pv_form.addRow(_section_label("General"))
    window.pv_name = QtWidgets.QLineEdit()
    window.pv_banner_path = QtWidgets.QLineEdit()
    window.pv_banner_browse = QtWidgets.QPushButton("Choose...")
    h = QtWidgets.QHBoxLayout()
    h.addWidget(window.pv_banner_path)
    h.addWidget(window.pv_banner_browse)
    pv_form.addRow("Example name:", window.pv_name)
    pv_form.addRow("Banner image:", h)
    pv_banner_hint = QtWidgets.QLabel("Recommended: 1500 × 550 px")
    pv_banner_hint.setStyleSheet("color:#9aa0a6; font-size:11px; margin-top:-4px;")
    pv_form.addRow("", pv_banner_hint)
    window.pv_message = QtWidgets.QPlainTextEdit()
    window.pv_message.setMinimumHeight(150)
    window.pv_message.setMaximumHeight(220)
    window.pv_message.setPlaceholderText("Welcome message template. Use {mention} for mention.")
    pv_form.addRow("Message:", window.pv_message)

    ph_widget = QtWidgets.QWidget()
    ph_grid = QtWidgets.QGridLayout(ph_widget)
    ph_grid.setContentsMargins(0, 0, 0, 0)
    ph_grid.setHorizontalSpacing(8)
    ph_grid.setVerticalSpacing(8)
    window.ph_mention = QtWidgets.QPushButton("{mention}")
    window.ph_rules = QtWidgets.QPushButton("{rules_channel}")
    window.ph_verify = QtWidgets.QPushButton("{verify_channel}")
    window.ph_about = QtWidgets.QPushButton("{aboutme_channel}")
    for _btn in (window.ph_mention, window.ph_rules, window.ph_verify, window.ph_about):
        try:
            _btn.setMinimumHeight(34)
        except Exception:
            pass
    ph_grid.addWidget(window.ph_mention, 0, 0)
    ph_grid.addWidget(window.ph_rules, 0, 1)
    ph_grid.addWidget(window.ph_verify, 0, 2)
    ph_grid.addWidget(window.ph_about, 0, 3)
    pv_form.addRow("Placeholders:", ph_widget)

    window.pv_emoji_picker_btn = QtWidgets.QPushButton("Server Emoji Picker...")
    pv_form.addRow("Server emojis:", window.pv_emoji_picker_btn)

    pv_form.addRow(_section_label("Background"))
    window.pv_bg_mode = QtWidgets.QComboBox()
    window.pv_bg_mode.addItem("Fill (cover)", "cover")
    window.pv_bg_mode.addItem("Fit (contain)", "contain")
    window.pv_bg_mode.addItem("Stretch", "stretch")
    pv_form.addRow("Background mode:", window.pv_bg_mode)

    window.pv_bg_zoom = QtWidgets.QSpinBox()
    window.pv_bg_zoom.setRange(10, 400)
    window.pv_bg_zoom.setValue(100)
    window.pv_bg_zoom.setSuffix(" %")
    window.pv_bg_zoom.setFixedWidth(120)
    pv_form.addRow("Background zoom:", window.pv_bg_zoom)

    bg_pos_row = QtWidgets.QHBoxLayout()
    window.pv_bg_x = QtWidgets.QSpinBox()
    window.pv_bg_x.setRange(-4000, 4000)
    window.pv_bg_x.setSingleStep(10)
    window.pv_bg_x.setFixedWidth(110)
    window.pv_bg_y = QtWidgets.QSpinBox()
    window.pv_bg_y.setRange(-4000, 4000)
    window.pv_bg_y.setSingleStep(10)
    window.pv_bg_y.setFixedWidth(110)
    bg_pos_row.addWidget(QtWidgets.QLabel("X"))
    bg_pos_row.addWidget(window.pv_bg_x)
    bg_pos_row.addSpacing(10)
    bg_pos_row.addWidget(QtWidgets.QLabel("Y"))
    bg_pos_row.addWidget(window.pv_bg_y)
    bg_pos_row.addStretch()
    pv_form.addRow("Background offset:", bg_pos_row)

    pv_form.addRow(_section_label("Typography"))
    window.pv_title = QtWidgets.QLineEdit()
    window.pv_title.setPlaceholderText("WELCOME")
    pv_form.addRow("Banner title:", window.pv_title)

    window.pv_title_font = QtWidgets.QComboBox()
    window.pv_title_font.setEditable(True)
    window.pv_title_font.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
    pv_form.addRow("Title font:", window.pv_title_font)

    window.pv_user_font = QtWidgets.QComboBox()
    window.pv_user_font.setEditable(True)
    window.pv_user_font.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
    pv_form.addRow("Username font:", window.pv_user_font)

    window.pv_title_size = QtWidgets.QSpinBox()
    window.pv_title_size.setRange(8, 400)
    window.pv_title_size.setValue(140)
    window.pv_title_size.setFixedWidth(120)
    pv_form.addRow("Title size:", window.pv_title_size)

    window.pv_user_size = QtWidgets.QSpinBox()
    window.pv_user_size.setRange(8, 300)
    window.pv_user_size.setValue(64)
    window.pv_user_size.setFixedWidth(120)
    pv_form.addRow("Username size:", window.pv_user_size)

    window.pv_title_color = QtWidgets.QLineEdit()
    window.pv_title_color.setPlaceholderText("#FFFFFF")
    window.pv_title_color_pick = QtWidgets.QPushButton("Pick...")
    window.pv_title_color_pick.setFixedWidth(72)
    title_color_row = QtWidgets.QHBoxLayout()
    title_color_row.addWidget(window.pv_title_color, 1)
    title_color_row.addWidget(window.pv_title_color_pick, 0)
    pv_form.addRow("Title color:", title_color_row)

    window.pv_user_color = QtWidgets.QLineEdit()
    window.pv_user_color.setPlaceholderText("#E6E6E6")
    window.pv_user_color_pick = QtWidgets.QPushButton("Pick...")
    window.pv_user_color_pick.setFixedWidth(72)
    user_color_row = QtWidgets.QHBoxLayout()
    user_color_row.addWidget(window.pv_user_color, 1)
    user_color_row.addWidget(window.pv_user_color_pick, 0)
    pv_form.addRow("Username color:", user_color_row)

    pv_form.addRow(_section_label("Position"))
    title_pos_row = QtWidgets.QHBoxLayout()
    window.pv_title_x = QtWidgets.QSpinBox()
    window.pv_title_x.setRange(-2000, 2000)
    window.pv_title_x.setSingleStep(5)
    window.pv_title_x.setFixedWidth(110)
    window.pv_title_y = QtWidgets.QSpinBox()
    window.pv_title_y.setRange(-2000, 2000)
    window.pv_title_y.setSingleStep(5)
    window.pv_title_y.setFixedWidth(110)
    title_pos_row.addWidget(QtWidgets.QLabel("X"))
    title_pos_row.addWidget(window.pv_title_x)
    title_pos_row.addSpacing(10)
    title_pos_row.addWidget(QtWidgets.QLabel("Y"))
    title_pos_row.addWidget(window.pv_title_y)
    title_pos_row.addStretch()
    pv_form.addRow("Title offset:", title_pos_row)

    user_pos_row = QtWidgets.QHBoxLayout()
    window.pv_user_x = QtWidgets.QSpinBox()
    window.pv_user_x.setRange(-2000, 2000)
    window.pv_user_x.setSingleStep(5)
    window.pv_user_x.setFixedWidth(110)
    window.pv_user_y = QtWidgets.QSpinBox()
    window.pv_user_y.setRange(-2000, 2000)
    window.pv_user_y.setSingleStep(5)
    window.pv_user_y.setFixedWidth(110)
    user_pos_row.addWidget(QtWidgets.QLabel("X"))
    user_pos_row.addWidget(window.pv_user_x)
    user_pos_row.addSpacing(10)
    user_pos_row.addWidget(QtWidgets.QLabel("Y"))
    user_pos_row.addWidget(window.pv_user_y)
    user_pos_row.addStretch()
    pv_form.addRow("Username offset:", user_pos_row)

    text_pos_row = QtWidgets.QHBoxLayout()
    window.pv_text_x = QtWidgets.QSpinBox()
    window.pv_text_x.setRange(-2000, 2000)
    window.pv_text_x.setSingleStep(5)
    window.pv_text_x.setFixedWidth(110)
    window.pv_text_y = QtWidgets.QSpinBox()
    window.pv_text_y.setRange(-2000, 2000)
    window.pv_text_y.setSingleStep(5)
    window.pv_text_y.setFixedWidth(110)
    text_pos_row.addWidget(QtWidgets.QLabel("X"))
    text_pos_row.addWidget(window.pv_text_x)
    text_pos_row.addSpacing(10)
    text_pos_row.addWidget(QtWidgets.QLabel("Y"))
    text_pos_row.addWidget(window.pv_text_y)
    text_pos_row.addStretch()
    pv_form.addRow("Text offset:", text_pos_row)

    pos_row = QtWidgets.QHBoxLayout()
    window.pv_avatar_x = QtWidgets.QSpinBox()
    window.pv_avatar_x.setRange(-2000, 2000)
    window.pv_avatar_x.setSingleStep(5)
    window.pv_avatar_x.setFixedWidth(110)
    window.pv_avatar_y = QtWidgets.QSpinBox()
    window.pv_avatar_y.setRange(-2000, 2000)
    window.pv_avatar_y.setSingleStep(5)
    window.pv_avatar_y.setFixedWidth(110)
    pos_row.addWidget(QtWidgets.QLabel("X"))
    pos_row.addWidget(window.pv_avatar_x)
    pos_row.addSpacing(10)
    pos_row.addWidget(QtWidgets.QLabel("Y"))
    pos_row.addWidget(window.pv_avatar_y)
    pos_row.addStretch()
    pv_form.addRow("Avatar offset:", pos_row)

    window.pv_avatar_size = QtWidgets.QSpinBox()
    window.pv_avatar_size.setRange(50, 600)
    window.pv_avatar_size.setValue(360)
    window.pv_avatar_size.setSuffix(" px")
    window.pv_avatar_size.setFixedWidth(120)
    pv_form.addRow("Avatar size:", window.pv_avatar_size)

    window.ph_mention.clicked.connect(lambda: window._insert_placeholder('{mention}'))
    window.ph_rules.clicked.connect(lambda: window._insert_placeholder('{rules_channel}'))
    window.ph_verify.clicked.connect(lambda: window._insert_placeholder('{verify_channel}'))
    window.ph_about.clicked.connect(lambda: window._insert_placeholder('{aboutme_channel}'))

    pv_controls_w = QtWidgets.QWidget()
    pv_controls_w.setLayout(pv_form)
    pv_scroll = QtWidgets.QScrollArea()
    pv_scroll.setWidgetResizable(True)
    pv_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    pv_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    pv_scroll.setContentsMargins(0, 0, 10, 0)
    pv_scroll.setWidget(pv_controls_w)
    pv_top.addWidget(pv_scroll, 1)
    pv_layout.addLayout(pv_top)

    pv_row = QtWidgets.QHBoxLayout()
    window.pv_save = QtWidgets.QPushButton("Save")
    window.pv_save_reload = QtWidgets.QPushButton("Save + Reload")
    window.pv_refresh = QtWidgets.QPushButton("Refresh Preview")
    for _btn in (window.pv_refresh, window.pv_save, window.pv_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    pv_row.addStretch()
    pv_row.addWidget(window.pv_refresh)
    pv_row.addWidget(window.pv_save)
    pv_row.addWidget(window.pv_save_reload)
    pv_layout.addLayout(pv_row)

    tabs.addTab(preview_w, "Welcome")

    rank_w = QtWidgets.QWidget()
    rank_layout = QtWidgets.QVBoxLayout(rank_w)
    rank_layout.setContentsMargins(8, 8, 10, 8)
    rank_layout.setSpacing(10)

    rk_main = QtWidgets.QHBoxLayout()
    rk_main.setSpacing(12)

    rk_left = QtWidgets.QVBoxLayout()
    lbl_preview = QtWidgets.QLabel("Preview")
    lbl_preview.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    lbl_preview.setStyleSheet("font-weight:700; font-size:14px; margin-bottom:6px;")
    rk_left.addWidget(lbl_preview)
    window.rk_image = QtWidgets.QLabel()
    window.rk_image.setFixedSize(520, 191)
    window.rk_image.setScaledContents(False)
    rk_left.addWidget(window.rk_image)
    rk_left.addStretch()

    rk_right = QtWidgets.QVBoxLayout()
    rk_right.setSpacing(10)
    rk_right.setContentsMargins(0, 0, 6, 0)
    rk_controls_w = QtWidgets.QWidget()
    rk_controls_w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    rk_controls_layout = QtWidgets.QVBoxLayout(rk_controls_w)
    rk_controls_layout.setContentsMargins(0, 0, 10, 0)
    rk_controls_layout.setSpacing(8)
    rk_form = QtWidgets.QFormLayout()
    rk_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    rk_form.setFormAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    rk_form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    rk_form.setHorizontalSpacing(10)
    rk_form.setVerticalSpacing(8)
    rk_form.setContentsMargins(0, 0, 18, 0)
    rk_form.addRow(_section_label("General"))
    window.rk_name = QtWidgets.QLineEdit()
    window.rk_bg_path = QtWidgets.QLineEdit()
    window.rk_bg_browse = QtWidgets.QPushButton("Choose...")
    hbg = QtWidgets.QHBoxLayout()
    hbg.addWidget(window.rk_bg_path)
    hbg.addWidget(window.rk_bg_browse)
    rk_form.addRow("Example name:", window.rk_name)
    rk_form.addRow("Background PNG:", hbg)
    rk_bg_hint = QtWidgets.QLabel("Recommended: 1500 × 550 px")
    rk_bg_hint.setStyleSheet("color:#9aa0a6; font-size:11px; margin-top:-4px;")
    rk_form.addRow("", rk_bg_hint)
    rk_form.addRow(_section_label("Background"))
    window.rk_bg_mode = QtWidgets.QComboBox()
    window.rk_bg_mode.addItem("Fill (cover)", "cover")
    window.rk_bg_mode.addItem("Fit (contain)", "contain")
    window.rk_bg_mode.addItem("Stretch", "stretch")
    rk_form.addRow("Background mode:", window.rk_bg_mode)

    window.rk_bg_zoom = QtWidgets.QSpinBox()
    window.rk_bg_zoom.setRange(10, 400)
    window.rk_bg_zoom.setValue(100)
    window.rk_bg_zoom.setSuffix(" %")
    window.rk_bg_zoom.setFixedWidth(120)
    rk_form.addRow("Background zoom:", window.rk_bg_zoom)

    rk_bg_offset_row = QtWidgets.QHBoxLayout()
    window.rk_bg_x = QtWidgets.QSpinBox()
    window.rk_bg_x.setRange(-4000, 4000)
    window.rk_bg_x.setSingleStep(10)
    window.rk_bg_x.setFixedWidth(110)
    window.rk_bg_y = QtWidgets.QSpinBox()
    window.rk_bg_y.setRange(-4000, 4000)
    window.rk_bg_y.setSingleStep(10)
    window.rk_bg_y.setFixedWidth(110)
    rk_bg_offset_row.addWidget(QtWidgets.QLabel("X"))
    rk_bg_offset_row.addWidget(window.rk_bg_x)
    rk_bg_offset_row.addSpacing(10)
    rk_bg_offset_row.addWidget(QtWidgets.QLabel("Y"))
    rk_bg_offset_row.addWidget(window.rk_bg_y)
    rk_bg_offset_row.addStretch()
    rk_form.addRow("Background offset:", rk_bg_offset_row)

    def _make_rank_xy_row():
        row = QtWidgets.QHBoxLayout()
        sx = QtWidgets.QSpinBox()
        sx.setRange(-4000, 4000)
        sx.setSingleStep(5)
        sx.setFixedWidth(110)
        sy = QtWidgets.QSpinBox()
        sy.setRange(-4000, 4000)
        sy.setSingleStep(5)
        sy.setFixedWidth(110)
        row.addWidget(QtWidgets.QLabel("X"))
        row.addWidget(sx)
        row.addSpacing(10)
        row.addWidget(QtWidgets.QLabel("Y"))
        row.addWidget(sy)
        row.addStretch()
        return row, sx, sy

    def _make_rank_font_combo():
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        return combo

    def _make_rank_size_spin(default_value: int):
        spin = QtWidgets.QSpinBox()
        spin.setRange(8, 300)
        spin.setValue(default_value)
        spin.setFixedWidth(120)
        return spin

    def _make_rank_color_row(placeholder: str):
        line = QtWidgets.QLineEdit()
        line.setPlaceholderText(placeholder)
        btn = QtWidgets.QPushButton("Pick...")
        btn.setFixedWidth(72)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(line, 1)
        row.addWidget(btn, 0)
        return row, line, btn

    rk_form.addRow(_section_label("Username"))
    window.rk_username_font = _make_rank_font_combo()
    rk_form.addRow("Font:", window.rk_username_font)
    window.rk_username_size = _make_rank_size_spin(90)
    rk_form.addRow("Size:", window.rk_username_size)
    rk_username_color_row, window.rk_username_color, window.rk_username_color_pick = _make_rank_color_row("#FFFFFF")
    rk_form.addRow("Color:", rk_username_color_row)
    rk_username_pos_row, window.rk_username_x, window.rk_username_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_username_pos_row)

    rk_form.addRow(_section_label("Level Text"))
    window.rk_level_font = _make_rank_font_combo()
    rk_form.addRow("Font:", window.rk_level_font)
    window.rk_level_size = _make_rank_size_spin(60)
    rk_form.addRow("Size:", window.rk_level_size)
    rk_level_color_row, window.rk_level_color, window.rk_level_color_pick = _make_rank_color_row("#C8C8C8")
    rk_form.addRow("Color:", rk_level_color_row)
    rk_level_pos_row, window.rk_level_x, window.rk_level_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_level_pos_row)

    rk_form.addRow(_section_label("XP Text"))
    window.rk_xp_font = _make_rank_font_combo()
    rk_form.addRow("Font:", window.rk_xp_font)
    window.rk_xp_size = _make_rank_size_spin(33)
    rk_form.addRow("Size:", window.rk_xp_size)
    rk_xp_color_row, window.rk_xp_color, window.rk_xp_color_pick = _make_rank_color_row("#C8C8C8")
    rk_form.addRow("Color:", rk_xp_color_row)
    rk_xp_pos_row, window.rk_xp_x, window.rk_xp_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_xp_pos_row)

    rk_form.addRow(_section_label("Messages Text"))
    window.rk_messages_font = _make_rank_font_combo()
    rk_form.addRow("Font:", window.rk_messages_font)
    window.rk_messages_size = _make_rank_size_spin(33)
    rk_form.addRow("Size:", window.rk_messages_size)
    rk_messages_color_row, window.rk_messages_color, window.rk_messages_color_pick = _make_rank_color_row("#C8C8C8")
    rk_form.addRow("Color:", rk_messages_color_row)
    rk_messages_pos_row, window.rk_messages_x, window.rk_messages_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_messages_pos_row)

    rk_form.addRow(_section_label("Voice Text"))
    window.rk_voice_font = _make_rank_font_combo()
    rk_form.addRow("Font:", window.rk_voice_font)
    window.rk_voice_size = _make_rank_size_spin(33)
    rk_form.addRow("Size:", window.rk_voice_size)
    rk_voice_color_row, window.rk_voice_color, window.rk_voice_color_pick = _make_rank_color_row("#C8C8C8")
    rk_form.addRow("Color:", rk_voice_color_row)
    rk_voice_pos_row, window.rk_voice_x, window.rk_voice_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_voice_pos_row)

    rk_form.addRow(_section_label("Achievements Text"))
    window.rk_achievements_font = _make_rank_font_combo()
    rk_form.addRow("Font:", window.rk_achievements_font)
    window.rk_achievements_size = _make_rank_size_spin(33)
    rk_form.addRow("Size:", window.rk_achievements_size)
    rk_achievements_color_row, window.rk_achievements_color, window.rk_achievements_color_pick = _make_rank_color_row("#C8C8C8")
    rk_form.addRow("Color:", rk_achievements_color_row)
    rk_achievements_pos_row, window.rk_achievements_x, window.rk_achievements_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_achievements_pos_row)

    rk_form.addRow(_section_label("Avatar"))
    rk_avatar_pos_row = QtWidgets.QHBoxLayout()
    window.rk_avatar_x = QtWidgets.QSpinBox()
    window.rk_avatar_x.setRange(-4000, 4000)
    window.rk_avatar_x.setSingleStep(5)
    window.rk_avatar_x.setFixedWidth(110)
    window.rk_avatar_y = QtWidgets.QSpinBox()
    window.rk_avatar_y.setRange(-4000, 4000)
    window.rk_avatar_y.setSingleStep(5)
    window.rk_avatar_y.setFixedWidth(110)
    rk_avatar_pos_row.addWidget(QtWidgets.QLabel("X"))
    rk_avatar_pos_row.addWidget(window.rk_avatar_x)
    rk_avatar_pos_row.addSpacing(10)
    rk_avatar_pos_row.addWidget(QtWidgets.QLabel("Y"))
    rk_avatar_pos_row.addWidget(window.rk_avatar_y)
    rk_avatar_pos_row.addStretch()
    rk_form.addRow("Avatar offset:", rk_avatar_pos_row)

    window.rk_avatar_size = QtWidgets.QSpinBox()
    window.rk_avatar_size.setRange(50, 600)
    window.rk_avatar_size.setValue(300)
    window.rk_avatar_size.setSuffix(" px")
    window.rk_avatar_size.setFixedWidth(120)
    rk_form.addRow("Size:", window.rk_avatar_size)

    rk_form.addRow(_section_label("Progress Bar"))
    rk_bar_pos_row, window.rk_bar_x, window.rk_bar_y = _make_rank_xy_row()
    rk_form.addRow("Position:", rk_bar_pos_row)

    rk_bar_size_row = QtWidgets.QHBoxLayout()
    window.rk_bar_width = QtWidgets.QSpinBox()
    window.rk_bar_width.setRange(10, 3000)
    window.rk_bar_width.setValue(900)
    window.rk_bar_width.setFixedWidth(120)
    window.rk_bar_height = QtWidgets.QSpinBox()
    window.rk_bar_height.setRange(4, 500)
    window.rk_bar_height.setValue(38)
    window.rk_bar_height.setFixedWidth(120)
    rk_bar_size_row.addWidget(QtWidgets.QLabel("W"))
    rk_bar_size_row.addWidget(window.rk_bar_width)
    rk_bar_size_row.addSpacing(10)
    rk_bar_size_row.addWidget(QtWidgets.QLabel("H"))
    rk_bar_size_row.addWidget(window.rk_bar_height)
    rk_bar_size_row.addStretch()
    rk_form.addRow("Size:", rk_bar_size_row)

    rk_bar_bg_color_row, window.rk_bar_bg_color, window.rk_bar_bg_color_pick = _make_rank_color_row("#323232")
    rk_form.addRow("Background:", rk_bar_bg_color_row)

    rk_bar_fill_color_row, window.rk_bar_fill_color, window.rk_bar_fill_color_pick = _make_rank_color_row("#8C6EFF")
    rk_form.addRow("Fill color:", rk_bar_fill_color_row)

    rk_controls_layout.addLayout(rk_form)

    info = QtWidgets.QLabel("Preview updates automatically. Use Save + Reload to apply to the bot.")
    info.setWordWrap(True)
    info.setStyleSheet("color:#9aa0a6; font-size:11px; margin-top:8px;")
    rk_controls_layout.addWidget(info)
    rk_controls_layout.addStretch()

    rk_scroll = QtWidgets.QScrollArea()
    rk_scroll.setWidgetResizable(True)
    rk_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    rk_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    rk_scroll.setContentsMargins(0, 0, 10, 0)
    rk_scroll.setWidget(rk_controls_w)
    rk_right.addWidget(rk_scroll, 1)

    rk_buttons = QtWidgets.QHBoxLayout()
    window.rk_refresh = QtWidgets.QPushButton("Refresh Rank")
    window.rk_save = QtWidgets.QPushButton("Save")
    window.rk_save_reload = QtWidgets.QPushButton("Save + Reload")
    for _btn in (window.rk_refresh, window.rk_save, window.rk_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    rk_buttons.addStretch()
    rk_buttons.addWidget(window.rk_refresh)
    rk_buttons.addWidget(window.rk_save)
    rk_buttons.addWidget(window.rk_save_reload)
    rk_right.addLayout(rk_buttons)

    rk_main.addLayout(rk_left, 0)
    rk_main.addLayout(rk_right, 1)
    rank_layout.addLayout(rk_main)

    tabs.addTab(rank_w, "Rankcard")

    leveling_w = QtWidgets.QWidget()
    leveling_layout = QtWidgets.QVBoxLayout(leveling_w)
    leveling_layout.setContentsMargins(8, 8, 10, 8)
    leveling_layout.setSpacing(10)

    lv_scroll = QtWidgets.QScrollArea()
    lv_scroll.setWidgetResizable(True)
    lv_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    lv_content = QtWidgets.QWidget()
    lv_content_layout = QtWidgets.QVBoxLayout(lv_content)

    lv_form = QtWidgets.QFormLayout()
    lv_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    lv_form.setFormAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    lv_form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    lv_form.setHorizontalSpacing(10)
    lv_form.setVerticalSpacing(8)
    lv_form.setContentsMargins(0, 0, 18, 0)

    lv_form.addRow(_section_label("XP Settings"))
    window.lv_xp_per_message = QtWidgets.QSpinBox()
    window.lv_xp_per_message.setRange(1, 10000)
    window.lv_xp_per_message.setValue(15)
    window.lv_xp_per_message.setFixedWidth(140)
    lv_form.addRow("XP per message:", window.lv_xp_per_message)

    window.lv_voice_xp_per_minute = QtWidgets.QSpinBox()
    window.lv_voice_xp_per_minute.setRange(1, 10000)
    window.lv_voice_xp_per_minute.setValue(10)
    window.lv_voice_xp_per_minute.setFixedWidth(140)
    lv_form.addRow("Voice XP per minute:", window.lv_voice_xp_per_minute)

    window.lv_message_cooldown = QtWidgets.QSpinBox()
    window.lv_message_cooldown.setRange(0, 3600)
    window.lv_message_cooldown.setValue(30)
    window.lv_message_cooldown.setSuffix(" s")
    window.lv_message_cooldown.setFixedWidth(140)
    lv_form.addRow("Message cooldown:", window.lv_message_cooldown)

    lv_form.addRow(_section_label("Messages"))
    window.lv_levelup_msg = QtWidgets.QPlainTextEdit()
    window.lv_levelup_msg.setMinimumHeight(96)
    window.lv_levelup_msg.setMaximumHeight(170)
    window.lv_levelup_msg.setPlaceholderText(
        "Use {member_mention}, {member_name}, {member_display_name}, {member_id}, {guild_name}, {level}"
    )
    lv_form.addRow("Level-up message:", window.lv_levelup_msg)

    window.lv_levelup_emoji_picker_btn = QtWidgets.QPushButton("Insert server emoji into level-up message...")
    lv_form.addRow("", window.lv_levelup_emoji_picker_btn)

    window.lv_ph_member_mention = QtWidgets.QPushButton("{member_mention}")
    window.lv_ph_member_name = QtWidgets.QPushButton("{member_name}")
    window.lv_ph_display_name = QtWidgets.QPushButton("{member_display_name}")
    window.lv_ph_member_id = QtWidgets.QPushButton("{member_id}")
    window.lv_ph_guild_name = QtWidgets.QPushButton("{guild_name}")
    window.lv_ph_level = QtWidgets.QPushButton("{level}")

    lv_ph_widget = QtWidgets.QWidget()
    lv_ph_grid = QtWidgets.QGridLayout(lv_ph_widget)
    lv_ph_grid.setContentsMargins(0, 0, 0, 0)
    lv_ph_grid.setHorizontalSpacing(8)
    lv_ph_grid.setVerticalSpacing(8)
    lv_ph_grid.addWidget(window.lv_ph_member_mention, 0, 0)
    lv_ph_grid.addWidget(window.lv_ph_member_name, 0, 1)
    lv_ph_grid.addWidget(window.lv_ph_display_name, 0, 2)
    lv_ph_grid.addWidget(window.lv_ph_member_id, 1, 0)
    lv_ph_grid.addWidget(window.lv_ph_guild_name, 1, 1)
    lv_ph_grid.addWidget(window.lv_ph_level, 1, 2)
    lv_form.addRow("Level placeholders:", lv_ph_widget)

    window.lv_achievement_msg = QtWidgets.QPlainTextEdit()
    window.lv_achievement_msg.setMinimumHeight(86)
    window.lv_achievement_msg.setMaximumHeight(150)
    window.lv_achievement_msg.setPlaceholderText(
        "Use {member_mention}, {member_name}, {member_display_name}, {member_id}, {guild_name}, {achievement_name}"
    )
    lv_form.addRow("Achievement message:", window.lv_achievement_msg)

    window.lv_achievement_emoji_picker_btn = QtWidgets.QPushButton("Insert server emoji into achievement message...")
    lv_form.addRow("", window.lv_achievement_emoji_picker_btn)

    window.av_ph_member_mention = QtWidgets.QPushButton("{member_mention}")
    window.av_ph_member_name = QtWidgets.QPushButton("{member_name}")
    window.av_ph_display_name = QtWidgets.QPushButton("{member_display_name}")
    window.av_ph_member_id = QtWidgets.QPushButton("{member_id}")
    window.av_ph_guild_name = QtWidgets.QPushButton("{guild_name}")
    window.av_ph_achievement_name = QtWidgets.QPushButton("{achievement_name}")
    for _btn in (
        window.lv_ph_member_mention,
        window.lv_ph_member_name,
        window.lv_ph_display_name,
        window.lv_ph_member_id,
        window.lv_ph_guild_name,
        window.lv_ph_level,
        window.av_ph_member_mention,
        window.av_ph_member_name,
        window.av_ph_display_name,
        window.av_ph_member_id,
        window.av_ph_guild_name,
        window.av_ph_achievement_name,
    ):
        try:
            _btn.setMinimumHeight(34)
        except Exception:
            pass

    av_ph_widget = QtWidgets.QWidget()
    av_ph_grid = QtWidgets.QGridLayout(av_ph_widget)
    av_ph_grid.setContentsMargins(0, 0, 0, 0)
    av_ph_grid.setHorizontalSpacing(8)
    av_ph_grid.setVerticalSpacing(8)
    av_ph_grid.addWidget(window.av_ph_member_mention, 0, 0)
    av_ph_grid.addWidget(window.av_ph_member_name, 0, 1)
    av_ph_grid.addWidget(window.av_ph_display_name, 0, 2)
    av_ph_grid.addWidget(window.av_ph_member_id, 1, 0)
    av_ph_grid.addWidget(window.av_ph_guild_name, 1, 1)
    av_ph_grid.addWidget(window.av_ph_achievement_name, 1, 2)
    lv_form.addRow("Achievement placeholders:", av_ph_widget)

    lv_form.addRow(_section_label("Rewards & Achievements"))
    window.lv_rewards_table = QtWidgets.QTableWidget(0, 3)
    window.lv_rewards_table.setHorizontalHeaderLabels(["Level", "Role name", "Role ID"])
    window.lv_rewards_table.verticalHeader().setVisible(False)
    window.lv_rewards_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    window.lv_rewards_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    window.lv_rewards_table.horizontalHeader().setStretchLastSection(True)
    window.lv_rewards_table.setColumnWidth(0, 70)
    window.lv_rewards_table.setColumnWidth(1, 250)
    window.lv_rewards_table.setSortingEnabled(True)
    window.lv_rewards_table.setMinimumHeight(170)
    lv_form.addRow("Level rewards:", window.lv_rewards_table)

    rewards_btns = QtWidgets.QHBoxLayout()
    rewards_btns.setSpacing(8)
    window.lv_rewards_add_btn = QtWidgets.QPushButton("Add reward")
    window.lv_rewards_remove_btn = QtWidgets.QPushButton("Remove selected")
    window.lv_rewards_pick_btn = QtWidgets.QPushButton("Pick...")
    window.lv_rewards_create_btn = QtWidgets.QPushButton("Create")
    window.lv_rewards_pick_btn.setToolTip("Pick an existing role from the server for the selected reward row")
    window.lv_rewards_create_btn.setToolTip("Create a new role on the server for the selected reward row")
    for _b in (window.lv_rewards_add_btn, window.lv_rewards_remove_btn,
               window.lv_rewards_pick_btn, window.lv_rewards_create_btn):
        _b.setMinimumWidth(90)
    rewards_btns.addWidget(window.lv_rewards_add_btn)
    rewards_btns.addWidget(window.lv_rewards_remove_btn)
    rewards_btns.addWidget(window.lv_rewards_pick_btn)
    rewards_btns.addWidget(window.lv_rewards_create_btn)
    rewards_btns.addStretch()
    lv_form.addRow("", rewards_btns)

    window.lv_achievements_table = QtWidgets.QTableWidget(0, 4)
    window.lv_achievements_table.setHorizontalHeaderLabels(["Achievement", "Type", "Value", "Image (URL/Path)"])
    window.lv_achievements_table.verticalHeader().setVisible(False)
    window.lv_achievements_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    window.lv_achievements_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    window.lv_achievements_table.horizontalHeader().setStretchLastSection(True)
    window.lv_achievements_table.setSortingEnabled(True)
    window.lv_achievements_table.setMinimumHeight(220)
    lv_form.addRow("Achievements:", window.lv_achievements_table)

    ach_btns = QtWidgets.QHBoxLayout()
    ach_btns.setSpacing(8)
    window.lv_achievements_add_btn = QtWidgets.QPushButton("Add achievement")
    window.lv_achievements_remove_btn = QtWidgets.QPushButton("Remove selected")
    window.lv_achievements_choose_image_btn = QtWidgets.QPushButton("Choose image...")
    for _b in (window.lv_achievements_add_btn, window.lv_achievements_remove_btn,
               window.lv_achievements_choose_image_btn):
        _b.setMinimumWidth(90)
    ach_btns.addWidget(window.lv_achievements_add_btn)
    ach_btns.addWidget(window.lv_achievements_remove_btn)
    ach_btns.addWidget(window.lv_achievements_choose_image_btn)
    ach_btns.addStretch()
    lv_form.addRow("", ach_btns)

    req_hint = QtWidgets.QLabel("Type supports: messages, voice_time, level, xp • Image supports URL or local path")
    req_hint.setStyleSheet("color:#9aa0a6;")
    lv_form.addRow("", req_hint)

    lv_content_layout.addLayout(lv_form)
    lv_content_layout.addStretch()
    lv_scroll.setWidget(lv_content)
    leveling_layout.addWidget(lv_scroll, 1)

    lv_buttons = QtWidgets.QHBoxLayout()
    window.lv_save = QtWidgets.QPushButton("Save")
    window.lv_save_reload = QtWidgets.QPushButton("Save + Reload")
    for _btn in (window.lv_save, window.lv_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    lv_buttons.addStretch()
    lv_buttons.addWidget(window.lv_save)
    lv_buttons.addWidget(window.lv_save_reload)
    leveling_layout.addLayout(lv_buttons)

    tabs.addTab(leveling_w, "Leveling")

    birthdays_w = QtWidgets.QWidget()
    birthdays_layout = QtWidgets.QVBoxLayout(birthdays_w)
    birthdays_layout.setContentsMargins(8, 8, 10, 8)
    birthdays_layout.setSpacing(10)

    bd_scroll = QtWidgets.QScrollArea()
    bd_scroll.setWidgetResizable(True)
    bd_content = QtWidgets.QWidget()
    bd_content_layout = QtWidgets.QVBoxLayout(bd_content)
    bd_form = QtWidgets.QFormLayout()
    bd_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    bd_form.setFormAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    bd_form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    bd_form.setHorizontalSpacing(10)
    bd_form.setVerticalSpacing(8)

    window.bd_embed_title = QtWidgets.QLineEdit()
    window.bd_embed_title.setPlaceholderText("🎂 Birthday")
    bd_form.addRow("Embed title:", window.bd_embed_title)

    window.bd_embed_description = QtWidgets.QPlainTextEdit()
    window.bd_embed_description.setMinimumHeight(110)
    window.bd_embed_description.setPlaceholderText("🎉 Today is {mention}'s birthday!")
    bd_form.addRow("Embed message:", window.bd_embed_description)

    ph_widget = QtWidgets.QWidget()
    ph_layout = QtWidgets.QGridLayout(ph_widget)
    ph_layout.setContentsMargins(0, 0, 0, 0)
    ph_layout.setHorizontalSpacing(8)
    ph_layout.setVerticalSpacing(8)
    window.bd_ph_mention = QtWidgets.QPushButton("{mention}")
    window.bd_ph_user_name = QtWidgets.QPushButton("{user_name}")
    window.bd_ph_display_name = QtWidgets.QPushButton("{display_name}")
    window.bd_ph_user_id = QtWidgets.QPushButton("{user_id}")
    window.bd_ph_date = QtWidgets.QPushButton("{date}")
    for _btn in (
        window.bd_ph_mention,
        window.bd_ph_user_name,
        window.bd_ph_display_name,
        window.bd_ph_user_id,
        window.bd_ph_date,
    ):
        try:
            _btn.setMinimumHeight(34)
        except Exception:
            pass
    ph_layout.addWidget(window.bd_ph_mention, 0, 0)
    ph_layout.addWidget(window.bd_ph_user_name, 0, 1)
    ph_layout.addWidget(window.bd_ph_display_name, 0, 2)
    ph_layout.addWidget(window.bd_ph_user_id, 1, 0)
    ph_layout.addWidget(window.bd_ph_date, 1, 1)
    bd_form.addRow("Placeholders:", ph_widget)

    window.bd_emoji_picker_btn = QtWidgets.QPushButton("Server Emoji Picker...")
    bd_form.addRow("Server emojis:", window.bd_emoji_picker_btn)

    window.bd_embed_footer = QtWidgets.QLineEdit()
    window.bd_embed_footer.setPlaceholderText("Optional footer")
    bd_form.addRow("Embed footer:", window.bd_embed_footer)

    window.bd_embed_color = QtWidgets.QLineEdit()
    window.bd_embed_color.setPlaceholderText("#F1C40F")
    window.bd_embed_color_pick = QtWidgets.QPushButton("Pick...")
    window.bd_embed_color_pick.setFixedWidth(72)
    bd_color_row = QtWidgets.QHBoxLayout()
    bd_color_row.addWidget(window.bd_embed_color, 1)
    bd_color_row.addWidget(window.bd_embed_color_pick, 0)
    bd_form.addRow("Embed color:", bd_color_row)

    window.bd_role_id = QtWidgets.QLineEdit()
    window.bd_role_id.setPlaceholderText("Discord Role ID (digits)")
    bd_form.addRow("Birthday role ID:", window.bd_role_id)
    bd_role_hint = QtWidgets.QLabel("If set, this role is assigned on the birthday and removed the next day.")
    bd_role_hint.setStyleSheet("color:#9aa0a6; font-size:11px;")
    bd_form.addRow("", bd_role_hint)

    bd_hint = QtWidgets.QLabel("Message is sent as embed once per birthday/day.")
    bd_hint.setStyleSheet("color:#9aa0a6;")
    bd_form.addRow("", bd_hint)

    bd_content_layout.addLayout(bd_form)
    bd_content_layout.addStretch()
    bd_scroll.setWidget(bd_content)
    birthdays_layout.addWidget(bd_scroll, 1)

    bd_buttons = QtWidgets.QHBoxLayout()
    window.bd_save = QtWidgets.QPushButton("Save")
    window.bd_save_reload = QtWidgets.QPushButton("Save + Reload")
    for _btn in (window.bd_save, window.bd_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    bd_buttons.addStretch()
    bd_buttons.addWidget(window.bd_save)
    bd_buttons.addWidget(window.bd_save_reload)
    birthdays_layout.addLayout(bd_buttons)

    tabs.addTab(birthdays_w, "Birthdays")

    window.rk_refresh.clicked.connect(window.on_refresh_rankpreview)
    window.rk_bg_browse.clicked.connect(window._choose_rank_bg)
    window.rk_username_color_pick.clicked.connect(lambda: window._pick_color(window.rk_username_color, "Choose username color"))
    window.rk_level_color_pick.clicked.connect(lambda: window._pick_color(window.rk_level_color, "Choose level color"))
    window.rk_xp_color_pick.clicked.connect(lambda: window._pick_color(window.rk_xp_color, "Choose XP color"))
    window.rk_messages_color_pick.clicked.connect(lambda: window._pick_color(window.rk_messages_color, "Choose messages color"))
    window.rk_voice_color_pick.clicked.connect(lambda: window._pick_color(window.rk_voice_color, "Choose voice color"))
    window.rk_achievements_color_pick.clicked.connect(lambda: window._pick_color(window.rk_achievements_color, "Choose achievements color"))
    window.rk_bar_bg_color_pick.clicked.connect(lambda: window._pick_color(window.rk_bar_bg_color, "Choose bar background color"))
    window.rk_bar_fill_color_pick.clicked.connect(lambda: window._pick_color(window.rk_bar_fill_color, "Choose bar fill color"))
    window.lv_ph_member_mention.clicked.connect(lambda: window._insert_placeholder_into(window.lv_levelup_msg, '{member_mention}'))
    window.lv_ph_member_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_levelup_msg, '{member_name}'))
    window.lv_ph_display_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_levelup_msg, '{member_display_name}'))
    window.lv_ph_member_id.clicked.connect(lambda: window._insert_placeholder_into(window.lv_levelup_msg, '{member_id}'))
    window.lv_ph_guild_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_levelup_msg, '{guild_name}'))
    window.lv_ph_level.clicked.connect(lambda: window._insert_placeholder_into(window.lv_levelup_msg, '{level}'))
    window.av_ph_member_mention.clicked.connect(lambda: window._insert_placeholder_into(window.lv_achievement_msg, '{member_mention}'))
    window.av_ph_member_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_achievement_msg, '{member_name}'))
    window.av_ph_display_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_achievement_msg, '{member_display_name}'))
    window.av_ph_member_id.clicked.connect(lambda: window._insert_placeholder_into(window.lv_achievement_msg, '{member_id}'))
    window.av_ph_guild_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_achievement_msg, '{guild_name}'))
    window.av_ph_achievement_name.clicked.connect(lambda: window._insert_placeholder_into(window.lv_achievement_msg, '{achievement_name}'))
    window.lv_rewards_add_btn.clicked.connect(window.on_leveling_add_reward_row)
    window.lv_rewards_remove_btn.clicked.connect(window.on_leveling_remove_reward_row)
    window.lv_rewards_pick_btn.clicked.connect(window.on_leveling_pick_reward_role)
    window.lv_rewards_create_btn.clicked.connect(window.on_leveling_create_reward_role)
    window.lv_achievements_add_btn.clicked.connect(window.on_leveling_add_achievement_row)
    window.lv_achievements_remove_btn.clicked.connect(window.on_leveling_remove_achievement_row)
    window.lv_achievements_choose_image_btn.clicked.connect(window.on_leveling_choose_achievement_image)
    window.lv_levelup_emoji_picker_btn.clicked.connect(window.on_open_leveling_levelup_emoji_picker)
    window.lv_achievement_emoji_picker_btn.clicked.connect(window.on_open_leveling_achievement_emoji_picker)
    window.lv_save.clicked.connect(lambda: window._save_leveling_settings(reload_after=False))
    window.lv_save_reload.clicked.connect(lambda: window._save_leveling_settings(reload_after=True))
    window.bd_ph_mention.clicked.connect(lambda: window._insert_placeholder_into(window.bd_embed_description, '{mention}'))
    window.bd_ph_user_name.clicked.connect(lambda: window._insert_placeholder_into(window.bd_embed_description, '{user_name}'))
    window.bd_ph_display_name.clicked.connect(lambda: window._insert_placeholder_into(window.bd_embed_description, '{display_name}'))
    window.bd_ph_user_id.clicked.connect(lambda: window._insert_placeholder_into(window.bd_embed_description, '{user_id}'))
    window.bd_ph_date.clicked.connect(lambda: window._insert_placeholder_into(window.bd_embed_description, '{date}'))
    window.bd_emoji_picker_btn.clicked.connect(window.on_open_birthday_emoji_picker)
    window.bd_embed_color_pick.clicked.connect(lambda: window._pick_color(window.bd_embed_color, "Choose birthday embed color"))
    window.bd_save.clicked.connect(lambda: window._save_birthday_settings(reload_after=False))
    window.bd_save_reload.clicked.connect(lambda: window._save_birthday_settings(reload_after=True))
    window.rk_save.clicked.connect(lambda: window._save_rank_preview(reload_after=False))
    window.rk_save_reload.clicked.connect(lambda: window._save_rank_preview(reload_after=True))

    window.pv_banner_browse.clicked.connect(window._choose_banner)
    window.pv_emoji_picker_btn.clicked.connect(window.on_open_welcome_emoji_picker)
    window.pv_title_color_pick.clicked.connect(lambda: window._pick_color(window.pv_title_color, "Choose title color"))
    window.pv_user_color_pick.clicked.connect(lambda: window._pick_color(window.pv_user_color, "Choose username color"))
    window.pv_refresh.clicked.connect(window.on_refresh_preview)
    window.pv_save.clicked.connect(lambda: window._save_preview(reload_after=False))
    window.pv_save_reload.clicked.connect(lambda: window._save_preview(reload_after=True))

    window._preview_debounce = QtCore.QTimer(window)
    window._preview_debounce.setSingleShot(True)
    window._preview_debounce.setInterval(250)
    window._preview_debounce.timeout.connect(window._apply_live_preview)

    window.pv_name.textChanged.connect(lambda: window._preview_debounce.start())
    window.pv_banner_path.textChanged.connect(lambda: window._preview_debounce.start())
    window.pv_message.textChanged.connect(lambda: window._preview_debounce.start())
    window.pv_bg_mode.currentIndexChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_bg_zoom.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_bg_x.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_bg_y.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_title.textChanged.connect(lambda: window._preview_debounce.start())
    window.pv_title_font.currentTextChanged.connect(lambda _t: window._preview_debounce.start())
    window.pv_user_font.currentTextChanged.connect(lambda _t: window._preview_debounce.start())
    window.pv_title_size.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_user_size.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_title_color.textChanged.connect(lambda: window._preview_debounce.start())
    window.pv_user_color.textChanged.connect(lambda: window._preview_debounce.start())
    window.pv_title_x.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_title_y.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_user_x.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_user_y.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_text_x.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_text_y.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_avatar_x.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_avatar_y.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_name.textChanged.connect(window._mark_preview_dirty)
    window.pv_banner_path.textChanged.connect(window._mark_preview_dirty)
    window.pv_message.textChanged.connect(window._mark_preview_dirty)
    window.pv_bg_mode.currentIndexChanged.connect(window._mark_preview_dirty)
    window.pv_bg_zoom.valueChanged.connect(window._mark_preview_dirty)
    window.pv_bg_x.valueChanged.connect(window._mark_preview_dirty)
    window.pv_bg_y.valueChanged.connect(window._mark_preview_dirty)
    window.pv_title.textChanged.connect(window._mark_preview_dirty)
    window.pv_title_font.currentTextChanged.connect(window._mark_preview_dirty)
    window.pv_user_font.currentTextChanged.connect(window._mark_preview_dirty)
    window.pv_title_size.valueChanged.connect(window._mark_preview_dirty)
    window.pv_user_size.valueChanged.connect(window._mark_preview_dirty)
    window.pv_title_color.textChanged.connect(window._mark_preview_dirty)
    window.pv_user_color.textChanged.connect(window._mark_preview_dirty)
    window.pv_title_x.valueChanged.connect(window._mark_preview_dirty)
    window.pv_title_y.valueChanged.connect(window._mark_preview_dirty)
    window.pv_user_x.valueChanged.connect(window._mark_preview_dirty)
    window.pv_user_y.valueChanged.connect(window._mark_preview_dirty)
    window.pv_text_x.valueChanged.connect(window._mark_preview_dirty)
    window.pv_text_y.valueChanged.connect(window._mark_preview_dirty)
    window.pv_avatar_x.valueChanged.connect(window._mark_preview_dirty)
    window.pv_avatar_y.valueChanged.connect(window._mark_preview_dirty)
    window.pv_avatar_size.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.pv_avatar_size.valueChanged.connect(window._mark_preview_dirty)
    window.rk_name.textChanged.connect(lambda: window._preview_debounce.start())
    window.rk_bg_path.textChanged.connect(lambda: window._preview_debounce.start())
    window.rk_bg_mode.currentIndexChanged.connect(lambda _v: window._preview_debounce.start())
    window.rk_bg_zoom.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.rk_bg_x.valueChanged.connect(lambda _v: window._preview_debounce.start())
    window.rk_bg_y.valueChanged.connect(lambda _v: window._preview_debounce.start())

    for _combo in (
        window.rk_username_font,
        window.rk_level_font,
        window.rk_xp_font,
        window.rk_messages_font,
        window.rk_voice_font,
        window.rk_achievements_font,
    ):
        _combo.currentTextChanged.connect(lambda _t: window._preview_debounce.start())

    for _spin in (
        window.rk_username_size,
        window.rk_level_size,
        window.rk_xp_size,
        window.rk_messages_size,
        window.rk_voice_size,
        window.rk_achievements_size,
        window.rk_username_x,
        window.rk_username_y,
        window.rk_level_x,
        window.rk_level_y,
        window.rk_xp_x,
        window.rk_xp_y,
        window.rk_messages_x,
        window.rk_messages_y,
        window.rk_voice_x,
        window.rk_voice_y,
        window.rk_achievements_x,
        window.rk_achievements_y,
        window.rk_avatar_x,
        window.rk_avatar_y,
        window.rk_avatar_size,
        window.rk_bar_x,
        window.rk_bar_y,
        window.rk_bar_width,
        window.rk_bar_height,
    ):
        _spin.valueChanged.connect(lambda _v: window._preview_debounce.start())

    for _line in (
        window.rk_username_color,
        window.rk_level_color,
        window.rk_xp_color,
        window.rk_messages_color,
        window.rk_voice_color,
        window.rk_achievements_color,
        window.rk_bar_bg_color,
        window.rk_bar_fill_color,
    ):
        _line.textChanged.connect(lambda: window._preview_debounce.start())


# =====================================================================
# Free Stuff tab
# =====================================================================

def build_freestuff_tab(window, tabs: QtWidgets.QTabWidget):
    """Build the 'Free Stuff' tab for configuring free game/offer posts."""
    fs = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(fs)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    header = QtWidgets.QLabel("Free Stuff Configuration")
    header.setObjectName("sectionLabel")
    header.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 6px;")
    layout.addWidget(header)

    desc = QtWidgets.QLabel(
        "Configure which free game/software sources the bot monitors.\n"
        "New free items are automatically posted to the configured channel."
    )
    desc.setWordWrap(True)
    desc.setStyleSheet("color: #9AA5B4; font-size: 12px; margin-bottom: 10px;")
    layout.addWidget(desc)

    form = QtWidgets.QFormLayout()
    form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
    form.setHorizontalSpacing(10)
    form.setVerticalSpacing(8)

    window.fs_channel_id = QtWidgets.QLineEdit()
    window.fs_channel_id.setPlaceholderText("Discord Channel ID (digits)")
    window.fs_channel_id.setMaximumWidth(280)
    form.addRow("Channel ID:", window.fs_channel_id)

    sources_box = QtWidgets.QGroupBox("Sources")
    sources_layout = QtWidgets.QVBoxLayout(sources_box)
    sources_layout.setSpacing(4)

    window.fs_source_epic = QtWidgets.QCheckBox("Epic Games Store")
    window.fs_source_epic.setChecked(True)
    window.fs_source_steam = QtWidgets.QCheckBox("Steam")
    window.fs_source_steam.setChecked(True)
    window.fs_source_gog = QtWidgets.QCheckBox("GOG")
    window.fs_source_gog.setChecked(True)
    window.fs_source_humble = QtWidgets.QCheckBox("Humble Bundle")
    window.fs_source_humble.setChecked(True)
    window.fs_source_misc = QtWidgets.QCheckBox("Misc / Other")
    window.fs_source_misc.setChecked(True)

    for chk in (
        window.fs_source_epic,
        window.fs_source_steam,
        window.fs_source_gog,
        window.fs_source_humble,
        window.fs_source_misc,
    ):
        chk.setStyleSheet("font-size: 13px;")
        sources_layout.addWidget(chk)

    form.addRow("", sources_box)

    layout.addLayout(form)

    # Buttons
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    window.fs_save = QtWidgets.QPushButton("Save")
    window.fs_save_reload = QtWidgets.QPushButton("Save + Reload")
    for _btn in (window.fs_save, window.fs_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    btn_row.addWidget(window.fs_save)
    btn_row.addWidget(window.fs_save_reload)
    layout.addLayout(btn_row)

    layout.addStretch()

    # Wire signals
    window.fs_save.clicked.connect(lambda: window._save_freestuff_settings(reload_after=False))
    window.fs_save_reload.clicked.connect(lambda: window._save_freestuff_settings(reload_after=True))

    tabs.addTab(fs, "Free Stuff")


# =====================================================================
# Social Media tab
# =====================================================================

def build_socials_tab(window, tabs: QtWidgets.QTabWidget):
    """Build the 'Social Media' tab with table-based entry management and TikTok support."""
    sm = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(sm)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    header = QtWidgets.QLabel("Social Media Configuration")
    header.setObjectName("sectionLabel")
    header.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 6px;")
    layout.addWidget(header)

    desc = QtWidgets.QLabel(
        "Configure social media feeds. The bot checks every 5 minutes and posts\n"
        "notifications to the configured Discord channels per source.\n"
        "Use the Channel Routes table to send specific creators to different channels."
    )
    desc.setWordWrap(True)
    desc.setStyleSheet("color: #9AA5B4; font-size: 12px; margin-bottom: 10px;")
    layout.addWidget(desc)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll_content = QtWidgets.QWidget()
    scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
    scroll_layout.setSpacing(10)

    def _make_entry_table(parent_layout, col_header):
        """Create a single-column table with Add / Remove buttons."""
        table = QtWidgets.QTableWidget(0, 1)
        table.setHorizontalHeaderLabels([col_header])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setMinimumHeight(90)
        table.setMaximumHeight(150)

        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("+ Add")
        remove_btn = QtWidgets.QPushButton("\u2212 Remove")
        add_btn.setFixedWidth(90)
        remove_btn.setFixedWidth(90)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()

        parent_layout.addWidget(table)
        parent_layout.addLayout(btn_row)

        def _on_add():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
            table.editItem(table.item(row, 0))

        def _on_remove():
            sel = table.currentRow()
            if sel >= 0:
                table.removeRow(sel)

        add_btn.clicked.connect(_on_add)
        remove_btn.clicked.connect(_on_remove)

        return table

    def _make_route_table(parent_layout):
        """Create a 2-column table (Creator, Channel ID) for per-creator routing."""
        lbl = QtWidgets.QLabel("Channel Routes (per-creator → channel):")
        lbl.setStyleSheet("margin-top:6px;")
        parent_layout.addWidget(lbl)

        table = QtWidgets.QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Creator", "Channel ID"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setMinimumHeight(70)
        table.setMaximumHeight(130)

        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("+ Add Route")
        remove_btn = QtWidgets.QPushButton("\u2212 Remove Route")
        add_btn.setFixedWidth(100)
        remove_btn.setFixedWidth(110)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()

        parent_layout.addWidget(table)
        parent_layout.addLayout(btn_row)

        def _on_add():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
            table.editItem(table.item(row, 0))

        def _on_remove():
            sel = table.currentRow()
            if sel >= 0:
                table.removeRow(sel)

        add_btn.clicked.connect(_on_add)
        remove_btn.clicked.connect(_on_remove)

        return table

    # --- Twitch ---
    twitch_box = QtWidgets.QGroupBox("Twitch")
    twitch_vbox = QtWidgets.QVBoxLayout(twitch_box)
    twitch_form = QtWidgets.QFormLayout()
    twitch_form.setHorizontalSpacing(10)
    twitch_form.setVerticalSpacing(6)

    window.sm_twitch_enabled = QtWidgets.QCheckBox("Enabled")
    twitch_form.addRow("", window.sm_twitch_enabled)
    window.sm_twitch_channel_id = QtWidgets.QLineEdit()
    window.sm_twitch_channel_id.setPlaceholderText("Discord Channel ID")
    window.sm_twitch_channel_id.setMaximumWidth(280)
    twitch_form.addRow("Channel ID:", window.sm_twitch_channel_id)
    window.sm_twitch_client_id = QtWidgets.QLineEdit()
    window.sm_twitch_client_id.setPlaceholderText("Twitch App Client ID")
    twitch_form.addRow("Client ID:", window.sm_twitch_client_id)
    window.sm_twitch_oauth = QtWidgets.QLineEdit()
    window.sm_twitch_oauth.setPlaceholderText("Twitch OAuth Token")
    window.sm_twitch_oauth.setEchoMode(QtWidgets.QLineEdit.Password)
    twitch_form.addRow("OAuth Token:", window.sm_twitch_oauth)
    twitch_vbox.addLayout(twitch_form)

    twitch_vbox.addWidget(QtWidgets.QLabel("Monitored Twitch Usernames:"))
    window.sm_twitch_usernames_table = _make_entry_table(twitch_vbox, "Username")
    window.sm_twitch_routes_table = _make_route_table(twitch_vbox)
    scroll_layout.addWidget(twitch_box)

    # --- YouTube ---
    yt_box = QtWidgets.QGroupBox("YouTube")
    yt_vbox = QtWidgets.QVBoxLayout(yt_box)
    yt_form = QtWidgets.QFormLayout()
    yt_form.setHorizontalSpacing(10)
    yt_form.setVerticalSpacing(6)

    window.sm_youtube_enabled = QtWidgets.QCheckBox("Enabled")
    yt_form.addRow("", window.sm_youtube_enabled)
    window.sm_youtube_channel_id = QtWidgets.QLineEdit()
    window.sm_youtube_channel_id.setPlaceholderText("Discord Channel ID")
    window.sm_youtube_channel_id.setMaximumWidth(280)
    yt_form.addRow("Channel ID:", window.sm_youtube_channel_id)
    yt_vbox.addLayout(yt_form)

    yt_vbox.addWidget(QtWidgets.QLabel("Monitored YouTube Channel IDs:"))
    window.sm_youtube_ids_table = _make_entry_table(yt_vbox, "YouTube Channel ID (UCxxxx)")
    window.sm_youtube_routes_table = _make_route_table(yt_vbox)
    scroll_layout.addWidget(yt_box)

    # --- Twitter/X ---
    tw_box = QtWidgets.QGroupBox("Twitter / X")
    tw_vbox = QtWidgets.QVBoxLayout(tw_box)
    tw_form = QtWidgets.QFormLayout()
    tw_form.setHorizontalSpacing(10)
    tw_form.setVerticalSpacing(6)

    window.sm_twitter_enabled = QtWidgets.QCheckBox("Enabled")
    tw_form.addRow("", window.sm_twitter_enabled)
    window.sm_twitter_channel_id = QtWidgets.QLineEdit()
    window.sm_twitter_channel_id.setPlaceholderText("Discord Channel ID")
    window.sm_twitter_channel_id.setMaximumWidth(280)
    tw_form.addRow("Channel ID:", window.sm_twitter_channel_id)
    window.sm_twitter_bearer = QtWidgets.QLineEdit()
    window.sm_twitter_bearer.setPlaceholderText("Twitter API Bearer Token")
    window.sm_twitter_bearer.setEchoMode(QtWidgets.QLineEdit.Password)
    tw_form.addRow("Bearer Token:", window.sm_twitter_bearer)
    tw_vbox.addLayout(tw_form)

    tw_vbox.addWidget(QtWidgets.QLabel("Monitored Twitter Usernames:"))
    window.sm_twitter_usernames_table = _make_entry_table(tw_vbox, "Username")
    window.sm_twitter_routes_table = _make_route_table(tw_vbox)
    scroll_layout.addWidget(tw_box)

    # --- TikTok ---
    tt_box = QtWidgets.QGroupBox("TikTok")
    tt_vbox = QtWidgets.QVBoxLayout(tt_box)
    tt_form = QtWidgets.QFormLayout()
    tt_form.setHorizontalSpacing(10)
    tt_form.setVerticalSpacing(6)

    window.sm_tiktok_enabled = QtWidgets.QCheckBox("Enabled")
    tt_form.addRow("", window.sm_tiktok_enabled)
    window.sm_tiktok_channel_id = QtWidgets.QLineEdit()
    window.sm_tiktok_channel_id.setPlaceholderText("Discord Channel ID")
    window.sm_tiktok_channel_id.setMaximumWidth(280)
    tt_form.addRow("Channel ID:", window.sm_tiktok_channel_id)
    tt_vbox.addLayout(tt_form)

    tt_vbox.addWidget(QtWidgets.QLabel("Monitored TikTok Usernames (without @):"))
    window.sm_tiktok_usernames_table = _make_entry_table(tt_vbox, "Username")
    window.sm_tiktok_routes_table = _make_route_table(tt_vbox)
    scroll_layout.addWidget(tt_box)

    scroll_layout.addStretch()
    scroll.setWidget(scroll_content)
    layout.addWidget(scroll, 1)

    # Buttons
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    window.sm_save = QtWidgets.QPushButton("Save")
    window.sm_save_reload = QtWidgets.QPushButton("Save + Reload")
    for _btn in (window.sm_save, window.sm_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    btn_row.addWidget(window.sm_save)
    btn_row.addWidget(window.sm_save_reload)
    layout.addLayout(btn_row)

    # Wire signals
    window.sm_save.clicked.connect(lambda: window._save_socials_settings(reload_after=False))
    window.sm_save_reload.clicked.connect(lambda: window._save_socials_settings(reload_after=True))

    tabs.addTab(sm, "Social Media")


# =====================================================================
# Welcome DM tab
# =====================================================================

def build_welcome_dm_tab(window, tabs: QtWidgets.QTabWidget):
    """Build the 'Welcome DM' tab for configuring DMs sent to new members."""
    wdm = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(wdm)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    header = QtWidgets.QLabel("Welcome DM Configuration")
    header.setObjectName("sectionLabel")
    header.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 6px;")
    layout.addWidget(header)

    desc = QtWidgets.QLabel(
        "Configure a private message sent to new members when they join.\n"
        "Supports placeholders and an optional embed."
    )
    desc.setWordWrap(True)
    desc.setStyleSheet("color: #9AA5B4; font-size: 12px; margin-bottom: 10px;")
    layout.addWidget(desc)

    form = QtWidgets.QFormLayout()
    form.setHorizontalSpacing(10)
    form.setVerticalSpacing(8)

    window.wdm_enabled = QtWidgets.QCheckBox("Enabled")
    form.addRow("", window.wdm_enabled)

    window.wdm_message = QtWidgets.QPlainTextEdit()
    window.wdm_message.setMinimumHeight(90)
    window.wdm_message.setMaximumHeight(150)
    window.wdm_message.setPlaceholderText(
        "Welcome {user_name} to {guild_name}! We now have {member_count} members."
    )
    form.addRow("Message:", window.wdm_message)

    # Placeholder buttons
    ph_widget = QtWidgets.QWidget()
    ph_grid = QtWidgets.QGridLayout(ph_widget)
    ph_grid.setContentsMargins(0, 0, 0, 0)
    ph_grid.setHorizontalSpacing(8)
    ph_grid.setVerticalSpacing(8)
    window.wdm_ph_mention = QtWidgets.QPushButton("{mention}")
    window.wdm_ph_user_name = QtWidgets.QPushButton("{user_name}")
    window.wdm_ph_display_name = QtWidgets.QPushButton("{display_name}")
    window.wdm_ph_user_id = QtWidgets.QPushButton("{user_id}")
    window.wdm_ph_guild_name = QtWidgets.QPushButton("{guild_name}")
    window.wdm_ph_member_count = QtWidgets.QPushButton("{member_count}")
    for _btn in (
        window.wdm_ph_mention, window.wdm_ph_user_name,
        window.wdm_ph_display_name, window.wdm_ph_user_id,
        window.wdm_ph_guild_name, window.wdm_ph_member_count,
    ):
        try:
            _btn.setMinimumHeight(34)
        except Exception:
            pass
    ph_grid.addWidget(window.wdm_ph_mention, 0, 0)
    ph_grid.addWidget(window.wdm_ph_user_name, 0, 1)
    ph_grid.addWidget(window.wdm_ph_display_name, 0, 2)
    ph_grid.addWidget(window.wdm_ph_user_id, 1, 0)
    ph_grid.addWidget(window.wdm_ph_guild_name, 1, 1)
    ph_grid.addWidget(window.wdm_ph_member_count, 1, 2)
    form.addRow("Placeholders:", ph_widget)

    window.wdm_embed_title = QtWidgets.QLineEdit()
    window.wdm_embed_title.setPlaceholderText("Optional embed title")
    form.addRow("Embed title:", window.wdm_embed_title)

    window.wdm_embed_description = QtWidgets.QPlainTextEdit()
    window.wdm_embed_description.setMinimumHeight(80)
    window.wdm_embed_description.setMaximumHeight(140)
    window.wdm_embed_description.setPlaceholderText("Optional embed description (supports placeholders)")
    form.addRow("Embed description:", window.wdm_embed_description)

    window.wdm_embed_color = QtWidgets.QLineEdit()
    window.wdm_embed_color.setPlaceholderText("#5865F2")
    window.wdm_embed_color.setMaximumWidth(140)
    form.addRow("Embed color:", window.wdm_embed_color)

    layout.addLayout(form)
    layout.addStretch()

    # Wire placeholder buttons to insert into message field
    def _insert_ph(text):
        cursor = window.wdm_message.textCursor()
        cursor.insertText(text)
        window.wdm_message.setFocus()

    window.wdm_ph_mention.clicked.connect(lambda: _insert_ph("{mention}"))
    window.wdm_ph_user_name.clicked.connect(lambda: _insert_ph("{user_name}"))
    window.wdm_ph_display_name.clicked.connect(lambda: _insert_ph("{display_name}"))
    window.wdm_ph_user_id.clicked.connect(lambda: _insert_ph("{user_id}"))
    window.wdm_ph_guild_name.clicked.connect(lambda: _insert_ph("{guild_name}"))
    window.wdm_ph_member_count.clicked.connect(lambda: _insert_ph("{member_count}"))

    # Buttons
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    window.wdm_save = QtWidgets.QPushButton("Save")
    window.wdm_save_reload = QtWidgets.QPushButton("Save + Reload")
    for _btn in (window.wdm_save, window.wdm_save_reload):
        try:
            _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
            _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
    btn_row.addWidget(window.wdm_save)
    btn_row.addWidget(window.wdm_save_reload)
    layout.addLayout(btn_row)

    # Wire signals
    window.wdm_save.clicked.connect(lambda: window._save_welcome_dm_settings(reload_after=False))
    window.wdm_save_reload.clicked.connect(lambda: window._save_welcome_dm_settings(reload_after=True))

    tabs.addTab(wdm, "Welcome DM")


# =====================================================================
# Purge tab
# =====================================================================

def build_purge_tab(window, tabs: QtWidgets.QTabWidget):
    """Build the 'Purge' tab for bulk-deleting a user's messages."""
    purge = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(purge)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    # ---- description ----
    desc = QtWidgets.QLabel(
        "Delete all messages from a specific user in a given time range.\n"
        "The bot must have Manage Messages permission in the target channels."
    )
    desc.setWordWrap(True)
    desc.setStyleSheet("color:#aaa; margin-bottom:6px;")
    layout.addWidget(desc)

    # ---- Guild selector ----
    guild_row = QtWidgets.QHBoxLayout()
    guild_row.addWidget(QtWidgets.QLabel("Guild:"))
    window.purge_guild_combo = QtWidgets.QComboBox()
    window.purge_guild_combo.setMinimumWidth(260)
    window.purge_guild_combo.addItem("— select guild —", None)
    guild_row.addWidget(window.purge_guild_combo)
    window.purge_refresh_btn = QtWidgets.QPushButton("Refresh Guilds")
    guild_row.addWidget(window.purge_refresh_btn)
    guild_row.addStretch()
    layout.addLayout(guild_row)

    # ---- Channel selector ----
    ch_row = QtWidgets.QHBoxLayout()
    ch_row.addWidget(QtWidgets.QLabel("Channel:"))
    window.purge_channel_combo = QtWidgets.QComboBox()
    window.purge_channel_combo.setMinimumWidth(260)
    window.purge_channel_combo.addItem("— all text channels —", "__ALL__")
    ch_row.addWidget(window.purge_channel_combo)
    ch_row.addStretch()
    layout.addLayout(ch_row)

    # ---- User ID ----
    user_row = QtWidgets.QHBoxLayout()
    user_row.addWidget(QtWidgets.QLabel("User ID:"))
    window.purge_user_id = QtWidgets.QLineEdit()
    window.purge_user_id.setPlaceholderText("e.g. 123456789012345678")
    window.purge_user_id.setMaximumWidth(260)
    user_row.addWidget(window.purge_user_id)
    user_row.addStretch()
    layout.addLayout(user_row)

    # ---- Hours ----
    hours_row = QtWidgets.QHBoxLayout()
    hours_row.addWidget(QtWidgets.QLabel("Hours:"))
    window.purge_hours = QtWidgets.QSpinBox()
    window.purge_hours.setRange(1, 8760)
    window.purge_hours.setValue(24)
    window.purge_hours.setSuffix(" h")
    window.purge_hours.setToolTip("Delete messages from the last N hours (1 – 8760 = 365 days)")
    window.purge_hours.setMaximumWidth(140)
    hours_row.addWidget(window.purge_hours)
    hours_row.addStretch()
    layout.addLayout(hours_row)

    # ---- Execute button ----
    btn_row = QtWidgets.QHBoxLayout()
    window.purge_execute_btn = QtWidgets.QPushButton("🗑  Purge Messages")
    window.purge_execute_btn.setStyleSheet(
        "QPushButton { background:#c0392b; color:white; font-weight:bold; padding:8px 24px; border-radius:4px; }"
        "QPushButton:hover { background:#e74c3c; }"
    )
    btn_row.addWidget(window.purge_execute_btn)
    btn_row.addStretch()
    layout.addLayout(btn_row)

    # ---- Progress label ----
    window.purge_progress_label = QtWidgets.QLabel("")
    window.purge_progress_label.setWordWrap(True)
    window.purge_progress_label.setStyleSheet("color:#e2b714; font-size:13px; margin-top:4px;")
    layout.addWidget(window.purge_progress_label)

    # ---- time estimate info ----
    info = QtWidgets.QLabel(
        "⏱  Time estimate: ~2 min for 12k messages < 14 days (bulk-delete).\n"
        "    Messages older than 14 days: ~1 message per 0.35s → 12k ≈ 70 min."
    )
    info.setWordWrap(True)
    info.setStyleSheet("color:#666; font-size:11px; margin-top:8px;")
    layout.addWidget(info)

    layout.addStretch()

    # ---- wire signals ----
    window.purge_refresh_btn.clicked.connect(window.on_purge_refresh_guilds)
    window.purge_guild_combo.currentIndexChanged.connect(window._on_purge_guild_changed)
    window.purge_execute_btn.clicked.connect(window.on_purge_execute)

    tabs.addTab(purge, "Purge")


def build_features_tab(window, tabs: QtWidgets.QTabWidget):
    features = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(features)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(6)

    header = QtWidgets.QLabel("Feature Toggles (per Guild)")
    header.setObjectName("sectionLabel")
    header.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 6px;")
    layout.addWidget(header)

    hint = QtWidgets.QLabel(
        "Enable or disable individual bot features for the currently selected guild.\n"
        "Changes take effect after saving and reloading."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet("color: #9AA5B4; font-size: 12px; margin-bottom: 10px;")
    layout.addWidget(hint)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; }")
    scroll_content = QtWidgets.QWidget()
    scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
    scroll_layout.setSpacing(4)

    for key in FEATURE_ORDER:
        info = FEATURE_DEFS.get(key, {})
        label_text = info.get("label", key)
        desc_text = info.get("desc", "")

        row = QtWidgets.QHBoxLayout()
        chk = QtWidgets.QCheckBox(label_text)
        chk.setChecked(True)
        chk.setMinimumWidth(180)
        chk.setStyleSheet("font-size: 13px; font-weight: 600;")
        setattr(window, f"feat_chk_{key}", chk)
        row.addWidget(chk)

        desc_label = QtWidgets.QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #8B95A5; font-size: 11px;")
        row.addWidget(desc_label, 1)
        scroll_layout.addLayout(row)

    scroll_layout.addStretch()
    scroll.setWidget(scroll_content)
    layout.addWidget(scroll, 1)

    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    window.feat_save_btn = QtWidgets.QPushButton("Save Features")
    window.feat_save_btn.setMinimumWidth(160)
    btn_row.addWidget(window.feat_save_btn)
    layout.addLayout(btn_row)

    window.feat_save_btn.clicked.connect(window._save_features_config)
    tabs.addTab(features, "Features")
