import os
import sys
import traceback
from datetime import datetime

from PySide6 import QtWidgets


def _handle_uncaught_exception(exc_type, exc_value, exc_tb):
    tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        print(tb, file=sys.stderr)
    except Exception:
        pass
    try:
        app = QtWidgets.QApplication.instance()
        if app:
            try:
                QtWidgets.QMessageBox.critical(None, "Unhandled Exception", tb)
            except Exception:
                pass
    except Exception:
        pass
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(repo_root, "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, "ui_crash.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"--- {datetime.now().isoformat()} ---\n")
            fh.write(tb + "\n")
    except Exception:
        pass


def install_exception_hook():
    sys.excepthook = _handle_uncaught_exception
