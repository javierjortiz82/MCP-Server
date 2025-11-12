"""Language Detection Service using Gemini 2.5 Flash.

This service uses Gemini AI to detect the language of user input,
eliminating hardcoded keywords and providing robust, scalable detection.

Architecture:
    1. Gemini-based detection (primary)
    2. Session-based caching (avoid repeated API calls)
    3. Configurable supported languages
    4. Fallback to session language when ambiguous

Benefits over keyword-based detection:
    - No hardcoded keywords to maintain
    - Handles new languages without code changes
    - Better accuracy on short texts and edge cases
    - Context-aware detection (idioms, expressions)
    - Automatic updates as Gemini improves

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Literal, Optional

from google import genai
from google.genai import types

from client_mcp.config.settings import settings
from client_mcp.utils.logger import get_logger

logger = get_logger("LanguageDetectorService", settings.LOG_LEVEL)


class LanguageDetectorService:
    """Gemini-powered language detection service.

    Uses Gemini 2.5 Flash to detect user language with high accuracy,
    eliminating the need for hardcoded keywords.

    Attributes:
        client: Gemini API client
        model_name: Model to use (default: Gemini 2.5 Flash)
        cache: In-memory cache for recent detections
        supported_languages: List of supported language codes

    Example:
        >>> detector = LanguageDetectorService()
        >>> await detector.initialize()
        >>> lang = await detector.detect_language("proximo martes")
        >>> print(lang)
        'es'
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        supported_languages: Optional[list[str]] = None
    ):
        """Initialize language detector service.

        Args:
            api_key: Google API key (uses settings if not provided)
            model_name: Model name (default: Gemini 2.5 Flash)
            supported_languages: List of language codes (default: ["en", "es"])
        """
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or "gemini-2.5-flash"
        self.supported_languages = supported_languages or ["en", "es"]
        self.client: Optional[genai.Client] = None
        self._cache: dict[str, str] = {}
        self._prompt_template: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize Gemini client and load prompt template."""
        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"✅ LanguageDetectorService initialized with model: {self.model_name}")

        # Load prompt template
        self._prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load language detection prompt template.

        Returns:
            Prompt template string

        Note:
            Loads from Jinja2 template file for easy customization
        """
        try:
            # Try to load from Jinja2 template
            # Correct path: go up to agent/src/ and then to multi_agent module
            from multi_agent.prompt_manager import PromptManager

            pm = PromptManager()
            template = pm.env.get_template("base/language_detection.jinja2")
            prompt = template.render(
                supported_languages=[
                    {"code": code, "name": self._get_language_name(code)}
                    for code in self.supported_languages
                ]
            )
            logger.debug("✅ Loaded language detection template from Jinja2")
            return prompt

        except Exception as e:
            logger.warning(f"Could not load Jinja2 template: {e}. Using fallback prompt.")
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt if Jinja2 template fails to load.

        Returns:
            Fallback prompt string
        """
        langs = ", ".join([f"{code} ({self._get_language_name(code)})" for code in self.supported_languages])
        return f"""You are a language detection system.

Detect the language of the user's text.

Supported languages: {langs}

Respond with ONLY the language code (e.g., "en", "es") or "null" if ambiguous.

Examples:
- "proximo martes" → es
- "I want a laptop" → en
- "123" → null
"""

    def _get_language_name(self, code: str) -> str:
        """Get human-readable language name.

        Args:
            code: Language code

        Returns:
            Language name
        """
        names = {
            "en": "English",
            "es": "Spanish (Español)",
            "fr": "French (Français)",
            "de": "German (Deutsch)",
            "pt": "Portuguese (Português)",
            "it": "Italian (Italiano)",
        }
        return names.get(code, code.upper())

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text.

        Args:
            text: Input text

        Returns:
            MD5 hash of normalized text
        """
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    async def detect_language(
        self,
        text: str,
        session_language: Optional[str] = None,
        use_cache: bool = True
    ) -> Literal["en", "es"] | str:
        """Detect language of user input using Gemini.

        Args:
            text: User input text
            session_language: Current session language (fallback for ambiguous)
            use_cache: Whether to use cached results (default: True)

        Returns:
            Language code ("en", "es", etc.) or session_language if ambiguous

        Example:
            >>> lang = await detector.detect_language("proximo martes")
            >>> print(lang)
            'es'

            >>> lang = await detector.detect_language("18", session_language="es")
            >>> print(lang)
            'es'  # Fallback to session language
        """
        if not self.client:
            raise RuntimeError("LanguageDetectorService not initialized. Call initialize() first.")

        # Validate input
        if not text or len(text.strip()) == 0:
            logger.debug("Empty input - using session language or default")
            return session_language or "en"

        # Check cache
        cache_key = self._get_cache_key(text)
        if use_cache and cache_key in self._cache:
            cached_lang = self._cache[cache_key]
            logger.debug(f"🔄 Cache hit for '{text[:30]}...' → {cached_lang}")
            return cached_lang

        # Detect using Gemini (simple approach)
        try:
            logger.debug(f"🔍 Detecting language for: '{text[:50]}...'")

            # Simple prompt
            prompt = f"{self._prompt_template}\n\nText to analyze: {text}\n\nLanguage code:"

            # CRITICAL: max_output_tokens must be >= 2048 for reliability
            # Reference: https://github.com/googleapis/python-genai/issues/1289
            config = types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=2048,  # Prevents empty responses
                response_mime_type="text/plain",
            )

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Extract language code
            if not response or not response.candidates:
                raise RuntimeError("Empty response from Gemini")

            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise RuntimeError("No content in response")

            detected = candidate.content.parts[0].text.strip().lower()

            # Handle "null" or ambiguous responses
            if detected == "null" or detected not in self.supported_languages:
                logger.debug(f"Ambiguous detection: '{detected}' - using session language")
                detected = session_language or "en"

            # Cache result
            self._cache[cache_key] = detected
            if len(self._cache) > 1000:
                for key in list(self._cache.keys())[:200]:
                    del self._cache[key]

            logger.info(f"🌐 Language detected: {detected} for '{text[:30]}...'")
            return detected

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            fallback = session_language or "en"
            logger.warning(f"Using fallback language: {fallback}")
            return fallback

    def clear_cache(self) -> None:
        """Clear language detection cache.

        Useful for testing or when you want fresh detections.
        """
        self._cache.clear()
        logger.debug("Cache cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with cache size and hit rate info
        """
        return {
            "size": len(self._cache),
            "max_size": 1000,
        }
