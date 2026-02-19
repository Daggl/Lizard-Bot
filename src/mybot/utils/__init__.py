# mybot utils package

__all__ = [
    "config",
    "paths",
]
# mybot utils package
from .config import load_cog_config, ensure_configs_from_example
from .paths import get_db_path, get_ticket_transcript_path, ensure_dirs, migrate_old_paths
