"""Internationalisation (i18n) system for per-guild language support.

Provides translation lookup, per-guild language configuration and
locale file management.  Translation files live under ``data/locales/``
as ``<code>.json`` (e.g. ``en.json``, ``de.json``).
"""

import json
import os
import threading
from typing import Any

from .paths import REPO_ROOT

_LOCALES_DIR = os.path.join(REPO_ROOT, "data", "locales")
_LANGUAGE_CONFIG_PATH = os.path.join(REPO_ROOT, "data", "language.json")
_DEFAULT_LANGUAGE = "en"
_LANGUAGE_LOCK = threading.RLock()


def _load_language_config() -> dict:
    """Load the global language config from ``data/language.json``."""
    try:
        if os.path.isfile(_LANGUAGE_CONFIG_PATH):
            with open(_LANGUAGE_CONFIG_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_language_config(data: dict) -> bool:
    """Persist the global language config to ``data/language.json``."""
    try:
        os.makedirs(os.path.dirname(_LANGUAGE_CONFIG_PATH), exist_ok=True)
        with open(_LANGUAGE_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _load_locale_file(path: str) -> dict[str, str]:
    """Load a single locale JSON file and return a normalised string→string map."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items() if v is not None}
    except Exception:
        pass
    return {}


class TranslationManager:
    """Thread-safe registry of locale catalogues loaded from disk."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._translations: dict[str, dict[str, str]] = {}
        self.reload()

    def reload(self) -> None:
        """(Re-)load all ``*.json`` files from the locales directory."""
        translations: dict[str, dict[str, str]] = {}
        if os.path.isdir(_LOCALES_DIR):
            for entry in os.listdir(_LOCALES_DIR):
                if not entry.lower().endswith(".json"):
                    continue
                code = entry[:-5].lower()
                translations[code] = _load_locale_file(os.path.join(_LOCALES_DIR, entry))
        if _DEFAULT_LANGUAGE not in translations:
            translations[_DEFAULT_LANGUAGE] = {}
        with self._lock:
            self._translations = translations

    def available_languages(self) -> tuple[str, ...]:
        """Return sorted tuple of loaded language codes."""
        with self._lock:
            return tuple(sorted(self._translations.keys()))

    def translate(
        self,
        key: str,
        language: str | None = None,
        fallback: str | None = None,
        **fmt,
    ) -> str:
        """Look up *key* in the catalogue for *language*, with optional format placeholders."""
        if not key:
            return ""
        code = (language or _DEFAULT_LANGUAGE or "en").lower()
        with self._lock:
            catalog = self._translations.get(code, {})
            default_catalog = self._translations.get(_DEFAULT_LANGUAGE, {})
            text = catalog.get(key) or default_catalog.get(key) or fallback or key
        if fmt:
            try:
                text = text.format(**fmt)
            except Exception:
                pass
        return text


_translation_manager = TranslationManager()
_language_cache = {
    "default": _DEFAULT_LANGUAGE,
    "guilds": {},
}

LANGUAGE_LABELS = {
    "en": "English",
    "de": "Deutsch",
}


def reload_translations() -> None:
    """Force re-read of all locale files from disk."""
    _translation_manager.reload()


def refresh_language_cache() -> None:
    """Sync the in-memory guild→language mapping from the config file."""
    data = _load_language_config()
    default_raw = (
        data.get("DEFAULT_LANGUAGE")
        or data.get("default_language")
        or data.get("default")
        or _DEFAULT_LANGUAGE
    )
    default_lang = str(default_raw or _DEFAULT_LANGUAGE).lower()
    guild_map = {}
    raw_guilds = data.get("GUILD_LANGUAGES") or data.get("guilds") or {}
    if isinstance(raw_guilds, dict):
        for guild_id, lang in raw_guilds.items():
            if guild_id is None:
                continue
            guid = str(guild_id)
            code = str(lang or default_lang).lower()
            guild_map[guid] = code
    with _LANGUAGE_LOCK:
        _language_cache["default"] = default_lang
        _language_cache["guilds"] = guild_map


refresh_language_cache()


def get_default_language() -> str:
    with _LANGUAGE_LOCK:
        return _language_cache.get("default", _DEFAULT_LANGUAGE)


def available_languages() -> tuple[str, ...]:
    """Return all loaded language codes."""
    return _translation_manager.available_languages()


def get_language_for_guild(guild_id: int | None) -> str:
    """Return the configured language code for a guild (falls back to default)."""
    if guild_id is None:
        return get_default_language()
    gid = str(guild_id)
    with _LANGUAGE_LOCK:
        return _language_cache.get("guilds", {}).get(gid, _language_cache.get("default", _DEFAULT_LANGUAGE))


def set_language_for_guild(guild_id: int, language: str) -> None:
    """Persist a language choice for *guild_id* and refresh the cache."""
    if guild_id is None:
        raise ValueError("guild_id is required")
    language_code = str(language or "").lower()
    if language_code not in available_languages():
        raise ValueError(f"Unsupported language code: {language_code}")

    data = _load_language_config()
    guilds = data.get("GUILD_LANGUAGES") or data.get("guilds") or {}
    if not isinstance(guilds, dict):
        guilds = {}
    guilds[str(guild_id)] = language_code
    data["GUILD_LANGUAGES"] = guilds
    if "DEFAULT_LANGUAGE" not in data:
        data["DEFAULT_LANGUAGE"] = get_default_language()
    _save_language_config(data)
    refresh_language_cache()


def set_default_language(language: str) -> None:
    """Change the global default language and persist to config."""
    language_code = str(language or "").lower()
    if language_code not in available_languages():
        raise ValueError(f"Unsupported language code: {language_code}")
    data = _load_language_config()
    data["DEFAULT_LANGUAGE"] = language_code
    _save_language_config(data)
    refresh_language_cache()


def translate(
    key: str,
    guild_id: int | None = None,
    language: str | None = None,
    default: str | None = None,
    **fmt,
) -> str:
    """Top-level translation helper — resolves guild language automatically."""
    lang = (language or get_language_for_guild(guild_id)).lower()
    return _translation_manager.translate(key, language=lang, fallback=default, **fmt)


def translate_for_ctx(ctx, key: str, default: str | None = None, **fmt) -> str:
    """Translate using guild info from a ``commands.Context``."""
    guild_id = getattr(getattr(ctx, "guild", None), "id", None)
    return translate(key, guild_id=guild_id, default=default, **fmt)


def translate_for_interaction(interaction, key: str, default: str | None = None, **fmt) -> str:
    """Translate using guild info from a ``discord.Interaction``."""
    guild_id = getattr(getattr(interaction, "guild", None), "id", None)
    return translate(key, guild_id=guild_id, default=default, **fmt)


def resolve_localized_value(
    value: Any,
    guild_id: int | None = None,
    language: str | None = None,
) -> Any:
    """If *value* is a ``{lang: text}`` dict, pick the best matching translation."""
    if isinstance(value, dict):
        lang = (language or get_language_for_guild(guild_id)).lower()
        normalized = {str(k).lower(): v for k, v in value.items()}
        if lang in normalized:
            return normalized[lang]
        default_lang = get_default_language()
        if default_lang in normalized:
            return normalized[default_lang]
        return next(iter(normalized.values()), None)
    return value


def describe_language(code: str) -> str:
    """Return a human-readable label for a language code (e.g. ``'de'`` → ``'Deutsch'``)."""
    key = str(code or "").lower()
    return LANGUAGE_LABELS.get(key, key.upper())


def get_all_guild_languages() -> dict[str, str]:
    """Return a copy of the guild→language mapping."""
    with _LANGUAGE_LOCK:
        return dict(_language_cache.get("guilds", {}))
