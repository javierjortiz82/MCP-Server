"""Internationalization (i18n) module for multi-language support.

Provides translation management for Spanish (ES) and English (EN) with:
- JSON-based translation files
- Fallback mechanism (ES as default)
- Template parameter interpolation
- Lazy loading and caching

Usage:
    from mcp_server.utils.i18n import t, set_language, get_language

    # Get translation with automatic language detection
    msg = t("booking.confirmation", lang="es", name="Juan")

    # Set language context for thread
    set_language("es")

Author: Lab01-MCP Team
Created: 2025-10-17
Version: 1.0.0
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional
from enum import Enum

# Setup logger
logger = logging.getLogger("i18n")


class Language(str, Enum):
    """Supported languages."""
    SPANISH = "es"
    ENGLISH = "en"


# Thread-local storage for current language context
import threading
_language_context = threading.local()


class TranslationManager:
    """Manages translations for multi-language support."""

    # Singleton instance
    _instance: Optional[TranslationManager] = None

    def __new__(cls) -> TranslationManager:
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize translation manager with lazy loading."""
        if self._initialized:
            return

        self._initialized = True
        self._translations: dict[str, dict[str, Any]] = {}
        self._locales_path = Path(__file__).parent.parent / "locales"
        self._default_lang = Language.SPANISH.value

        logger.info(f"📚 TranslationManager initialized - Locales path: {self._locales_path}")

    def _load_language(self, lang: str) -> dict[str, Any]:
        """Load all translation files for a language.

        Args:
            lang: Language code ("es" or "en")

        Returns:
            Merged dictionary of all translations for the language
        """
        if lang in self._translations:
            return self._translations[lang]

        try:
            lang_path = self._locales_path / lang
            if not lang_path.exists():
                logger.warning(f"⚠️ Language path not found: {lang_path}")
                if lang != self._default_lang:
                    return self._load_language(self._default_lang)
                return {}

            merged_translations: dict[str, Any] = {}

            # Load all JSON files in language directory
            for json_file in sorted(lang_path.glob("*.json")):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                        # Merge with dot-notation support
                        module_name = json_file.stem  # e.g., "booking"
                        merged_translations[module_name] = file_data
                        logger.debug(f"✓ Loaded {lang}/{json_file.name}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in {json_file}: {e}")
                except Exception as e:
                    logger.error(f"❌ Failed to load {json_file}: {e}")

            self._translations[lang] = merged_translations
            logger.info(f"✓ Loaded {lang} translations: {len(merged_translations)} modules")
            return merged_translations

        except Exception as e:
            logger.error(f"❌ Error loading language {lang}: {e}")
            if lang != self._default_lang:
                return self._load_language(self._default_lang)
            return {}

    def get_translation(
        self,
        key: str,
        lang: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Get a translation string with optional parameter interpolation.

        Key format: "module.key" (e.g., "booking.confirmation")

        Args:
            key: Translation key in "module.key" format
            lang: Language code (uses context or default if None)
            **kwargs: Parameters for string interpolation

        Returns:
            Translated string with interpolated parameters
        """
        if lang is None:
            lang = getattr(_language_context, "lang", None) or self._default_lang

        # Normalize language
        if lang not in [Language.SPANISH.value, Language.ENGLISH.value]:
            logger.warning(f"⚠️ Unknown language '{lang}', using default")
            lang = self._default_lang

        try:
            # Split key into module and key
            parts = key.split(".", 1)
            if len(parts) != 2:
                logger.error(f"❌ Invalid key format: {key} (expected 'module.key')")
                return key

            module, key_path = parts

            # Load language if not already loaded
            translations = self._load_language(lang)

            # Navigate through nested dict
            if module not in translations:
                logger.warning(f"⚠️ Module '{module}' not found in {lang}")
                # Try fallback language
                if lang != self._default_lang:
                    return self.get_translation(key, lang=self._default_lang, **kwargs)
                return key

            # Get value from module
            value = translations[module]

            # Handle nested keys (e.g., "days.monday" → days["monday"])
            for part in key_path.split("."):
                if isinstance(value, dict):
                    value = value.get(part)
                    if value is None:
                        logger.warning(f"⚠️ Key '{key}' not found in {lang}")
                        return key
                else:
                    logger.warning(f"⚠️ Cannot access '{part}' in non-dict value")
                    return key

            # Interpolate parameters if string template
            if isinstance(value, str) and kwargs:
                try:
                    value = value.format(**kwargs)
                except KeyError as e:
                    logger.warning(f"⚠️ Missing parameter {e} for key '{key}'")

            return str(value)

        except Exception as e:
            logger.error(f"❌ Error getting translation for '{key}': {e}")
            return key

    def get_available_languages(self) -> list[str]:
        """Get list of available language codes."""
        if not self._locales_path.exists():
            return [self._default_lang]

        languages = []
        for lang_dir in self._locales_path.iterdir():
            if lang_dir.is_dir() and lang_dir.name in [Language.SPANISH.value, Language.ENGLISH.value]:
                languages.append(lang_dir.name)

        return sorted(languages) if languages else [self._default_lang]



# Global singleton instance
_manager = TranslationManager()


def t(
    key: str,
    lang: Optional[str] = None,
    **kwargs: Any
) -> str:
    """Translate a key with optional parameter interpolation.

    Shorthand for TranslationManager.get_translation()

    Args:
        key: Translation key in "module.key" format
        lang: Language code ("es" or "en"). Uses context or default if None
        **kwargs: Parameters for string interpolation

    Returns:
        Translated string

    Example:
        >>> t("booking.confirmation", name="Juan")
        "¡Tu reserva ha sido confirmada, Juan!"

        >>> t("booking.confirmation", lang="en", name="John")
        "Your booking has been confirmed, John!"
    """
    return _manager.get_translation(key, lang=lang, **kwargs)


def set_language(lang: str) -> None:
    """Set the current language context for the thread.

    Args:
        lang: Language code ("es" or "en")
    """
    if lang not in [Language.SPANISH.value, Language.ENGLISH.value]:
        logger.warning(f"⚠️ Unknown language '{lang}'")
        return

    _language_context.lang = lang
    logger.debug(f"🌐 Language context set to: {lang}")


def get_language() -> str:
    """Get the current language context for the thread.

    Returns:
        Current language code or default ("es")
    """
    return getattr(_language_context, "lang", None) or _manager._default_lang


def get_days_of_week(lang: Optional[str] = None) -> list[str]:
    """Get localized days of the week.

    Args:
        lang: Language code. Uses context or default if None

    Returns:
        List of day names [Monday, Tuesday, ..., Sunday]
    """
    days = []
    for i in range(7):
        day_key = ["booking.days.monday", "booking.days.tuesday", "booking.days.wednesday", "booking.days.thursday",
                   "booking.days.friday", "booking.days.saturday", "booking.days.sunday"][i]
        days.append(t(day_key, lang=lang))
    return days


def get_months_of_year(lang: Optional[str] = None) -> list[str]:
    """Get localized months of the year.

    Args:
        lang: Language code. Uses context or default if None

    Returns:
        List of month names [January, February, ..., December]
    """
    months = []
    month_keys = [
        "booking.months.january", "booking.months.february", "booking.months.march", "booking.months.april",
        "booking.months.may", "booking.months.june", "booking.months.july", "booking.months.august",
        "booking.months.september", "booking.months.october", "booking.months.november", "booking.months.december"
    ]
    for month_key in month_keys:
        months.append(t(month_key, lang=lang))
    return months


def format_date_localized(
    date_obj: Any,
    lang: Optional[str] = None,
    format_string: str = "{day} {month} de {year}"
) -> str:
    """Format a date object using localized month and day names.

    Args:
        date_obj: datetime.date object
        lang: Language code. Uses context or default if None
        format_string: Format template with {day}, {month}, {year} placeholders

    Returns:
        Formatted date string (e.g., "21 de octubre de 2025")
    """
    try:
        from datetime import date

        if not isinstance(date_obj, date):
            logger.error(f"❌ Invalid date object: {date_obj}")
            return str(date_obj)

        # Get month name
        months = get_months_of_year(lang=lang)
        month_name = months[date_obj.month - 1]

        # Format using template
        formatted = format_string.format(
            day=date_obj.day,
            month=month_name,
            year=date_obj.year
        )

        return formatted

    except Exception as e:
        logger.error(f"❌ Error formatting date: {e}")
        return str(date_obj)


# Export public API
__all__ = [
    "Language",
    "TranslationManager",
    "t",
    "set_language",
    "get_language",
    "get_days_of_week",
    "get_months_of_year",
    "format_date_localized",
]
