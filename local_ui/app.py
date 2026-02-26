"""Simple PySide6 desktop UI that talks to the bot control API.

It sends single-line JSON requests to 127.0.0.1:8765 and expects a single-line
JSON response. This is a minimal example to get started.
"""



import sys
import os
import json
import threading
import sqlite3
import subprocess
import time
from datetime import datetime
# HTML embed removed; no html module required
from PySide6 import QtWidgets, QtCore, QtGui
from config_editor import ConfigEditor
from config_io import config_json_path, load_json_dict, save_json_merged
from control_api_client import send_cmd
from exception_handler import install_exception_hook
from file_ops import open_tracked_writer, prune_backups, rotate_log_file
from guides import open_bot_tutorial, open_commands_guide
from log_format import format_db_row
from log_poller import LogPoller
from runtime import run_main_window
from startup_trace import write_startup_trace
from ui_tabs import build_configs_tab, build_dashboard_tab, build_logs_tab


UI_RESTART_EXIT_CODE = 42


write_startup_trace()


install_exception_hook()


class MainWindow(QtWidgets.QMainWindow):
    _async_done = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lizard UI")
        self.resize(1220, 780)
        self.setMinimumSize(1160, 740)
        # Repo root path for data/logs tracking
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # central tabs
        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)

        build_dashboard_tab(self, tabs)
        build_logs_tab(self, tabs)
        build_configs_tab(self, tabs, ConfigEditor)

        # Preview tab (detailed settings + render)
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
        self.pv_banner = QtWidgets.QLabel()
        self.pv_banner.setFixedSize(520, 180)
        self.pv_banner.setScaledContents(False)
        pv_left.addWidget(self.pv_banner)
        pv_left.addStretch()
        pv_top.addLayout(pv_left, 0)

        pv_form = QtWidgets.QFormLayout()
        pv_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
        pv_form.setFormAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        pv_form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        pv_form.setHorizontalSpacing(10)
        pv_form.setVerticalSpacing(8)
        pv_form.setContentsMargins(0, 0, 18, 0)

        def _pv_section(text: str) -> QtWidgets.QLabel:
            label = QtWidgets.QLabel(text)
            label.setObjectName("sectionLabel")
            return label

        pv_form.addRow(_pv_section("General"))
        self.pv_name = QtWidgets.QLineEdit()
        self.pv_banner_path = QtWidgets.QLineEdit()
        self.pv_banner_browse = QtWidgets.QPushButton("Choose...")
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.pv_banner_path)
        h.addWidget(self.pv_banner_browse)
        pv_form.addRow("Example name:", self.pv_name)
        pv_form.addRow("Banner image:", h)
        self.pv_message = QtWidgets.QPlainTextEdit()
        self.pv_message.setMinimumHeight(150)
        self.pv_message.setMaximumHeight(220)
        self.pv_message.setPlaceholderText("Welcome message template. Use {mention} for mention.")
        pv_form.addRow("Message:", self.pv_message)

        # placeholder helper buttons (directly below message)
        ph_widget = QtWidgets.QWidget()
        ph_grid = QtWidgets.QGridLayout(ph_widget)
        ph_grid.setContentsMargins(0, 0, 0, 0)
        ph_grid.setHorizontalSpacing(8)
        ph_grid.setVerticalSpacing(8)
        self.ph_mention = QtWidgets.QPushButton("{mention}")
        self.ph_rules = QtWidgets.QPushButton("{rules_channel}")
        self.ph_verify = QtWidgets.QPushButton("{verify_channel}")
        self.ph_about = QtWidgets.QPushButton("{aboutme_channel}")
        for _btn in (self.ph_mention, self.ph_rules, self.ph_verify, self.ph_about):
            try:
                _btn.setMinimumHeight(34)
            except Exception:
                pass
        ph_grid.addWidget(self.ph_mention, 0, 0)
        ph_grid.addWidget(self.ph_rules, 0, 1)
        ph_grid.addWidget(self.ph_verify, 0, 2)
        ph_grid.addWidget(self.ph_about, 0, 3)
        pv_form.addRow("Placeholders:", ph_widget)

        pv_form.addRow(_pv_section("Background"))
        self.pv_bg_mode = QtWidgets.QComboBox()
        self.pv_bg_mode.addItem("Fill (cover)", "cover")
        self.pv_bg_mode.addItem("Fit (contain)", "contain")
        self.pv_bg_mode.addItem("Stretch", "stretch")
        pv_form.addRow("Background mode:", self.pv_bg_mode)

        self.pv_bg_zoom = QtWidgets.QSpinBox()
        self.pv_bg_zoom.setRange(10, 400)
        self.pv_bg_zoom.setValue(100)
        self.pv_bg_zoom.setSuffix(" %")
        self.pv_bg_zoom.setFixedWidth(120)
        pv_form.addRow("Background zoom:", self.pv_bg_zoom)

        bg_pos_row = QtWidgets.QHBoxLayout()
        self.pv_bg_x = QtWidgets.QSpinBox()
        self.pv_bg_x.setRange(-4000, 4000)
        self.pv_bg_x.setSingleStep(10)
        self.pv_bg_x.setFixedWidth(110)
        self.pv_bg_y = QtWidgets.QSpinBox()
        self.pv_bg_y.setRange(-4000, 4000)
        self.pv_bg_y.setSingleStep(10)
        self.pv_bg_y.setFixedWidth(110)
        bg_pos_row.addWidget(QtWidgets.QLabel("X"))
        bg_pos_row.addWidget(self.pv_bg_x)
        bg_pos_row.addSpacing(10)
        bg_pos_row.addWidget(QtWidgets.QLabel("Y"))
        bg_pos_row.addWidget(self.pv_bg_y)
        bg_pos_row.addStretch()
        pv_form.addRow("Background offset:", bg_pos_row)

        pv_form.addRow(_pv_section("Typography"))
        self.pv_title = QtWidgets.QLineEdit()
        self.pv_title.setPlaceholderText("WELCOME")
        pv_form.addRow("Banner title:", self.pv_title)

        self.pv_title_font = QtWidgets.QComboBox()
        self.pv_title_font.setEditable(True)
        self.pv_title_font.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        pv_form.addRow("Title font:", self.pv_title_font)

        self.pv_user_font = QtWidgets.QComboBox()
        self.pv_user_font.setEditable(True)
        self.pv_user_font.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        pv_form.addRow("Username font:", self.pv_user_font)

        self.pv_title_size = QtWidgets.QSpinBox()
        self.pv_title_size.setRange(8, 400)
        self.pv_title_size.setValue(140)
        self.pv_title_size.setFixedWidth(120)
        pv_form.addRow("Title size:", self.pv_title_size)

        self.pv_user_size = QtWidgets.QSpinBox()
        self.pv_user_size.setRange(8, 300)
        self.pv_user_size.setValue(64)
        self.pv_user_size.setFixedWidth(120)
        pv_form.addRow("Username size:", self.pv_user_size)

        self.pv_title_color = QtWidgets.QLineEdit()
        self.pv_title_color.setPlaceholderText("#FFFFFF")
        self.pv_title_color_pick = QtWidgets.QPushButton("Pick...")
        self.pv_title_color_pick.setFixedWidth(72)
        title_color_row = QtWidgets.QHBoxLayout()
        title_color_row.addWidget(self.pv_title_color, 1)
        title_color_row.addWidget(self.pv_title_color_pick, 0)
        pv_form.addRow("Title color:", title_color_row)

        self.pv_user_color = QtWidgets.QLineEdit()
        self.pv_user_color.setPlaceholderText("#E6E6E6")
        self.pv_user_color_pick = QtWidgets.QPushButton("Pick...")
        self.pv_user_color_pick.setFixedWidth(72)
        user_color_row = QtWidgets.QHBoxLayout()
        user_color_row.addWidget(self.pv_user_color, 1)
        user_color_row.addWidget(self.pv_user_color_pick, 0)
        pv_form.addRow("Username color:", user_color_row)

        pv_form.addRow(_pv_section("Position"))
        title_pos_row = QtWidgets.QHBoxLayout()
        self.pv_title_x = QtWidgets.QSpinBox()
        self.pv_title_x.setRange(-2000, 2000)
        self.pv_title_x.setSingleStep(5)
        self.pv_title_x.setFixedWidth(110)
        self.pv_title_y = QtWidgets.QSpinBox()
        self.pv_title_y.setRange(-2000, 2000)
        self.pv_title_y.setSingleStep(5)
        self.pv_title_y.setFixedWidth(110)
        title_pos_row.addWidget(QtWidgets.QLabel("X"))
        title_pos_row.addWidget(self.pv_title_x)
        title_pos_row.addSpacing(10)
        title_pos_row.addWidget(QtWidgets.QLabel("Y"))
        title_pos_row.addWidget(self.pv_title_y)
        title_pos_row.addStretch()
        pv_form.addRow("Title offset:", title_pos_row)

        user_pos_row = QtWidgets.QHBoxLayout()
        self.pv_user_x = QtWidgets.QSpinBox()
        self.pv_user_x.setRange(-2000, 2000)
        self.pv_user_x.setSingleStep(5)
        self.pv_user_x.setFixedWidth(110)
        self.pv_user_y = QtWidgets.QSpinBox()
        self.pv_user_y.setRange(-2000, 2000)
        self.pv_user_y.setSingleStep(5)
        self.pv_user_y.setFixedWidth(110)
        user_pos_row.addWidget(QtWidgets.QLabel("X"))
        user_pos_row.addWidget(self.pv_user_x)
        user_pos_row.addSpacing(10)
        user_pos_row.addWidget(QtWidgets.QLabel("Y"))
        user_pos_row.addWidget(self.pv_user_y)
        user_pos_row.addStretch()
        pv_form.addRow("Username offset:", user_pos_row)

        text_pos_row = QtWidgets.QHBoxLayout()
        self.pv_text_x = QtWidgets.QSpinBox()
        self.pv_text_x.setRange(-2000, 2000)
        self.pv_text_x.setSingleStep(5)
        self.pv_text_x.setFixedWidth(110)
        self.pv_text_y = QtWidgets.QSpinBox()
        self.pv_text_y.setRange(-2000, 2000)
        self.pv_text_y.setSingleStep(5)
        self.pv_text_y.setFixedWidth(110)
        text_pos_row.addWidget(QtWidgets.QLabel("X"))
        text_pos_row.addWidget(self.pv_text_x)
        text_pos_row.addSpacing(10)
        text_pos_row.addWidget(QtWidgets.QLabel("Y"))
        text_pos_row.addWidget(self.pv_text_y)
        text_pos_row.addStretch()
        pv_form.addRow("Text offset:", text_pos_row)

        pos_row = QtWidgets.QHBoxLayout()
        self.pv_avatar_x = QtWidgets.QSpinBox()
        self.pv_avatar_x.setRange(-2000, 2000)
        self.pv_avatar_x.setSingleStep(5)
        self.pv_avatar_x.setFixedWidth(110)
        self.pv_avatar_y = QtWidgets.QSpinBox()
        self.pv_avatar_y.setRange(-2000, 2000)
        self.pv_avatar_y.setSingleStep(5)
        self.pv_avatar_y.setFixedWidth(110)
        pos_row.addWidget(QtWidgets.QLabel("X"))
        pos_row.addWidget(self.pv_avatar_x)
        pos_row.addSpacing(10)
        pos_row.addWidget(QtWidgets.QLabel("Y"))
        pos_row.addWidget(self.pv_avatar_y)
        pos_row.addStretch()
        pv_form.addRow("Avatar offset:", pos_row)

        # wire placeholder buttons to insert text at cursor
        self.ph_mention.clicked.connect(lambda: self._insert_placeholder('{mention}'))
        self.ph_rules.clicked.connect(lambda: self._insert_placeholder('{rules_channel}'))
        self.ph_verify.clicked.connect(lambda: self._insert_placeholder('{verify_channel}'))
        self.ph_about.clicked.connect(lambda: self._insert_placeholder('{aboutme_channel}'))

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

        # Toolbar row for preview actions
        pv_row = QtWidgets.QHBoxLayout()
        self.pv_save = QtWidgets.QPushButton("Save")
        self.pv_save_reload = QtWidgets.QPushButton("Save + Reload")
        self.pv_refresh = QtWidgets.QPushButton("Refresh Preview")
        for _btn in (self.pv_refresh, self.pv_save, self.pv_save_reload):
            try:
                _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
                _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            except Exception:
                pass
        pv_row.addStretch()
        pv_row.addWidget(self.pv_refresh)
        pv_row.addWidget(self.pv_save)
        pv_row.addWidget(self.pv_save_reload)
        pv_layout.addLayout(pv_row)

        tabs.addTab(preview_w, "Welcome")

        # Rankcard preview tab
        rank_w = QtWidgets.QWidget()
        rank_layout = QtWidgets.QVBoxLayout(rank_w)
        rank_layout.setContentsMargins(8, 8, 10, 8)
        rank_layout.setSpacing(10)

        # Rankcard layout: preview on the left, controls on the right
        rk_main = QtWidgets.QHBoxLayout()
        rk_main.setSpacing(12)

        # Left: preview area with header
        rk_left = QtWidgets.QVBoxLayout()
        lbl_preview = QtWidgets.QLabel("Preview")
        lbl_preview.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl_preview.setStyleSheet("font-weight:700; font-size:14px; margin-bottom:6px;")
        rk_left.addWidget(lbl_preview)
        self.rk_image = QtWidgets.QLabel()
        self.rk_image.setFixedSize(520, 180)
        self.rk_image.setScaledContents(False)
        rk_left.addWidget(self.rk_image)
        rk_left.addStretch()

        # Right: form controls and actions
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
        rk_form.addRow(_pv_section("General"))
        self.rk_name = QtWidgets.QLineEdit()
        self.rk_bg_path = QtWidgets.QLineEdit()
        self.rk_bg_browse = QtWidgets.QPushButton("Choose...")
        hbg = QtWidgets.QHBoxLayout()
        hbg.addWidget(self.rk_bg_path)
        hbg.addWidget(self.rk_bg_browse)
        rk_form.addRow("Example name:", self.rk_name)
        rk_form.addRow("Background PNG:", hbg)
        rk_form.addRow(_pv_section("Background"))
        self.rk_bg_mode = QtWidgets.QComboBox()
        self.rk_bg_mode.addItem("Fill (cover)", "cover")
        self.rk_bg_mode.addItem("Fit (contain)", "contain")
        self.rk_bg_mode.addItem("Stretch", "stretch")
        rk_form.addRow("Background mode:", self.rk_bg_mode)

        self.rk_bg_zoom = QtWidgets.QSpinBox()
        self.rk_bg_zoom.setRange(10, 400)
        self.rk_bg_zoom.setValue(100)
        self.rk_bg_zoom.setSuffix(" %")
        self.rk_bg_zoom.setFixedWidth(120)
        rk_form.addRow("Background zoom:", self.rk_bg_zoom)

        rk_bg_offset_row = QtWidgets.QHBoxLayout()
        self.rk_bg_x = QtWidgets.QSpinBox()
        self.rk_bg_x.setRange(-4000, 4000)
        self.rk_bg_x.setSingleStep(10)
        self.rk_bg_x.setFixedWidth(110)
        self.rk_bg_y = QtWidgets.QSpinBox()
        self.rk_bg_y.setRange(-4000, 4000)
        self.rk_bg_y.setSingleStep(10)
        self.rk_bg_y.setFixedWidth(110)
        rk_bg_offset_row.addWidget(QtWidgets.QLabel("X"))
        rk_bg_offset_row.addWidget(self.rk_bg_x)
        rk_bg_offset_row.addSpacing(10)
        rk_bg_offset_row.addWidget(QtWidgets.QLabel("Y"))
        rk_bg_offset_row.addWidget(self.rk_bg_y)
        rk_bg_offset_row.addStretch()
        rk_form.addRow("Background offset:", rk_bg_offset_row)

        rk_form.addRow(_pv_section("Typography"))
        self.rk_name_font = QtWidgets.QComboBox()
        self.rk_name_font.setEditable(True)
        self.rk_name_font.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        rk_form.addRow("Name font:", self.rk_name_font)

        self.rk_info_font = QtWidgets.QComboBox()
        self.rk_info_font.setEditable(True)
        self.rk_info_font.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        rk_form.addRow("Info font:", self.rk_info_font)

        self.rk_name_size = QtWidgets.QSpinBox()
        self.rk_name_size.setRange(8, 200)
        self.rk_name_size.setValue(60)
        self.rk_name_size.setFixedWidth(120)
        rk_form.addRow("Name size:", self.rk_name_size)

        self.rk_info_size = QtWidgets.QSpinBox()
        self.rk_info_size.setRange(8, 120)
        self.rk_info_size.setValue(40)
        self.rk_info_size.setFixedWidth(120)
        rk_form.addRow("Info size:", self.rk_info_size)

        self.rk_name_color = QtWidgets.QLineEdit()
        self.rk_name_color.setPlaceholderText("#FFFFFF")
        self.rk_name_color_pick = QtWidgets.QPushButton("Pick...")
        self.rk_name_color_pick.setFixedWidth(72)
        rk_name_color_row = QtWidgets.QHBoxLayout()
        rk_name_color_row.addWidget(self.rk_name_color, 1)
        rk_name_color_row.addWidget(self.rk_name_color_pick, 0)
        rk_form.addRow("Name color:", rk_name_color_row)

        self.rk_info_color = QtWidgets.QLineEdit()
        self.rk_info_color.setPlaceholderText("#C8C8C8")
        self.rk_info_color_pick = QtWidgets.QPushButton("Pick...")
        self.rk_info_color_pick.setFixedWidth(72)
        rk_info_color_row = QtWidgets.QHBoxLayout()
        rk_info_color_row.addWidget(self.rk_info_color, 1)
        rk_info_color_row.addWidget(self.rk_info_color_pick, 0)
        rk_form.addRow("Info color:", rk_info_color_row)

        rk_text_pos_row = QtWidgets.QHBoxLayout()
        self.rk_text_x = QtWidgets.QSpinBox()
        self.rk_text_x.setRange(-2000, 2000)
        self.rk_text_x.setSingleStep(5)
        self.rk_text_x.setFixedWidth(110)
        self.rk_text_y = QtWidgets.QSpinBox()
        self.rk_text_y.setRange(-2000, 2000)
        self.rk_text_y.setSingleStep(5)
        self.rk_text_y.setFixedWidth(110)
        rk_text_pos_row.addWidget(QtWidgets.QLabel("X"))
        rk_text_pos_row.addWidget(self.rk_text_x)
        rk_text_pos_row.addSpacing(10)
        rk_text_pos_row.addWidget(QtWidgets.QLabel("Y"))
        rk_text_pos_row.addWidget(self.rk_text_y)
        rk_text_pos_row.addStretch()
        rk_form.addRow("Text offset:", rk_text_pos_row)

        rk_form.addRow(_pv_section("Messages"))
        self.lv_levelup_msg = QtWidgets.QPlainTextEdit()
        self.lv_levelup_msg.setMinimumHeight(96)
        self.lv_levelup_msg.setMaximumHeight(170)
        self.lv_levelup_msg.setPlaceholderText(
            "Use {member_mention}, {member_name}, {member_display_name}, {member_id}, {guild_name}, {level}"
        )
        self.lv_emoji_win = QtWidgets.QLineEdit()
        self.lv_emoji_win.setPlaceholderText("Leading emoji ID or <:name:id>")
        rk_form.addRow("Leading emoji ID/tag:", self.lv_emoji_win)

        self.lv_emoji_heart = QtWidgets.QLineEdit()
        self.lv_emoji_heart.setPlaceholderText("Trailing emoji ID or <:name:id>")
        rk_form.addRow("Trailing emoji ID/tag:", self.lv_emoji_heart)
        rk_form.addRow("Level-up message:", self.lv_levelup_msg)

        self.lv_ph_member_mention = QtWidgets.QPushButton("{member_mention}")
        self.lv_ph_member_name = QtWidgets.QPushButton("{member_name}")
        self.lv_ph_display_name = QtWidgets.QPushButton("{member_display_name}")
        self.lv_ph_member_id = QtWidgets.QPushButton("{member_id}")
        self.lv_ph_guild_name = QtWidgets.QPushButton("{guild_name}")
        self.lv_ph_level = QtWidgets.QPushButton("{level}")
        self.lv_ph_leading_emoji = QtWidgets.QPushButton("{leading_emoji}")
        self.lv_ph_trailing_emoji = QtWidgets.QPushButton("{trailing_emoji}")

        lv_ph_widget = QtWidgets.QWidget()
        lv_ph_grid = QtWidgets.QGridLayout(lv_ph_widget)
        lv_ph_grid.setContentsMargins(0, 0, 0, 0)
        lv_ph_grid.setHorizontalSpacing(8)
        lv_ph_grid.setVerticalSpacing(8)
        lv_ph_grid.addWidget(self.lv_ph_member_mention, 0, 0)
        lv_ph_grid.addWidget(self.lv_ph_member_name, 0, 1)
        lv_ph_grid.addWidget(self.lv_ph_display_name, 0, 2)
        lv_ph_grid.addWidget(self.lv_ph_member_id, 1, 0)
        lv_ph_grid.addWidget(self.lv_ph_guild_name, 1, 1)
        lv_ph_grid.addWidget(self.lv_ph_level, 1, 2)
        lv_ph_grid.addWidget(self.lv_ph_leading_emoji, 2, 0)
        lv_ph_grid.addWidget(self.lv_ph_trailing_emoji, 2, 1)
        rk_form.addRow("Level placeholders:", lv_ph_widget)

        self.lv_achievement_msg = QtWidgets.QPlainTextEdit()
        self.lv_achievement_msg.setMinimumHeight(86)
        self.lv_achievement_msg.setMaximumHeight(150)
        self.lv_achievement_msg.setPlaceholderText(
            "Use {member_mention}, {member_name}, {member_display_name}, {member_id}, {guild_name}, {achievement_name}"
        )
        rk_form.addRow("Achievement message:", self.lv_achievement_msg)

        self.av_ph_member_mention = QtWidgets.QPushButton("{member_mention}")
        self.av_ph_member_name = QtWidgets.QPushButton("{member_name}")
        self.av_ph_display_name = QtWidgets.QPushButton("{member_display_name}")
        self.av_ph_member_id = QtWidgets.QPushButton("{member_id}")
        self.av_ph_guild_name = QtWidgets.QPushButton("{guild_name}")
        self.av_ph_achievement_name = QtWidgets.QPushButton("{achievement_name}")
        for _btn in (
            self.lv_ph_member_mention,
            self.lv_ph_member_name,
            self.lv_ph_display_name,
            self.lv_ph_member_id,
            self.lv_ph_guild_name,
            self.lv_ph_level,
            self.lv_ph_leading_emoji,
            self.lv_ph_trailing_emoji,
            self.av_ph_member_mention,
            self.av_ph_member_name,
            self.av_ph_display_name,
            self.av_ph_member_id,
            self.av_ph_guild_name,
            self.av_ph_achievement_name,
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
        av_ph_grid.addWidget(self.av_ph_member_mention, 0, 0)
        av_ph_grid.addWidget(self.av_ph_member_name, 0, 1)
        av_ph_grid.addWidget(self.av_ph_display_name, 0, 2)
        av_ph_grid.addWidget(self.av_ph_member_id, 1, 0)
        av_ph_grid.addWidget(self.av_ph_guild_name, 1, 1)
        av_ph_grid.addWidget(self.av_ph_achievement_name, 1, 2)
        rk_form.addRow("Achievement placeholders:", av_ph_widget)
        rk_controls_layout.addLayout(rk_form)

        # Add a small info label under the form
        info = QtWidgets.QLabel("Choose a background PNG to preview the rank. Use Save + Reload to apply to the bot.")
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

        # action buttons (aligned right)
        rk_buttons = QtWidgets.QHBoxLayout()
        self.rk_refresh = QtWidgets.QPushButton("Refresh Rank")
        self.rk_save = QtWidgets.QPushButton("Save")
        self.rk_save_reload = QtWidgets.QPushButton("Save + Reload")
        for _btn in (self.rk_refresh, self.rk_save, self.rk_save_reload):
            try:
                _btn.setMinimumWidth(_btn.sizeHint().width() + 18)
                _btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            except Exception:
                pass
        rk_buttons.addStretch()
        rk_buttons.addWidget(self.rk_refresh)
        rk_buttons.addWidget(self.rk_save)
        rk_buttons.addWidget(self.rk_save_reload)
        rk_right.addLayout(rk_buttons)

        rk_main.addLayout(rk_left, 0)
        rk_main.addLayout(rk_right, 1)
        rank_layout.addLayout(rk_main)

        tabs.addTab(rank_w, "Rank")

        # wire rankcard controls
        self.rk_refresh.clicked.connect(self.on_refresh_rankpreview)
        self.rk_bg_browse.clicked.connect(self._choose_rank_bg)
        self.rk_name_color_pick.clicked.connect(lambda: self._pick_color(self.rk_name_color, "Choose rank name color"))
        self.rk_info_color_pick.clicked.connect(lambda: self._pick_color(self.rk_info_color, "Choose rank info color"))
        self.lv_ph_member_mention.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{member_mention}'))
        self.lv_ph_member_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{member_name}'))
        self.lv_ph_display_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{member_display_name}'))
        self.lv_ph_member_id.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{member_id}'))
        self.lv_ph_guild_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{guild_name}'))
        self.lv_ph_level.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{level}'))
        self.lv_ph_leading_emoji.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{leading_emoji}'))
        self.lv_ph_trailing_emoji.clicked.connect(lambda: self._insert_placeholder_into(self.lv_levelup_msg, '{trailing_emoji}'))
        self.av_ph_member_mention.clicked.connect(lambda: self._insert_placeholder_into(self.lv_achievement_msg, '{member_mention}'))
        self.av_ph_member_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_achievement_msg, '{member_name}'))
        self.av_ph_display_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_achievement_msg, '{member_display_name}'))
        self.av_ph_member_id.clicked.connect(lambda: self._insert_placeholder_into(self.lv_achievement_msg, '{member_id}'))
        self.av_ph_guild_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_achievement_msg, '{guild_name}'))
        self.av_ph_achievement_name.clicked.connect(lambda: self._insert_placeholder_into(self.lv_achievement_msg, '{achievement_name}'))
        self.rk_save.clicked.connect(lambda: self._save_rank_preview(reload_after=False))
        self.rk_save_reload.clicked.connect(lambda: self._save_rank_preview(reload_after=True))

        # wire preview controls
        self.pv_banner_browse.clicked.connect(self._choose_banner)
        self.pv_title_color_pick.clicked.connect(lambda: self._pick_color(self.pv_title_color, "Choose title color"))
        self.pv_user_color_pick.clicked.connect(lambda: self._pick_color(self.pv_user_color, "Choose username color"))
        self.pv_refresh.clicked.connect(self.on_refresh_preview)
        self.pv_save.clicked.connect(lambda: self._save_preview(reload_after=False))
        self.pv_save_reload.clicked.connect(lambda: self._save_preview(reload_after=True))

        # live preview: debounce updates while typing
        self._preview_debounce = QtCore.QTimer(self)
        self._preview_debounce.setSingleShot(True)
        self._preview_debounce.setInterval(250)
        self._preview_debounce.timeout.connect(self._apply_live_preview)

        # QLineEdit.textChanged provides the new text, QPlainTextEdit.textChanged provides no args
        # Use an argless wrapper so signal/slot signatures match and avoid TypeError
        self.pv_name.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_banner_path.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_message.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_bg_mode.currentIndexChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_bg_zoom.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_bg_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_bg_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_title.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_title_font.currentTextChanged.connect(lambda _t: self._preview_debounce.start())
        self.pv_user_font.currentTextChanged.connect(lambda _t: self._preview_debounce.start())
        self.pv_title_size.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_user_size.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_title_color.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_user_color.textChanged.connect(lambda: self._preview_debounce.start())
        self.pv_title_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_title_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_user_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_user_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_text_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_text_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_avatar_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_avatar_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.pv_name.textChanged.connect(self._mark_preview_dirty)
        self.pv_banner_path.textChanged.connect(self._mark_preview_dirty)
        self.pv_message.textChanged.connect(self._mark_preview_dirty)
        self.pv_bg_mode.currentIndexChanged.connect(self._mark_preview_dirty)
        self.pv_bg_zoom.valueChanged.connect(self._mark_preview_dirty)
        self.pv_bg_x.valueChanged.connect(self._mark_preview_dirty)
        self.pv_bg_y.valueChanged.connect(self._mark_preview_dirty)
        self.pv_title.textChanged.connect(self._mark_preview_dirty)
        self.pv_title_font.currentTextChanged.connect(self._mark_preview_dirty)
        self.pv_user_font.currentTextChanged.connect(self._mark_preview_dirty)
        self.pv_title_size.valueChanged.connect(self._mark_preview_dirty)
        self.pv_user_size.valueChanged.connect(self._mark_preview_dirty)
        self.pv_title_color.textChanged.connect(self._mark_preview_dirty)
        self.pv_user_color.textChanged.connect(self._mark_preview_dirty)
        self.pv_title_x.valueChanged.connect(self._mark_preview_dirty)
        self.pv_title_y.valueChanged.connect(self._mark_preview_dirty)
        self.pv_user_x.valueChanged.connect(self._mark_preview_dirty)
        self.pv_user_y.valueChanged.connect(self._mark_preview_dirty)
        self.pv_text_x.valueChanged.connect(self._mark_preview_dirty)
        self.pv_text_y.valueChanged.connect(self._mark_preview_dirty)
        self.pv_avatar_x.valueChanged.connect(self._mark_preview_dirty)
        self.pv_avatar_y.valueChanged.connect(self._mark_preview_dirty)
        self.rk_name.textChanged.connect(lambda: self._preview_debounce.start())
        self.rk_bg_path.textChanged.connect(lambda: self._preview_debounce.start())
        self.rk_bg_mode.currentIndexChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_bg_zoom.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_bg_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_bg_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_name_font.currentTextChanged.connect(lambda _t: self._preview_debounce.start())
        self.rk_info_font.currentTextChanged.connect(lambda _t: self._preview_debounce.start())
        self.rk_name_size.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_info_size.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_name_color.textChanged.connect(lambda: self._preview_debounce.start())
        self.rk_info_color.textChanged.connect(lambda: self._preview_debounce.start())
        self.rk_text_x.valueChanged.connect(lambda _v: self._preview_debounce.start())
        self.rk_text_y.valueChanged.connect(lambda _v: self._preview_debounce.start())
        # ensure rank preview doesn't get clobbered when other previews update

        self.setCentralWidget(tabs)

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
        # helper to update status label and force UI repaint
        def _set_status(msg: str):
            try:
                # update dashboard label
                try:
                    self.status_label.setText(msg)
                except Exception:
                    pass
                # also show in the main window status bar for stronger feedback
                try:
                    self.statusBar().showMessage(msg, 5000)
                except Exception:
                    pass
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
        # attach helper to instance for use in handlers
        self._set_status = _set_status
        try:
            self._async_done.connect(self._process_async_result)
        except Exception:
            pass
        # write a startup marker so the user can confirm the UI launched
        try:
            try:
                start_dir = os.path.join(self._repo_root, "data", "logs")
                os.makedirs(start_dir, exist_ok=True)
                with open(os.path.join(start_dir, "ui_start.log"), "a", encoding="utf-8") as fh:
                    fh.write(f"UI started at {datetime.now().isoformat()}\n")
            except Exception:
                pass
        except Exception:
            pass

        # heartbeat timer to show the UI is alive every 2s
        # NOTE: use the status bar only for the periodic "Alive" message so
        # it doesn't overwrite the dashboard `status_label` which is updated
        # by refresh/status actions.
        try:
            self._alive_timer = QtCore.QTimer(self)
            self._alive_timer.timeout.connect(lambda: self.statusBar().showMessage(f"Alive {datetime.now().strftime('%H:%M:%S')}", 2000))
            self._alive_timer.start(2000)
        except Exception:
            pass

        # dashboard live console poller (reads start_all supervisor output)
        try:
            self._dash_console_timer = QtCore.QTimer(self)
            self._dash_console_timer.timeout.connect(self._poll_dashboard_console)
            self._dash_console_timer.start(1000)
            self._poll_dashboard_console()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            try:
                self.status_timer.stop()
            except Exception:
                pass
            try:
                self.log_timer.stop()
            except Exception:
                pass
            try:
                if getattr(self, "_alive_timer", None):
                    self._alive_timer.stop()
            except Exception:
                pass
            try:
                if getattr(self, "_dash_console_timer", None):
                    self._dash_console_timer.stop()
            except Exception:
                pass
            try:
                if getattr(self, "_log_poller", None):
                    self._log_poller.stop()
            except Exception:
                pass
            try:
                if getattr(self, "_log_fp", None):
                    self._log_fp.close()
            except Exception:
                pass
            try:
                if getattr(self, "_tracked_fp", None):
                    self._tracked_fp.close()
            except Exception:
                pass
            try:
                if getattr(self, "_db_conn", None):
                    self._db_conn.close()
            except Exception:
                pass
        except Exception:
            pass
        return super().closeEvent(event)

    def send_cmd_async(self, cmd: dict, timeout: float = 1.0, cb=None):
        def _worker():
            try:
                res = send_cmd(cmd, timeout=timeout)
            except Exception as e:
                res = {"ok": False, "error": str(e)}
            try:
                self._async_done.emit((cb, res))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _process_async_result(self, payload):
        try:
            cb, res = payload
            if cb:
                cb(res)
        except Exception:
            pass

    def _format_uptime(self, seconds: int) -> str:
        try:
            s = int(max(0, seconds or 0))
            days, rem = divmod(s, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, secs = divmod(rem, 60)
            if days > 0:
                return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except Exception:
            return "—"

    def _set_monitor_offline(self):
        try:
            self.mon_ready.setText("No")
            self.mon_user.setText("—")
            self.mon_ping.setText("—")
            self.mon_uptime.setText("—")
            self.mon_cpu.setText("—")
            self.mon_mem.setText("—")
            self.mon_cogs.setText("—")
        except Exception:
            pass

    def on_ping(self):
        self.send_cmd_async({"action": "ping"}, timeout=0.8, cb=self._on_ping_result)

    def _on_ping_result(self, r: dict):
        QtWidgets.QMessageBox.information(self, "Ping", str(r))

    def on_refresh(self):
        if self._status_inflight:
            return
        self._status_inflight = True
        self.send_cmd_async({"action": "status"}, timeout=1.0, cb=self._on_refresh_result)

    def _on_refresh_result(self, r: dict):
        try:
            if r and r.get("ok"):
                user = r.get("user") or "(no user)"
                ready = bool(r.get("ready"))
                cogs = r.get("cogs", [])
                ping_ms = r.get("gateway_ping_ms")
                uptime_seconds = r.get("uptime_seconds")
                cpu_percent = r.get("cpu_percent")
                system_cpu_percent = r.get("system_cpu_percent")
                mem_mb = r.get("memory_rss_mb")

                self.status_label.setText(f"User: {user} — Ready: {ready} — Cogs: {len(cogs)}")
                try:
                    self.mon_ready.setText("Yes" if ready else "No")
                    self.mon_user.setText(str(user))
                    self.mon_ping.setText(f"{int(ping_ms)} ms" if isinstance(ping_ms, (int, float)) else "—")
                    self.mon_uptime.setText(self._format_uptime(int(uptime_seconds or 0)))
                    if isinstance(cpu_percent, (int, float)) or isinstance(system_cpu_percent, (int, float)):
                        bot_cpu = float(cpu_percent) if isinstance(cpu_percent, (int, float)) else None
                        sys_cpu = float(system_cpu_percent) if isinstance(system_cpu_percent, (int, float)) else None
                        if bot_cpu is not None and bot_cpu > 0:
                            if bot_cpu < 0.01:
                                self.mon_cpu.setText("<0.01%")
                            else:
                                self.mon_cpu.setText(f"{bot_cpu:.2f}%")
                        elif sys_cpu is not None:
                            if sys_cpu > 0 and sys_cpu < 0.01:
                                self.mon_cpu.setText("<0.01% (sys)")
                            else:
                                self.mon_cpu.setText(f"{sys_cpu:.2f}% (sys)")
                        else:
                            self.mon_cpu.setText("—")
                    else:
                        self.mon_cpu.setText("—")
                    self.mon_mem.setText(f"{float(mem_mb):.1f} MB" if isinstance(mem_mb, (int, float)) else "—")
                    self.mon_cogs.setText(str(len(cogs)))
                except Exception:
                    pass
                try:
                    self.update_preview()
                except Exception:
                    pass
            else:
                self.status_label.setText(f"Status: offline ({(r or {}).get('error')})")
                self._set_monitor_offline()
        finally:
            self._status_inflight = False

    def on_refresh_preview(self):
        """Request a banner preview from the bot and update the preview widgets."""
        try:
            try:
                self._set_status("Preview: requesting...")
            except Exception:
                pass
            name = self.pv_name.text() or "NewMember"
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
                cb=lambda ping, name=name, overrides=overrides: self._on_preview_ping_result(ping, name, overrides),
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Preview error", str(e))

    def _on_preview_ping_result(self, ping: dict, name: str, overrides: dict):
        try:
            if not ping.get("ok"):
                QtWidgets.QMessageBox.warning(self, "Preview", f"Control API not available, using local banner ({ping.get('error')})")
                try:
                    self.update_preview()
                except Exception:
                    pass
                return
            self.send_cmd_async(
                {"action": "banner_preview", "name": name, "overrides": overrides},
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
        """Request a rank image from the bot and display it in the Rank tab."""
        try:
            try:
                self._set_status("Rank Preview: requesting...")
            except Exception:
                pass
            name = self.rk_name.text() or (self.pv_name.text() or "NewMember")
            # prefer explicit field; if empty, use persisted config
            bg = self.rk_bg_path.text() or self._rank_config.get("BG_PATH") if getattr(self, "_rank_config", None) is not None else None
            req = {"action": "rank_preview", "name": name}
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

    def on_shutdown(self):
        ok = QtWidgets.QMessageBox.question(
            self,
            "Shutdown",
            "Bot herunterfahren und UI schließen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if ok != QtWidgets.QMessageBox.Yes:
            return
        self.send_cmd_async({"action": "shutdown"}, timeout=2.5, cb=self._on_shutdown_result)

    def _on_shutdown_result(self, r: dict):
        try:
            if r.get("ok"):
                QtWidgets.QMessageBox.information(self, "Shutdown", "Bot wird heruntergefahren. UI wird geschlossen.")
                try:
                    self._set_status("Shutdown: bot + UI")
                    self.statusBar().showMessage("Shutdown ausgelöst...", 2000)
                except Exception:
                    pass
            else:
                QtWidgets.QMessageBox.warning(self, "Shutdown", f"Bot-Shutdown fehlgeschlagen: {r}\nUI wird trotzdem beendet.")
                try:
                    self._set_status("Shutdown: UI only")
                    self.statusBar().showMessage("Bot konnte nicht bestätigt werden, UI beendet...", 2500)
                except Exception:
                    pass
        finally:
            # Ensure the Python process exits so terminal command ends.
            try:
                QtWidgets.QApplication.quit()
            except Exception:
                pass
            try:
                QtCore.QTimer.singleShot(350, lambda: os._exit(0))
            except Exception:
                try:
                    os._exit(0)
                except Exception:
                    pass

    def on_restart_and_restart_ui(self):
        """Shutdown the bot (via control API), restart the bot module, then relaunch the UI.

        This method will: 1) ask for confirmation, 2) request bot shutdown, 3) spawn a new bot process
        via `python -m src.mybot`, 4) spawn a new UI process running this script, and
        5) quit the current UI.
        """
        try:
            self._set_status("Restart: preparing...")
        except Exception:
            pass
        ok = QtWidgets.QMessageBox.question(self, "Restart", "Restart the bot and the UI? This will stop the bot and relaunch both.", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if ok != QtWidgets.QMessageBox.Yes:
            return

        # If started via start_all.py supervisor, delegate full restart to it so
        # bot + UI are relaunched cleanly in the same terminal session.
        if os.environ.get("LOCAL_UI_SUPERVISED") == "1":
            try:
                self._set_status("Restart: requesting supervised restart...")
                self.statusBar().showMessage("Restart wird an Supervisor übergeben...", 2500)
            except Exception:
                pass
            try:
                marker_dir = os.path.join(self._repo_root, "data", "logs")
                os.makedirs(marker_dir, exist_ok=True)
                marker_path = os.path.join(marker_dir, "ui_restart.request")
                with open(marker_path, "w", encoding="utf-8") as fh:
                    fh.write(datetime.now().isoformat())
            except Exception:
                pass
            try:
                send_cmd({"action": "shutdown"}, timeout=2.5)
            except Exception:
                pass
            try:
                QtWidgets.QApplication.exit(UI_RESTART_EXIT_CODE)
            except Exception:
                try:
                    os._exit(UI_RESTART_EXIT_CODE)
                except Exception:
                    pass
            return

        # 1) request bot shutdown via control API (best-effort) and wait briefly
        try:
            send_cmd({"action": "shutdown"}, timeout=2.5)
        except Exception:
            pass

        # wait until old API is down (or timeout), to reduce restart races
        try:
            deadline = time.time() + 4.0
            while time.time() < deadline:
                p = send_cmd({"action": "ping"}, timeout=0.6)
                if not p.get("ok"):
                    break
                time.sleep(0.25)
        except Exception:
            pass

        bot_started = False
        ui_started = False

        # 2) start the bot module (current project entrypoint)
        try:
            env = os.environ.copy()
            env["LOCAL_UI_ENABLE"] = "1"
            env["PYTHONUNBUFFERED"] = "1"
            subprocess.Popen([sys.executable, "-u", "-m", "src.mybot"], cwd=self._repo_root, env=env)
            bot_started = True
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to start bot process: {e}")

        # 3) spawn a delayed UI relaunch helper so lock/port 8766 is released first
        try:
            app_path = os.path.abspath(__file__)
            repo_root = self._repo_root
            launcher_code = (
                "import os,sys,time,subprocess;"
                "time.sleep(1.1);"
                "env=os.environ.copy();"
                "env['PYTHONUNBUFFERED']='1';"
                f"subprocess.Popen([sys.executable,'-u',r'{app_path}'], cwd=r'{repo_root}', env=env)"
            )
            subprocess.Popen([sys.executable, "-c", launcher_code], cwd=self._repo_root)
            ui_started = True
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Restart", f"Failed to relaunch UI: {e}")

        # 4) quit current application
        if ui_started:
            try:
                if bot_started:
                    self._set_status("Restart: bot + UI started")
                    self.statusBar().showMessage("Restart ausgelöst: Bot und UI werden neu gestartet...", 3000)
                else:
                    self._set_status("Restart: UI started, bot start failed")
                    self.statusBar().showMessage("UI neu gestartet, Bot-Start fehlgeschlagen (siehe Meldung).", 4000)
            except Exception:
                pass
            try:
                QtCore.QTimer.singleShot(350, QtWidgets.QApplication.quit)
            except Exception:
                try:
                    QtWidgets.QApplication.quit()
                except Exception:
                    try:
                        sys.exit(0)
                    except Exception:
                        pass
        else:
            try:
                self._set_status("Restart: failed (UI relaunch)")
                self.statusBar().showMessage("Restart abgebrochen: Neue UI konnte nicht gestartet werden.", 5000)
            except Exception:
                pass

    def on_reload(self):
        self.send_cmd_async({"action": "reload"}, timeout=3.0, cb=self._on_reload_result)

    def on_open_bot_tutorial(self):
        try:
            open_bot_tutorial(self)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Tutorial", f"Failed to open tutorial: {e}")

    def on_open_commands_guide(self):
        try:
            open_commands_guide(self)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Commands", f"Failed to open commands guide: {e}")

    def _on_reload_result(self, r: dict):
        if r.get("ok"):
            reloaded = r.get("reloaded", [])
            failed = r.get("failed", {})
            msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
            details = ''
            if failed:
                details = '\n'.join(f"{k}: {v}" for k, v in failed.items())
                msg = msg + "\n" + details
            QtWidgets.QMessageBox.information(self, "Reload Cogs", msg)
        else:
            QtWidgets.QMessageBox.warning(self, "Reload Cogs", f"Failed: {r}")

    def _on_reload_after_save_rank(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_rank_config()
                except Exception:
                    pass
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception:
            pass

    def _on_reload_after_save_preview(self, r: dict):
        try:
            if r.get("ok"):
                try:
                    self._load_welcome_message_from_file()
                except Exception:
                    pass
                reloaded = r.get("reloaded", [])
                failed = r.get("failed", {})
                msg = f"Reloaded: {len(reloaded)} modules. Failed: {len(failed)}"
                if failed:
                    msg = msg + "\n" + "\n".join(f"{k}: {v}" for k, v in failed.items())
                QtWidgets.QMessageBox.information(self, "Reload", msg)
            else:
                QtWidgets.QMessageBox.warning(self, "Reload failed", f"{r}")
        except Exception:
            pass

    def on_edit_configs(self):
        # switch to Configs tab (if available) or open modal
        try:
            tabs = self.parent().findChild(QtWidgets.QTabWidget)
        except Exception:
            tabs = None
        if tabs:
            for i in range(tabs.count()):
                if tabs.tabText(i) == "Configs":
                    tabs.setCurrentIndex(i)
                    return
        dlg = ConfigEditor(self)
        dlg.exec()

    def _stop_log_poller(self):
        try:
            if getattr(self, "_log_poller", None):
                try:
                    self._log_poller.stop()
                except Exception:
                    pass
                self._log_poller = None
        except Exception:
            pass

    def _start_log_poller(self, path: str, mode: str = "file", table: str = None):
        try:
            self._stop_log_poller()
            if not path:
                return
            if mode == "db":
                poller = LogPoller(
                    path,
                    mode="db",
                    table=table,
                    last_rowid=self._db_last_rowid,
                    interval=2.0,
                )
            else:
                poller = LogPoller(path, mode="file", interval=1.0)
            poller.new_line.connect(self._on_new_log_line)
            poller.start()
            self._log_poller = poller
        except Exception:
            pass

    def _on_new_log_line(self, line: str):
        try:
            try:
                self.log_text.appendPlainText(line)
            except Exception:
                pass
            try:
                if getattr(self, "_tracked_fp", None):
                    self._tracked_fp.write(line + "\n")
                    self._tracked_fp.flush()
            except Exception:
                pass
            try:
                self.log_text.verticalScrollBar().setValue(
                    self.log_text.verticalScrollBar().maximum()
                )
            except Exception:
                pass
        except Exception:
            pass

    # ==================================================
    # Log tailing & preview helpers
    # ==================================================

    def _open_log(self):
        # Try to open a log file. Search common locations and pick the most
        # recently modified .log file if multiple candidates exist.
        try:
            try:
                self._set_status("Logs: choosing file...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates = []
            # common locations
            candidates.append(os.path.join(repo_root, "discord.log"))
            candidates.append(os.path.join(repo_root, "logs"))
            candidates.append(os.path.join(repo_root, "log"))
            candidates.append(os.path.join(repo_root, "data", "logs"))

            log_files = []
            for p in candidates:
                if os.path.isdir(p):
                    for fn in os.listdir(p):
                        if fn.lower().endswith(('.log', '.txt')):
                            full = os.path.join(p, fn)
                            try:
                                mtime = os.path.getmtime(full)
                                log_files.append((mtime, full))
                            except Exception:
                                pass
                else:
                    if os.path.exists(p) and os.path.isfile(p):
                        try:
                            mtime = os.path.getmtime(p)
                            log_files.append((mtime, p))
                        except Exception:
                            pass

            # choose the most recent log file
            if log_files:
                log_files.sort(reverse=True)
                _, log_path = log_files[0]
                try:
                    self._log_fp = open(log_path, "r", encoding="utf-8", errors="ignore")
                    self._log_fp.seek(0, os.SEEK_END)
                    # clear any previous message and show which file is tailed
                    try:
                        self.log_text.clear()
                        self.log_text.appendPlainText(f"Tailing: {log_path}")
                        # ensure tracked logs dir exists and open tracked writer
                        try:
                            self._open_tracked_writer(
                                f"\n--- Tailing: {log_path} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                            )
                        except Exception:
                            pass
                    except Exception:
                        pass
                    try:
                        self._start_log_poller(log_path, mode="file")
                    except Exception:
                        pass
                    return
                except Exception:
                    self._log_fp = None

            # no log file found
            self._log_fp = None
            try:
                self.log_text.clear()
                self.log_text.appendPlainText("No log file found in common locations.\nStart the bot or place a log file named 'discord.log' in the repo root or a 'logs' folder.")
            except Exception:
                pass
        except Exception:
            self._log_fp = None

    def _choose_log_file(self):
        try:
            try:
                self._set_status("Logs: choosing file...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            start_dir = repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose log file", start_dir, "Log files (*.log *.txt);;All files (*)")
            if path:
                try:
                    # close any previous file or DB connection
                    try:
                        self._stop_log_poller()
                        if getattr(self, "_db_conn", None):
                            try:
                                self._db_conn.close()
                            except Exception:
                                pass
                            self._db_conn = None
                            self._db_table = None
                            self._db_last_rowid = 0
                        if getattr(self, "_log_fp", None):
                            try:
                                self._log_fp.close()
                            except Exception:
                                pass
                            self._log_fp = None
                    except Exception:
                        pass

                    # handle sqlite DB files
                    if path.lower().endswith(('.db', '.sqlite')):
                        try:
                            # open sqlite connection
                            conn = sqlite3.connect(path)
                            conn.row_factory = sqlite3.Row
                            self._db_conn = conn
                            # find user tables
                            cur = conn.cursor()
                            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                            tables = [r[0] for r in cur.fetchall()]
                            if not tables:
                                QtWidgets.QMessageBox.warning(self, "Open DB", "Keine Tabellen in der Datenbank gefunden.")
                                return
                            # if multiple tables, ask user to pick
                            table = tables[0]
                            if len(tables) > 1:
                                table, ok = QtWidgets.QInputDialog.getItem(self, "Wähle Tabelle", "Tabelle:", tables, 0, False)
                                if not ok:
                                    return
                            self._db_table = table
                            # get last rowid
                            try:
                                cur.execute(f"SELECT max(rowid) as m FROM '{table}';")
                                r = cur.fetchone()
                                self._db_last_rowid = int(r['m']) if r and r['m'] is not None else 0
                            except Exception:
                                self._db_last_rowid = 0
                            # initial load: show last 200 rows
                            try:
                                cur.execute(f"SELECT rowid, * FROM '{table}' ORDER BY rowid DESC LIMIT 200;")
                                rows = cur.fetchall()
                                self.log_text.clear()
                                self.log_text.appendPlainText(f"Tailing DB: {path} table: {table}")
                                for row in reversed(rows):
                                    # format row using smart formatter
                                    try:
                                        line = self._format_db_row(row)
                                        self.log_text.appendPlainText(line)
                                    except Exception:
                                        try:
                                            values = dict(row)
                                            self.log_text.appendPlainText(str(values))
                                        except Exception:
                                            self.log_text.appendPlainText(str(tuple(row)))
                            except Exception as e:
                                QtWidgets.QMessageBox.warning(self, "Open DB", f"Fehler beim Lesen der Tabelle: {e}")
                            # open tracked writer
                            try:
                                self._open_tracked_writer(
                                    f"\n--- Tailing DB: {path} table: {table} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                                )
                            except Exception:
                                pass
                            try:
                                self._start_log_poller(path, mode="db", table=table)
                            except Exception:
                                pass
                            return
                        except Exception as e:
                            QtWidgets.QMessageBox.warning(self, "Open DB", f"Fehler beim Öffnen der Datenbank: {e}")
                            return

                    # otherwise open as plain text file
                    self._log_fp = open(path, "r", encoding="utf-8", errors="ignore")
                    self._log_fp.seek(0, os.SEEK_END)
                    self.log_text.clear()
                    self.log_text.appendPlainText(f"Tailing: {path}")
                    # ensure tracked logs dir exists and open tracked writer
                    try:
                        self._open_tracked_writer(
                            f"\n--- Tailing: {path} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                        )
                    except Exception:
                        pass
                    try:
                        self._start_log_poller(path, mode="file")
                    except Exception:
                        pass
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Open log", f"Failed to open log file: {e}")
        except Exception:
            pass

    def _choose_banner(self):
        try:
            try:
                self._set_status("Banner: choosing image...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    def _format_db_row(self, row: sqlite3.Row) -> str:
        return format_db_row(row)

    def _choose_rank_bg(self):
        try:
            try:
                self._set_status("Rank: choosing background...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            start_dir = os.path.join(repo_root, "assets") if os.path.exists(os.path.join(repo_root, "assets")) else repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose rank background image", start_dir, "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.rk_bg_path.setText(path)
                # optional: show it scaled in the rank image preview area
                try:
                    pix = QtGui.QPixmap(path)
                    self.rk_image.setPixmap(pix.scaled(self.rk_image.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                except Exception:
                    pass
                # persist selection immediately
                try:
                    self._save_rank_config({"BG_PATH": path})
                except Exception:
                    pass
        except Exception:
            pass

    def _rank_config_paths(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return config_json_path(repo_root, "rank.json")

    def _leveling_config_paths(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return config_json_path(repo_root, "leveling.json")

    def _load_leveling_config(self):
        cfg_path = self._leveling_config_paths()
        cfg = load_json_dict(cfg_path)

        levelup_tpl = str(
            cfg.get(
                "LEVEL_UP_MESSAGE_TEMPLATE",
                "{member_mention}\nyou just reached level {level}!\nkeep it up, cutie!",
            )
        )
        achievement_tpl = str(
            cfg.get(
                "ACHIEVEMENT_MESSAGE_TEMPLATE",
                "🏆 {member_mention} got Achievement **{achievement_name}**",
            )
        )
        win_emoji = str(cfg.get("EMOJI_WIN", "") or "")
        heart_emoji = str(cfg.get("EMOJI_HEART", "") or "")
        try:
            if not self.lv_levelup_msg.hasFocus():
                self.lv_levelup_msg.setPlainText(levelup_tpl)
            if not self.lv_achievement_msg.hasFocus():
                self.lv_achievement_msg.setPlainText(achievement_tpl)
            if not self.lv_emoji_win.hasFocus():
                self.lv_emoji_win.setText(win_emoji)
            if not self.lv_emoji_heart.hasFocus():
                self.lv_emoji_heart.setText(heart_emoji)
        except Exception:
            pass

    def _save_leveling_config(self, data: dict):
        cfg_path = self._leveling_config_paths()
        save_json_merged(cfg_path, data or {})

    def _load_rank_config(self):
        cfg_path = self._rank_config_paths()
        self._rank_config_path = cfg_path
        cfg = load_json_dict(cfg_path)
        self._rank_config = cfg
        # populate UI fields if empty
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
            # populate example name if present and user not editing
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

            lvl_data = {
                "LEVEL_UP_MESSAGE_TEMPLATE": self.lv_levelup_msg.toPlainText().strip() or "{member_mention}\\nyou just reached level {level}!\\nkeep it up, cutie!",
                "ACHIEVEMENT_MESSAGE_TEMPLATE": self.lv_achievement_msg.toPlainText().strip() or "🏆 {member_mention} got Achievement **{achievement_name}**",
                "EMOJI_WIN": (self.lv_emoji_win.text() or "").strip(),
                "EMOJI_HEART": (self.lv_emoji_heart.text() or "").strip(),
            }
            self._save_leveling_config(lvl_data)

            if reload_after:
                try:
                    self.send_cmd_async(
                        {"action": "reload"},
                        timeout=3.0,
                        cb=self._on_reload_after_save_rank,
                    )
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Reload error", str(e))

            QtWidgets.QMessageBox.information(self, "Saved", "Rank settings saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save rank settings: {e}")

    def _insert_placeholder(self, text: str):
        self._insert_placeholder_into(self.pv_message, text)

    def _insert_placeholder_into(self, target: QtWidgets.QPlainTextEdit, text: str):
        try:
            cur = target.textCursor()
            cur.insertText(text)
            target.setTextCursor(cur)
            # trigger live preview
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
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

            # de-duplicate by absolute path
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
            try:
                self._set_status("Preview: saving...")
            except Exception:
                pass
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
            # Prevent accidental deletion: do not overwrite WELCOME_MESSAGE with an empty value.
            new_msg = self.pv_message.toPlainText()
            if new_msg and new_msg.strip():
                cfg["WELCOME_MESSAGE"] = new_msg
            else:
                # keep existing message if present
                cfg["WELCOME_MESSAGE"] = cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", ""))

            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            # create a backup of the existing config to avoid data loss
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

            # update preview immediately
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
        # render preview from current fields (banner + formatted message)
        try:
            name = self.pv_name.text() or "NewMember"
            banner = self.pv_banner_path.text() or ""
            message = self.pv_message.toPlainText() or "Welcome {mention}!"

            # Use a cached banner data URL produced only by the Refresh Preview button.
            # Do NOT call the control API here — banner generation should be explicit.
            banner_url = getattr(self, "_preview_banner_data_url", None) or ""
            if banner_url:
                # if we have a data URL, pv_banner was already set by the Refresh handler
                pass
            else:
                # fall back to local file if provided
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

            # substitute placeholder in plain text (no HTML embed)
            rendered = message.replace("{mention}", f"@{name}")
            try:
                self.pv_banner.setToolTip(rendered)
            except Exception:
                pass

            # No rich embed is rendered; banner tooltip is used for message preview.
            pass
        except Exception:
            pass

    def tail_logs(self):
        try:
            # Prefer background poller when active to keep UI thread light.
            if getattr(self, "_log_poller", None):
                return
            # if tailing a sqlite DB
            if getattr(self, "_db_conn", None) and getattr(self, "_db_table", None):
                try:
                    cur = self._db_conn.cursor()
                    cur.execute(f"SELECT rowid, * FROM '{self._db_table}' WHERE rowid > ? ORDER BY rowid ASC", (self._db_last_rowid,))
                    rows = cur.fetchall()
                    for row in rows:
                        try:
                            line = self._format_db_row(row)
                        except Exception:
                            try:
                                line = str(dict(row))
                            except Exception:
                                line = str(tuple(row))
                        self.log_text.appendPlainText(line)
                        try:
                            if getattr(self, "_tracked_fp", None):
                                self._tracked_fp.write(line + "\n")
                                self._tracked_fp.flush()
                        except Exception:
                            pass
                        try:
                            self._db_last_rowid = int(row['rowid'])
                        except Exception:
                            try:
                                self._db_last_rowid = int(row[0])
                            except Exception:
                                pass
                    # scroll
                    self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
                except Exception:
                    pass
                return

            # otherwise tail a plain file
            if not getattr(self, "_log_fp", None):
                return
            for line in self._log_fp:
                txt = line.rstrip()
                self.log_text.appendPlainText(txt)
                # also append to tracked log if available
                try:
                    if getattr(self, "_tracked_fp", None):
                        try:
                            self._tracked_fp.write(txt + "\n")
                            self._tracked_fp.flush()
                        except Exception:
                            pass
                except Exception:
                    pass
            # keep the view scrolled to bottom
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        except Exception:
            pass

    def _poll_dashboard_console(self):
        try:
            path = getattr(self, "_dash_console_path", None)
            if not path:
                return
            if not os.path.exists(path):
                self._dash_console_pos = 0
                return

            try:
                size = os.path.getsize(path)
            except Exception:
                size = None

            pos = int(getattr(self, "_dash_console_pos", 0) or 0)
            if size is not None and pos > size:
                pos = 0

            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                if pos > 0:
                    fh.seek(pos)
                chunk = fh.read()
                self._dash_console_pos = fh.tell()

            if not chunk:
                return

            lines = chunk.splitlines()
            if lines:
                self.dash_console.appendPlainText("\n".join(lines))
                sb = self.dash_console.verticalScrollBar()
                sb.setValue(sb.maximum())
        except Exception:
            pass

    def update_preview(self):
        # simple preview using config/welcome.json values
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

        # show banner image if available (for Preview tab)
        banner = cfg.get("BANNER_PATH") or os.path.join(repo_root, "assets", "welcome.png")
        try:
            # if a generated banner data URL exists (from Refresh), do not overwrite the shown pixmap
            if getattr(self, "_preview_banner_data_url", None):
                # keep the banner set by Refresh Preview
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

        # update fields in Preview tab and render
        try:
            # Do not clobber manual edits: while unsaved changes exist, keep UI values.
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

                    # Load canonical message when not actively edited.
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
        """Load the canonical `WELCOME_MESSAGE` from config/welcome.json and
        set it into the Preview message field (overwrites current text).
        This is intended to be called only after a successful Save + Reload.
        """
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cfg_path = os.path.join(repo_root, "config", "welcome.json")
            if not os.path.exists(cfg_path):
                return
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            msg = str(cfg.get("WELCOME_MESSAGE", cfg.get("PREVIEW_MESSAGE", "Welcome {mention}!")))
            # overwrite regardless of focus because the user explicitly requested reload
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


def main():
    sys.exit(run_main_window(MainWindow))


if __name__ == "__main__":
    main()
