import os
import socket
import sys
from datetime import datetime

from PySide6 import QtCore, QtWidgets


def run_main_window(main_window_cls):
    lock_sock = None
    try:
        lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lock_sock.bind(("127.0.0.1", 8766))
        lock_sock.listen(1)
    except Exception:
        try:
            print("Another UI instance seems to be running; exiting.")
        except Exception:
            pass
        try:
            if lock_sock:
                lock_sock.close()
        except Exception:
            pass
        return 0

    app = QtWidgets.QApplication(sys.argv)

    if os.environ.get("UI_EVENT_TRACE") == "1":
        _install_event_trace(app)

    w = main_window_cls()
    w.show()
    code = app.exec()
    try:
        if lock_sock:
            lock_sock.close()
    except Exception:
        pass
    return code


def _install_event_trace(app: QtWidgets.QApplication):
    class _EventLogger(QtCore.QObject):
        def eventFilter(self, obj, event):
            try:
                t = event.type()
            except Exception:
                t = None

            try:
                interesting = (
                    QtCore.QEvent.MouseButtonPress,
                    QtCore.QEvent.MouseButtonRelease,
                    QtCore.QEvent.KeyPress,
                    QtCore.QEvent.KeyRelease,
                    QtCore.QEvent.FocusIn,
                    QtCore.QEvent.FocusOut,
                )
            except Exception:
                interesting = ()

            if t in interesting:
                try:
                    if hasattr(QtCore.QEvent, "typeToString"):
                        try:
                            name = QtCore.QEvent.typeToString(t)
                        except Exception:
                            name = str(t)
                    else:
                        name = str(t)

                    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    objname = getattr(obj, "__class__", type(obj)).__name__
                    line = f"EVENT {datetime.now().isoformat()} {name} obj={objname}\\n"
                    try:
                        buf = getattr(self, "_evbuf", None)
                        if buf is None:
                            self._evbuf = []
                            buf = self._evbuf
                        buf.append(line)
                    except Exception:
                        try:
                            trace = os.path.join(repo_root, "data", "logs", "ui_run_trace.log")
                            with open(trace, "a", encoding="utf-8") as fh:
                                fh.write(line)
                        except Exception:
                            pass
                except Exception:
                    pass

            return super().eventFilter(obj, event)

    try:
        evlogger = _EventLogger(app)
        app.installEventFilter(evlogger)
    except Exception:
        return

    def _flush_events():
        try:
            buf = getattr(evlogger, "_evbuf", None)
            if not buf:
                return
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            trace = os.path.join(repo_root, "data", "logs", "ui_run_trace.log")
            try:
                towrite = list(buf)
                evlogger._evbuf.clear()
            except Exception:
                towrite = buf
                evlogger._evbuf = []
            try:
                with open(trace, "a", encoding="utf-8") as fh:
                    fh.writelines(towrite)
            except Exception:
                pass
        except Exception:
            pass

    try:
        flush_timer = QtCore.QTimer(app)
        flush_timer.setInterval(700)
        flush_timer.timeout.connect(_flush_events)
        flush_timer.start()
    except Exception:
        pass
