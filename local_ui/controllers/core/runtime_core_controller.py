"""Core runtime controller mixin — async command dispatch and resource cleanup.

Provides ``send_cmd_async`` which bridges background TCP calls to the Qt main
thread via the ``_async_done`` signal defined on ``MainWindow``.
"""

import os
import threading

from PySide6 import QtCore

from services.control_api_client import send_cmd


class RuntimeCoreControllerMixin:
    """Mixin that adds async command dispatch and runtime resource management."""

    def _debug_log(self, message: str):
        """Write a debug message to ``data/logs/ui_debug.log`` when ``UI_DEBUG=1``."""
        try:
            if os.environ.get("UI_DEBUG") != "1":
                return
            log_dir = os.path.join(self._repo_root, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "ui_debug.log"), "a", encoding="utf-8", errors="ignore") as fh:
                from datetime import datetime
                fh.write(f"{datetime.now().isoformat()} {message}\n")
        except Exception:
            pass

    def _safe_stop_timer(self, name: str):
        try:
            timer = getattr(self, name, None)
            if timer:
                timer.stop()
        except Exception:
            pass

    def _safe_close_attr(self, name: str):
        try:
            obj = getattr(self, name, None)
            if obj:
                obj.close()
        except Exception:
            pass
        finally:
            try:
                setattr(self, name, None)
            except Exception:
                pass

    def _cleanup_runtime_resources(self):
        """Stop all timers and close open file handles / DB connections."""
        for timer_name in ("status_timer", "log_timer", "_alive_timer", "_dash_console_timer"):
            self._safe_stop_timer(timer_name)
        try:
            poller = getattr(self, "_log_poller", None)
            if poller:
                poller.stop()
        except Exception:
            pass
        finally:
            try:
                self._log_poller = None
            except Exception:
                pass
        self._safe_close_attr("_log_fp")
        self._safe_close_attr("_tracked_fp")
        self._safe_close_attr("_db_conn")

    def send_cmd_async(self, cmd: dict, timeout: float = 1.0, cb=None):
        """Send a control API command in a background thread.

        When the response arrives, the ``_async_done`` signal is emitted so
        the callback *cb* runs safely on the Qt main thread.
        """
        def _worker():
            try:
                res = send_cmd(cmd, timeout=timeout)
            except Exception as e:
                res = {"ok": False, "error": str(e)}
            # Signal emission is thread-safe in Qt and queues the slot
            # in the receiver's (main) thread.
            try:
                self._async_done.emit((cb, res))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _process_async_result(self, payload):
        """Slot connected to ``_async_done`` — invokes the callback on the main thread."""
        try:
            cb, res = payload
            if cb:
                cb(res)
        except Exception as exc:
            self._debug_log(f"_process_async_result error: {exc}")
