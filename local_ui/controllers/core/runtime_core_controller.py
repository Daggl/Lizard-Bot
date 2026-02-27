import os
import threading
from datetime import datetime

from PySide6 import QtCore

from services.control_api_client import send_cmd


class RuntimeCoreControllerMixin:
    def _log_async_event(self, message: str):
        try:
            repo_root = getattr(self, "_repo_root", os.getcwd())
            log_dir = os.path.join(repo_root, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            path = os.path.join(log_dir, "ui_runtime.log")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now().isoformat()} {message}\n")
        except Exception:
            pass
    def _debug_log(self, message: str):
        try:
            if os.environ.get("UI_DEBUG") != "1":
                return
            log_dir = os.path.join(self._repo_root, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "ui_debug.log"), "a", encoding="utf-8", errors="ignore") as fh:
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
        def _worker():
            try:
                res = send_cmd(cmd, timeout=timeout)
            except Exception as e:
                res = {"ok": False, "error": str(e)}
            try:
                action = cmd.get("action")
            except Exception:
                action = None
            self._log_async_event(
                f"worker done action={action} ok={res.get('ok')}"
            )
            # Signal emit IS thread-safe and queues the slot in the main thread
            try:
                self._async_done.emit((cb, res))
                self._log_async_event("signal emitted")
            except Exception as exc:
                self._log_async_event(f"signal emit FAILED: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _process_async_result(self, payload):
        try:
            cb, res = payload
            self._log_async_event(
                f"_process_async_result ok={res.get('ok')} cb={bool(cb)}"
            )
            if cb:
                cb(res)
                self._log_async_event("callback finished")
        except Exception as exc:
            self._log_async_event(f"_process_async_result error: {exc}")
