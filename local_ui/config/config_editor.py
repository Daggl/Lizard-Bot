import json
import os

from core.repo_paths import get_repo_root
from PySide6 import QtCore, QtWidgets

from .config_io import config_json_path, ensure_env_file, load_env_dict, save_env_dict

_HIDDEN_ENV_KEYS = {"LOCAL_UI_ENABLE"}


class ConfigEditor(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Cog Configs")
        self.resize(700, 420)

        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.list = QtWidgets.QListWidget()
        self.load_button = QtWidgets.QPushButton("Refresh List")
        top.addWidget(self.list, 1)
        top.addWidget(self.load_button)
        layout.addLayout(top)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        row = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save")
        self.add_btn = QtWidgets.QPushButton("Add Key")
        self.remove_btn = QtWidgets.QPushButton("Remove Selected")
        row.addWidget(self.add_btn)
        row.addWidget(self.remove_btn)
        row.addStretch()
        row.addWidget(self.save_btn)
        layout.addLayout(row)

        self.load_button.clicked.connect(self.refresh_list)
        self.list.currentItemChanged.connect(self.on_select)
        self.save_btn.clicked.connect(self.on_save)
        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)

        self.repo_root = get_repo_root()
        os.makedirs(os.path.join(self.repo_root, "config"), exist_ok=True)
        ensure_env_file(self.repo_root)

        self.refresh_list()

    # ------------------------------------------------------------------
    # Guild awareness
    # ------------------------------------------------------------------

    def _active_guild_id(self) -> str | None:
        """Return the currently selected guild ID from the parent window."""
        try:
            parent = self.parent()
            if parent is not None:
                gid = getattr(parent, "_active_guild_id", None)
                return str(gid) if gid else None
        except Exception:
            pass
        return None

    def _config_dir(self) -> str:
        """Return the config directory for the active guild (or global)."""
        gid = self._active_guild_id()
        if gid:
            d = os.path.join(self.repo_root, "config", "guilds", gid)
            os.makedirs(d, exist_ok=True)
            return d
        return os.path.join(self.repo_root, "config")

    def _config_path_for(self, filename: str) -> str:
        """Return the full path to a config file for the active guild.

        If a guild is active, returns the guild-specific path.  On read the
        caller should fall back to the global path when the file is missing.
        """
        gid = self._active_guild_id()
        return config_json_path(self.repo_root, filename, guild_id=gid)

    def _load_config_data(self, filename: str) -> dict:
        """Load config JSON for the active guild (no global fallback)."""
        gid = self._active_guild_id()
        if gid:
            guild_path = config_json_path(self.repo_root, filename, guild_id=gid)
            try:
                with open(guild_path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                return {}
        # No guild selected → global config
        global_path = os.path.join(self.repo_root, "config", filename)
        try:
            with open(global_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def refresh_list(self):
        # Remember previous selection so we can re-select after rebuild
        prev_item = self.list.currentItem()
        prev_name = prev_item.text() if prev_item else None

        self.list.clear()
        self.list.addItem(".env")
        gid = self._active_guild_id()
        if gid:
            # Guild selected → show only guild-specific files
            guild_dir = os.path.join(self.repo_root, "config", "guilds", gid)
            try:
                for fn in sorted(os.listdir(guild_dir)):
                    if fn.endswith(".json"):
                        self.list.addItem(fn)
            except Exception:
                pass
        else:
            # No guild → show global files
            global_dir = os.path.join(self.repo_root, "config")
            try:
                for fn in sorted(os.listdir(global_dir)):
                    if fn.endswith(".json"):
                        self.list.addItem(fn)
            except Exception:
                pass

        # Try to re-select the previously selected file; if it no longer
        # exists in this guild, clear the table so stale data disappears.
        restored = False
        if prev_name:
            for i in range(self.list.count()):
                if self.list.item(i).text() == prev_name:
                    self.list.setCurrentRow(i)  # triggers on_select → reloads data
                    restored = True
                    break
        if not restored:
            self.table.setRowCount(0)

    def on_select(self, current, prev=None):
        if current is None:
            return
        name = current.text()
        is_env = name == ".env"
        if is_env:
            try:
                path, _created = ensure_env_file(self.repo_root)
                data = load_env_dict(path)
            except Exception:
                data = {}
        else:
            data = self._load_config_data(name)

        self.table.setRowCount(0)
        if isinstance(data, dict):
            for k, v in data.items():
                if is_env and str(k) in _HIDDEN_ENV_KEYS:
                    continue
                r = self.table.rowCount()
                self.table.insertRow(r)
                key_item = QtWidgets.QTableWidgetItem(str(k))
                if not is_env:
                    key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
                if isinstance(v, (dict, list)):
                    val_text = json.dumps(v, ensure_ascii=False)
                else:
                    val_text = str(v) if v is not None else ""
                val_item = QtWidgets.QTableWidgetItem(val_text)
                self.table.setItem(r, 0, key_item)
                self.table.setItem(r, 1, val_item)

    def on_save(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        is_env = name == ".env"
        data = {}
        for r in range(self.table.rowCount()):
            key_item = self.table.item(r, 0)
            val_item = self.table.item(r, 1)
            if key_item is None:
                continue
            k = key_item.text().strip()
            if not k:
                continue
            vtxt = val_item.text() if val_item is not None else ""
            if is_env:
                data[k] = str(vtxt)
                continue
            val = None
            if vtxt.lower() in ("null", "none", ""):
                val = None
            elif vtxt.lower() in ("true", "false"):
                val = vtxt.lower() == "true"
            else:
                try:
                    val = int(vtxt)
                except Exception:
                    try:
                        val = float(vtxt)
                    except Exception:
                        try:
                            val = json.loads(vtxt)
                        except Exception:
                            val = vtxt
            data[k] = val

        try:
            if is_env:
                save_env_dict(self.repo_root, data)
            else:
                path = self._config_path_for(name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            QtWidgets.QMessageBox.information(self, "Saved", f"Saved {name}")
            try:
                parent = self.parent()
                if parent and hasattr(parent, "update_preview"):
                    parent.update_preview()
            except Exception:
                pass
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def on_add(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QtWidgets.QTableWidgetItem("NEW_KEY"))
        self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(""))

    def on_remove(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
