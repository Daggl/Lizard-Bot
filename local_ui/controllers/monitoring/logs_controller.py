import json
import os
import sqlite3

from PySide6 import QtCore, QtWidgets
from services.log_format import format_db_row
from services.log_poller import LogPoller


class LogsControllerMixin:
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

    def _get_log_filter_text(self) -> str:
        """Return the current text filter (lowercase)."""
        try:
            widget = getattr(self, "log_filter_input", None)
            if widget is not None:
                return str(widget.text() or "").strip().lower()
        except Exception:
            pass
        return ""

    def _get_log_filter_category(self) -> str:
        """Return the current category filter (lowercase)."""
        try:
            widget = getattr(self, "log_filter_category", None)
            if widget is not None:
                return str(widget.currentData() or "").strip().lower()
        except Exception:
            pass
        return ""

    def _log_line_matches_filter(self, line: str) -> bool:
        """Check if a log line matches the active filters."""
        text_filter = self._get_log_filter_text()
        cat_filter = self._get_log_filter_category()
        if not text_filter and not cat_filter:
            return True
        lower = line.lower()
        if text_filter and text_filter not in lower:
            return False
        if cat_filter and cat_filter not in lower:
            return False
        return True

    def _apply_log_filter(self):
        """Re-filter displayed logs by reloading the last 200 entries with the active filter."""
        try:
            self._set_status("Filtering logs...")
        except Exception:
            pass
        try:
            db_conn = getattr(self, "_db_conn", None)
            db_table = getattr(self, "_db_table", None)
            if db_conn is not None and db_table is not None:
                self.log_text.clear()
                guild_id = getattr(self, "_active_guild_id", None)
                cur = db_conn.cursor()
                if guild_id:
                    cur.execute(
                        f"SELECT rowid, * FROM '{db_table}' WHERE guild_id = ? ORDER BY rowid DESC LIMIT 500;",
                        (int(guild_id),),
                    )
                else:
                    cur.execute(f"SELECT rowid, * FROM '{db_table}' ORDER BY rowid DESC LIMIT 500;")
                rows = cur.fetchall()
                count = 0
                for row in reversed(rows):
                    formatted = self._format_db_row(row)
                    if self._log_line_matches_filter(formatted):
                        self.log_text.appendPlainText(formatted)
                        count += 1
                try:
                    self._set_status(f"Filter applied — {count} entries shown")
                except Exception:
                    pass
            else:
                # File-based logs: re-read and filter
                path = getattr(self, "_active_log_path", None)
                if path and os.path.isfile(path):
                    self.log_text.clear()
                    count = 0
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for raw_line in fh:
                            line = raw_line.rstrip()
                            if self._log_line_matches_filter(line):
                                self.log_text.appendPlainText(line)
                                count += 1
                    try:
                        self._set_status(f"Filter applied — {count} lines shown")
                    except Exception:
                        pass
        except Exception as e:
            self._debug_log(f"_apply_log_filter failed: {e}")

    def _clear_log_filter(self):
        """Reset all log filters and reload."""
        try:
            widget = getattr(self, "log_filter_input", None)
            if widget is not None:
                widget.clear()
            cat_widget = getattr(self, "log_filter_category", None)
            if cat_widget is not None:
                cat_widget.setCurrentIndex(0)
            self._apply_log_filter()
        except Exception:
            pass

    def _start_log_poller(self, path: str, mode: str = "file", table: str = None):
        try:
            self._stop_log_poller()
            if not path:
                return
            self._active_log_mode = mode
            guild_id = getattr(self, "_active_guild_id", None) if mode == "db" else None
            if mode == "db":
                poller = LogPoller(
                    path,
                    mode="db",
                    table=table,
                    last_rowid=self._db_last_rowid,
                    interval=2.0,
                    guild_id=guild_id,
                )
            else:
                start_at_end = True
                try:
                    start_at_end = not str(path).replace("\\", "/").endswith("data/logs/ui_restart.request")
                except Exception:
                    start_at_end = True
                poller = LogPoller(path, mode="file", interval=1.0, start_at_end=start_at_end)
            poller.new_line.connect(self._on_new_log_line)
            poller.start()
            self._log_poller = poller
        except Exception as e:
            self._debug_log(f"start_log_poller failed: {e}")

    def _on_new_log_line(self, line: str):
        try:
            display_line = line
            try:
                active = str(getattr(self, "_active_log_path", "") or "").replace("\\", "/")
                if getattr(self, "_active_log_mode", "file") == "db":
                    try:
                        payload = json.loads(str(line or ""))
                        if isinstance(payload, dict):
                            display_line = self._format_db_row(payload)
                    except Exception:
                        display_line = str(line)
                elif active.endswith("data/logs/ui_restart.request"):
                    raw = str(line or "").strip()
                    if raw:
                        display_line = f"Restart requested at {raw}"
                    else:
                        display_line = "Restart marker updated"
            except Exception:
                display_line = line
            # Apply active filter — skip lines that don't match
            if not self._log_line_matches_filter(display_line):
                return
            try:
                self.log_text.appendPlainText(display_line)
            except Exception as e:
                self._debug_log(f"append log line failed: {e}")
            try:
                if getattr(self, "_tracked_fp", None):
                    self._tracked_fp.write(display_line + "\n")
                    self._tracked_fp.flush()
            except Exception as e:
                self._debug_log(f"tracked log write failed: {e}")
            try:
                self.log_text.verticalScrollBar().setValue(
                    self.log_text.verticalScrollBar().maximum()
                )
            except Exception as e:
                self._debug_log(f"log autoscroll failed: {e}")
        except Exception as e:
            self._debug_log(f"on_new_log_line failed: {e}")

    def _open_log(self):
        try:
            try:
                self._set_status("Logs: choosing file...")
            except Exception:
                pass
            repo_root = self._repo_root

            preferred_dbs = [
                os.path.join(repo_root, "data", "db", "logs.db"),
                os.path.join(repo_root, "data", "logs", "logs.db"),
            ]
            for db_path in preferred_dbs:
                if not (os.path.exists(db_path) and os.path.isfile(db_path)):
                    continue
                try:
                    self._stop_log_poller()
                    self._safe_close_attr("_db_conn")
                    self._db_table = None
                    self._db_last_rowid = 0
                    self._safe_close_attr("_log_fp")

                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    self._db_conn = conn
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                    tables = [r[0] for r in cur.fetchall()]
                    if not tables:
                        continue

                    table = "logs" if "logs" in tables else tables[0]
                    self._db_table = table
                    self._active_log_path = db_path

                    try:
                        cur.execute(f"SELECT max(rowid) as m FROM '{table}';")
                        r = cur.fetchone()
                        self._db_last_rowid = int(r['m']) if r and r['m'] is not None else 0
                    except Exception:
                        self._db_last_rowid = 0

                    try:
                        self.log_text.clear()
                        guild_id = getattr(self, "_active_guild_id", None)
                        guild_label = f" guild={guild_id}" if guild_id else ""
                        self.log_text.appendPlainText(f"Tailing DB: {db_path} table: {table}{guild_label}")
                        if guild_id:
                            cur.execute(f"SELECT rowid, * FROM '{table}' WHERE guild_id = ? ORDER BY rowid DESC LIMIT 200;", (int(guild_id),))
                        else:
                            cur.execute(f"SELECT rowid, * FROM '{table}' ORDER BY rowid DESC LIMIT 200;")
                        rows = cur.fetchall()
                        for row in reversed(rows):
                            self.log_text.appendPlainText(self._format_db_row(row))
                    except Exception:
                        pass
                    try:
                        self._open_tracked_writer(
                            f"\n--- Tailing DB: {db_path} table: {table} (started at {QtCore.QDateTime.currentDateTime().toString()}) ---"
                        )
                    except Exception:
                        pass
                    try:
                        self._start_log_poller(db_path, mode="db", table=table)
                    except Exception:
                        pass
                    return
                except Exception:
                    pass

            candidates = []
            candidates.append(os.path.join(repo_root, "discord.log"))
            candidates.append(os.path.join(repo_root, "logs"))
            candidates.append(os.path.join(repo_root, "log"))
            candidates.append(os.path.join(repo_root, "data", "logs"))

            log_files = []
            for p in candidates:
                if os.path.isdir(p):
                    for fn in os.listdir(p):
                        if fn.lower().endswith((".log", ".txt")):
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

            if log_files:
                log_files.sort(reverse=True)
                _, log_path = log_files[0]
                try:
                    self._active_log_path = log_path
                    self._log_fp = open(log_path, "r", encoding="utf-8", errors="ignore")
                    self._log_fp.seek(0, os.SEEK_END)
                    try:
                        self.log_text.clear()
                        self.log_text.appendPlainText(f"Tailing: {log_path}")
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
            repo_root = self._repo_root
            start_dir = repo_root
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose log file", start_dir, "Log files (*.log *.txt);;All files (*)")
            if path:
                try:
                    self._stop_log_poller()
                    self._safe_close_attr("_db_conn")
                    self._db_table = None
                    self._db_last_rowid = 0
                    self._safe_close_attr("_log_fp")

                    if path.lower().endswith((".db", ".sqlite")):
                        try:
                            conn = sqlite3.connect(path)
                            conn.row_factory = sqlite3.Row
                            self._db_conn = conn
                            cur = conn.cursor()
                            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                            tables = [r[0] for r in cur.fetchall()]
                            if not tables:
                                QtWidgets.QMessageBox.warning(self, "Open DB", "Keine Tabellen in der Datenbank gefunden.")
                                return
                            table = tables[0]
                            if len(tables) > 1:
                                table, ok = QtWidgets.QInputDialog.getItem(self, "Wähle Tabelle", "Tabelle:", tables, 0, False)
                                if not ok:
                                    return
                            self._db_table = table
                            try:
                                cur.execute(f"SELECT max(rowid) as m FROM '{table}';")
                                r = cur.fetchone()
                                self._db_last_rowid = int(r['m']) if r and r['m'] is not None else 0
                            except Exception:
                                self._db_last_rowid = 0
                            try:
                                cur.execute(f"SELECT rowid, * FROM '{table}' ORDER BY rowid DESC LIMIT 200;")
                                rows = cur.fetchall()
                                self.log_text.clear()
                                self.log_text.appendPlainText(f"Tailing DB: {path} table: {table}")
                                for row in reversed(rows):
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

                    self._log_fp = open(path, "r", encoding="utf-8", errors="ignore")
                    self._active_log_path = path
                    self._active_log_mode = "file"
                    self._log_fp.seek(0, os.SEEK_END)
                    self.log_text.clear()
                    self.log_text.appendPlainText(f"Tailing: {path}")
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

    def _format_db_row(self, row: sqlite3.Row) -> str:
        return format_db_row(row)

    def tail_logs(self):
        try:
            if getattr(self, "_log_poller", None):
                return
            if getattr(self, "_db_conn", None) and getattr(self, "_db_table", None):
                try:
                    cur = self._db_conn.cursor()
                    guild_id = getattr(self, "_active_guild_id", None)
                    if guild_id:
                        cur.execute(
                            f"SELECT rowid, * FROM '{self._db_table}' WHERE rowid > ? AND guild_id = ? ORDER BY rowid ASC",
                            (self._db_last_rowid, int(guild_id)),
                        )
                    else:
                        cur.execute(
                            f"SELECT rowid, * FROM '{self._db_table}' WHERE rowid > ? ORDER BY rowid ASC",
                            (self._db_last_rowid,),
                        )
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
                    self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
                except Exception:
                    pass
                return

            if not getattr(self, "_log_fp", None):
                return
            for line in self._log_fp:
                txt = line.rstrip()
                self.log_text.appendPlainText(txt)
                try:
                    if getattr(self, "_tracked_fp", None):
                        try:
                            self._tracked_fp.write(txt + "\n")
                            self._tracked_fp.flush()
                        except Exception:
                            pass
                except Exception:
                    pass
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        except Exception:
            pass
