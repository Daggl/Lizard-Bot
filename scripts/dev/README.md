# Dev Helper Scripts

Utilities in this folder are for local debugging and maintenance, not production runtime.

- `_ping_test.py`: quick ping check for local control API
- `_check_ui_lock.py`: verify UI single-instance lock port
- `stop_powershells.ps1`: stop leftover PowerShell processes from test runs
- `cleanup_tracked.py`: clean duplicate header lines in tracked log files
- `cleanup_runtime.ps1`: remove runtime cache/trace leftovers safely

Legacy utilities from the old archive layout are in `scripts/dev/legacy/`:

- `legacy/check_env.py`
- `legacy/check_imports.py`
- `legacy/find_long_lines.py`
- `legacy/inspect_python.ps1`

These scripts were moved from `local_ui/` to keep the UI folder focused on runtime app files.
