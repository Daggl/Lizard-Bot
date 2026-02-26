from PySide6 import QtWidgets


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
    window.restart_btn = QtWidgets.QPushButton("Restart Bot & UI")

    for w in (window.refresh_btn, window.reload_btn, window.shutdown_btn):
        btn_row.addWidget(w)
    btn_row.addWidget(window.restart_btn)

    tools_box = QtWidgets.QGroupBox("Tools")
    tools_layout = QtWidgets.QHBoxLayout(tools_box)
    tools_layout.addLayout(btn_row)
    tools_layout.addStretch()
    dash_layout.addWidget(tools_box)
    dash_layout.addWidget(monitor_box)
    dash_layout.addWidget(console_box)

    dash_layout.addStretch()

    help_box = QtWidgets.QGroupBox("Help")
    help_layout = QtWidgets.QHBoxLayout(help_box)
    window.tutorial_btn = QtWidgets.QPushButton("Bot Tutorial")
    window.commands_btn = QtWidgets.QPushButton("Commands")
    help_layout.addWidget(window.tutorial_btn)
    help_layout.addWidget(window.commands_btn)
    help_layout.addStretch()
    dash_layout.addWidget(help_box)

    window.refresh_btn.clicked.connect(window.on_refresh)
    window.reload_btn.clicked.connect(window.on_reload)
    window.tutorial_btn.clicked.connect(window.on_open_bot_tutorial)
    window.commands_btn.clicked.connect(window.on_open_commands_guide)
    window.shutdown_btn.clicked.connect(window.on_shutdown)
    window.restart_btn.clicked.connect(window.on_restart_and_restart_ui)

    tabs.addTab(dash, "Dashboard")


def build_logs_tab(window, tabs: QtWidgets.QTabWidget):
    logs = QtWidgets.QWidget()
    logs_layout = QtWidgets.QVBoxLayout(logs)
    top_row = QtWidgets.QHBoxLayout()
    window.choose_log_btn = QtWidgets.QPushButton("Choose Log...")
    window.clear_log_btn = QtWidgets.QPushButton("Clear")
    top_row.addWidget(window.choose_log_btn)
    top_row.addWidget(window.clear_log_btn)
    top_row.addStretch()
    logs_layout.addLayout(top_row)

    window.log_text = QtWidgets.QPlainTextEdit()
    window.log_text.setReadOnly(True)
    logs_layout.addWidget(window.log_text)

    window.choose_log_btn.clicked.connect(window._choose_log_file)
    window.clear_log_btn.clicked.connect(lambda: window.log_text.clear())
    tabs.addTab(logs, "Logs")


def build_configs_tab(window, tabs: QtWidgets.QTabWidget, config_editor_cls):
    window.cfg_editor = config_editor_cls(window)
    tabs.addTab(window.cfg_editor, "Configs")
