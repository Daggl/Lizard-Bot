"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""



import os
import sys
from datetime import datetime

from config.config_editor import ConfigEditor
from controllers.core.lifecycle_controller import LifecycleControllerMixin
from controllers.core.runtime_core_controller import RuntimeCoreControllerMixin
from controllers.features.birthdays_controller import BirthdaysControllerMixin
from controllers.features.leveling_controller import LevelingControllerMixin
from controllers.monitoring.dashboard_controller import \
    DashboardControllerMixin
from controllers.monitoring.logs_controller import LogsControllerMixin
from controllers.ui.admin_controller import AdminControllerMixin
from controllers.ui.emoji_controller import EmojiControllerMixin
from controllers.ui.preview_api_controller import PreviewApiControllerMixin
from controllers.ui.preview_controller import PreviewControllerMixin
from core.exception_handler import install_exception_hook
from core.repo_paths import get_repo_root
from core.runtime import run_main_window
from core.startup_trace import write_startup_trace
# HTML embed removed; no html module required
from PySide6 import QtCore, QtWidgets
from ui.ui_tabs import (build_configs_tab, build_dashboard_tab, build_logs_tab,
                        build_welcome_and_rank_tabs)

write_startup_trace()


install_exception_hook()


class MainWindow(LevelingControllerMixin, BirthdaysControllerMixin, LogsControllerMixin, DashboardControllerMixin, AdminControllerMixin, EmojiControllerMixin, PreviewControllerMixin, PreviewApiControllerMixin, LifecycleControllerMixin, RuntimeCoreControllerMixin, QtWidgets.QMainWindow):
    _async_done = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lizard UI")
        self.resize(1220, 780)
        self.setMinimumSize(1160, 740)
        # Repo root path for data/logs tracking
        self._repo_root = get_repo_root()
        # Active guild ID for per-guild config loading/saving (None = global)
        self._active_guild_id = None

        # central tabs
        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)

        build_dashboard_tab(self, tabs)
        build_logs_tab(self, tabs)
        build_configs_tab(self, tabs, ConfigEditor)

        build_welcome_and_rank_tabs(self, tabs, QtCore)

        self.setCentralWidget(tabs)

        # connect async result dispatcher before any background requests
        try:
            self._async_done.connect(self._process_async_result)
        except Exception:
            pass

        # styling
        self.setStyleSheet("""
        QWidget {
            font-family: Segoe UI, Arial, Helvetica, sans-serif;
            background: #121417;
            color: #E7EBF3;
        }
        QMainWindow {
            background: #121417;
        }
        QTabWidget::pane {
            border: 1px solid #2A3240;
            border-radius: 10px;
            background: #171C23;
            top: -1px;
        }
        QTabBar::tab {
            background: #1B212A;
            color: #C9D2E3;
            border: 1px solid #2A3240;
            padding: 8px 14px;
            margin-right: 6px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            min-width: 90px;
        }
        QTabBar::tab:selected {
            background: #283246;
            color: #FFFFFF;
            border-color: #4A76C9;
        }
        QTabBar::tab:hover {
            background: #222A35;
        }
        #statusLabel {
            font-weight: 700;
            font-size: 14px;
            color: #D8E5FF;
            padding: 8px 10px;
            background: #1B2230;
            border: 1px solid #334258;
            border-radius: 8px;
        }
        QPushButton {
            background: #222A35;
            color: #F0F4FF;
            border: 1px solid #334258;
            border-radius: 8px;
            padding: 7px 12px;
        }
        QPushButton:hover {
            background: #2A3544;
            border-color: #4A76C9;
        }
        QPushButton:pressed {
            background: #1A212B;
        }
        QPushButton:disabled {
            color: #7D8798;
            border-color: #3A4352;
            background: #1A1F27;
        }
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {
            background: #0F141B;
            color: #EAF1FF;
            border: 1px solid #334258;
            border-radius: 7px;
            selection-background-color: #3B5D9A;
        }
        QLineEdit, QComboBox {
            min-height: 28px;
            padding: 4px 8px;
        }
        QPlainTextEdit, QTextEdit {
            padding: 8px;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 1px solid #5D8BE0;
            background: #101722;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QComboBox QAbstractItemView {
            background: #171D26;
            color: #EAF1FF;
            border: 1px solid #334258;
            selection-background-color: #314C7E;
        }
        QScrollBar:vertical {
            background: #151A22;
            width: 10px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #354257;
            border-radius: 5px;
            min-height: 24px;
        }
        QScrollBar::handle:vertical:hover {
            background: #496084;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QLabel {
            color: #DCE5F5;
        }
        QLabel#sectionLabel {
            color: #8FB6FF;
            font-weight: 700;
            padding-top: 8px;
            padding-bottom: 2px;
        }
        QStatusBar {
            background: #151B24;
            color: #C8D5EE;
            border-top: 1px solid #2A3240;
        }
        QGroupBox {
            border: 1px solid #2C3542;
            border-radius: 8px;
            margin-top: 8px;
            padding: 10px;
        }
        """)

        # timers
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.timeout.connect(self.on_refresh)
        self.status_timer.start(3000)

        self.log_timer = QtCore.QTimer(self)
        # keep a fallback timer but increase interval to reduce load
        self.log_timer.timeout.connect(self.tail_logs)
        self.log_timer.start(5000)

        # background poller for logs (db or tail); created when a log is chosen
        self._log_poller = None
        self._status_inflight = False

        # initialize
        self._log_fp = None
        self._active_log_path = None
        self._active_log_mode = "file"
        # sqlite support
        self._db_conn = None
        self._db_table = None
        self._db_last_rowid = 0
        self._tracked_fp = None
        # data URL for a banner received via the Refresh Preview button
        self._preview_banner_data_url = None
        # rank preview persisted settings
        self._rank_config = {}
        self._rank_config_path = None
        self._preview_dirty = False
        self._preview_syncing = False
        self._title_font_lookup = {}
        self._dash_console_path = os.path.join(self._repo_root, "data", "logs", "start_all_console.log")
        self._dash_console_pos = 0
        self._ui_settings = {}
        self._language_overview = {}
        self._language_overview_attempts = 0
        try:
            self._load_title_font_choices()
            self._load_user_font_choices()
            self._load_rank_name_font_choices()
            self._load_rank_info_font_choices()
        except Exception:
            pass
        self._open_log()
        self.on_refresh()
        # load rank config if present
        try:
            self._load_rank_config()
        except Exception:
            pass
        try:
            self._load_leveling_config()
        except Exception:
            pass
        try:
            self._load_birthdays_config()
        except Exception:
            pass
        try:
            self._load_ui_settings()
        except Exception:
            pass
        try:
            self.request_language_overview()
        except Exception:
            pass
        self._init_status_helper()
        self._init_startup_marker()
        self._init_timers()

    def _reload_guild_configs(self):
        """Reload all guild-scoped configs and previews for the active guild."""
        try:
            self._load_rank_config()
        except Exception:
            pass
        try:
            self._load_leveling_config()
        except Exception:
            pass
        try:
            self._load_birthdays_config()
        except Exception:
            pass
        try:
            self._preview_dirty = False
            self._preview_banner_data_url = None
            self.update_preview()
        except Exception:
            pass
        # Refresh the ConfigEditor file list for the new guild
        try:
            if hasattr(self, "cfg_editor") and self.cfg_editor is not None:
                self.cfg_editor.refresh_list()
        except Exception:
            pass
        # Re-open logs with guild filter
        try:
            self._open_log()
        except Exception:
            pass
        try:
            self._set_status(f"Loaded configs for guild {self._active_guild_id or 'global'}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Init helpers (called once during __init__, not per guild switch)
    # ------------------------------------------------------------------

    def _init_status_helper(self):
        """Create the ``_set_status`` convenience method."""
        def _set_status(msg: str):
            try:
                try:
                    self.status_label.setText(msg)
                except Exception:
                    pass
                try:
                    self.statusBar().showMessage(msg, 5000)
                except Exception:
                    pass
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
        self._set_status = _set_status

    def _init_startup_marker(self):
        """Write a startup marker so the user can confirm the UI launched."""
        try:
            start_dir = os.path.join(self._repo_root, "data", "logs")
            os.makedirs(start_dir, exist_ok=True)
            with open(os.path.join(start_dir, "ui_start.log"), "a", encoding="utf-8") as fh:
                fh.write(f"UI started at {datetime.now().isoformat()}\n")
        except Exception:
            pass

    def _init_timers(self):
        """Start heartbeat and console-poller timers."""
        try:
            self._alive_timer = QtCore.QTimer(self)
            self._alive_timer.timeout.connect(
                lambda: self.statusBar().showMessage(
                    f"Alive {datetime.now().strftime('%H:%M:%S')}", 2000
                )
            )
            self._alive_timer.start(2000)
        except Exception:
            pass
        try:
            self._dash_console_timer = QtCore.QTimer(self)
            self._dash_console_timer.timeout.connect(self._poll_dashboard_console)
            self._dash_console_timer.start(1000)
            self._poll_dashboard_console()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self._cleanup_runtime_resources()
        except Exception:
            pass
        return super().closeEvent(event)


def main():
    sys.exit(run_main_window(MainWindow))


if __name__ == "__main__":
    main()
