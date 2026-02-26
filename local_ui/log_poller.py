import json
import os
import sqlite3

from PySide6 import QtCore


class LogPoller(QtCore.QThread):
    new_line = QtCore.Signal(str)

    def __init__(self, path: str, mode: str = "file", table: str = None, last_rowid: int = 0, interval: float = 5.0):
        super().__init__()
        self.path = path
        self.mode = mode
        self.table = table
        self._last_rowid = int(last_rowid or 0)
        self._interval = float(interval)
        self._stopped = False

    def stop(self):
        self._stopped = True
        try:
            self.wait(2000)
        except Exception:
            pass

    def run(self):
        try:
            if self.mode == "db":
                try:
                    conn = sqlite3.connect(self.path)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                except Exception:
                    return

                while not self._stopped:
                    try:
                        cur.execute(f"SELECT rowid, * FROM '{self.table}' WHERE rowid > ? ORDER BY rowid ASC", (self._last_rowid,))
                        rows = cur.fetchall()
                        for row in rows:
                            try:
                                try:
                                    data = dict(row)
                                    s = json.dumps(data, ensure_ascii=False)
                                except Exception:
                                    s = str(tuple(row))
                                self.new_line.emit(s)
                            except Exception:
                                pass
                            try:
                                self._last_rowid = int(row['rowid'])
                            except Exception:
                                try:
                                    self._last_rowid = int(row[0])
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    for _ in range(int(self._interval * 10)):
                        if self._stopped:
                            break
                        self.msleep(100)
                try:
                    conn.close()
                except Exception:
                    pass
            else:
                try:
                    with open(self.path, 'r', encoding='utf-8', errors='ignore') as fh:
                        fh.seek(0, os.SEEK_END)
                        while not self._stopped:
                            line = fh.readline()
                            if line:
                                self.new_line.emit(line.rstrip('\n'))
                            else:
                                self.msleep(int(self._interval * 1000))
                except Exception:
                    pass
        except Exception:
            pass
