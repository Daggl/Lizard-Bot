import json
import os
import threading
from typing import Any, Dict, Iterable, Optional

from .config import load_cog_config, write_cog_config
from .paths import REPO_ROOT

_LOCALES_DIR = os.path.join(REPO_ROOT, "data", "locales")
_LANGUAGE_CONFIG_NAME = "language"
_DEFAULT_LANGUAGE = "en"
_LANGUAGE_LOCK = threading.RLock()


def _load_locale_file(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items() if v is not None}
    except Exception:
        pass
    return {}


class TranslationManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._translations: Dict[str, Dict[str, str]] = {}
        self.reload()

    def reload(self) -> None:
        translations: Dict[str, Dict[str, str]] = {}
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

    def available_languages(self) -> Iterable[str]:
        with self._lock:
            return tuple(sorted(self._translations.keys()))

    def translate(self, key: str, language: Optional[str] = None, fallback: Optional[str] = None, **fmt) -> str:
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
    _translation_manager.reload()


def refresh_language_cache() -> None:
    data = load_cog_config(_LANGUAGE_CONFIG_NAME) or {}
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


def available_languages() -> Iterable[str]:
    return _translation_manager.available_languages()


def get_language_for_guild(guild_id: Optional[int]) -> str:
    if guild_id is None:
        return get_default_language()
    gid = str(guild_id)
    with _LANGUAGE_LOCK:
        return _language_cache.get("guilds", {}).get(gid, _language_cache.get("default", _DEFAULT_LANGUAGE))


def set_language_for_guild(guild_id: int, language: str) -> None:
    if guild_id is None:
        raise ValueError("guild_id is required")
    language_code = str(language or "").lower()
    if language_code not in available_languages():
        raise ValueError(f"Unsupported language code: {language_code}")

    data = load_cog_config(_LANGUAGE_CONFIG_NAME) or {}
    guilds = data.get("GUILD_LANGUAGES") or data.get("guilds") or {}
    if not isinstance(guilds, dict):
        guilds = {}
    guilds[str(guild_id)] = language_code
    data["GUILD_LANGUAGES"] = guilds
    if "DEFAULT_LANGUAGE" not in data:
        data["DEFAULT_LANGUAGE"] = get_default_language()
    write_cog_config(_LANGUAGE_CONFIG_NAME, data)
    refresh_language_cache()


def set_default_language(language: str) -> None:
    language_code = str(language or "").lower()
    if language_code not in available_languages():
        raise ValueError(f"Unsupported language code: {language_code}")
    data = load_cog_config(_LANGUAGE_CONFIG_NAME) or {}
    data["DEFAULT_LANGUAGE"] = language_code
    write_cog_config(_LANGUAGE_CONFIG_NAME, data)
    refresh_language_cache()


def translate(key: str, guild_id: Optional[int] = None, language: Optional[str] = None, default: Optional[str] = None, **fmt) -> str:
    lang = (language or get_language_for_guild(guild_id)).lower()
    return _translation_manager.translate(key, language=lang, fallback=default, **fmt)


def translate_for_ctx(ctx, key: str, default: Optional[str] = None, **fmt) -> str:
    guild = getattr(ctx, "guild", None)
    guild_id = getattr(guild, "id", None)
    return translate(key, guild_id=guild_id, default=default, **fmt)


def translate_for_interaction(interaction, key: str, default: Optional[str] = None, **fmt) -> str:
    guild = getattr(interaction, "guild", None)
    guild_id = getattr(guild, "id", None)
    return translate(key, guild_id=guild_id, default=default, **fmt)


def resolve_localized_value(value: Any, guild_id: Optional[int] = None, language: Optional[str] = None) -> Any:
    if isinstance(value, dict):
        lang = (language or get_language_for_guild(guild_id)).lower()
        normalized = {str(k).lower(): v for k, v in value.items()}
        if lang in normalized:
            return normalized[lang]
        default_lang = get_default_language()
        if default_lang in normalized:
            return normalized[default_lang]
        for fallback_value in normalized.values():
            return fallback_value
        return None
    return value


def describe_language(code: str) -> str:
    key = str(code or "").lower()
    return LANGUAGE_LABELS.get(key, key.upper())


def get_all_guild_languages() -> Dict[str, str]:
    with _LANGUAGE_LOCK:
        return dict(_language_cache.get("guilds", {}))
