"""SentimentClient - Cliente para Sentiment-Service.

Cliente HTTP para el servicio de análisis de sentimientos y urgencia.

Service endpoint: http://localhost:8003/analyze
Method: POST (application/json)

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx not installed. Install with: pip install httpx"
    )

logger = logging.getLogger(__name__)


@dataclass
class SentimentResponse:
    """Respuesta del servicio de análisis de sentimientos.

    Attributes:
        success: Si el análisis fue exitoso
        polarity: Tupla (label, score) - ej: ("negative", 0.89)
        emotion: Tupla (label, score) - ej: ("frustrated", 0.85)
        urgency_level: Nivel de urgencia ("low", "medium", "high", "critical")
        recommendation: Recomendación del sistema
        error: Mensaje de error (si success=False)
    """
    success: bool
    polarity: Optional[List] = None  # [label, score]
    emotion: Optional[List] = None   # [label, score]
    urgency_level: Optional[str] = None
    recommendation: Optional[str] = None
    error: Optional[str] = None

    @property
    def polarity_label(self) -> Optional[str]:
        """Retorna el label de polaridad."""
        return self.polarity[0] if self.polarity else None

    @property
    def polarity_score(self) -> Optional[float]:
        """Retorna el score de polaridad."""
        return self.polarity[1] if self.polarity else None

    @property
    def emotion_label(self) -> Optional[str]:
        """Retorna el label de emoción."""
        return self.emotion[0] if self.emotion else None

    @property
    def emotion_score(self) -> Optional[float]:
        """Retorna el score de emoción."""
        return self.emotion[1] if self.emotion else None

    def is_urgent(self) -> bool:
        """Retorna True si requiere escalamiento urgente.

        Returns:
            True si urgency_level es "high" o "critical"
        """
        return self.urgency_level in ["high", "critical"]


class SentimentClient:
    """Cliente para Sentiment-Service.

    Este cliente maneja la comunicación con el servicio de análisis
    de sentimientos, emociones y detección de urgencia.

    Attributes:
        base_url: URL base del servicio Sentiment
        timeout: Timeout para requests HTTP en segundos
        http_client: Cliente HTTP httpx

    Example:
        >>> client = SentimentClient()
        >>> async with client:
        ...     response = await client.analyze(
        ...         text="I'm really frustrated with this product!",
        ...         user_id="telegram_123"
        ...     )
        ...     if response.success and response.is_urgent():
        ...         print("⚠️ Escalate to support!")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8003",
        timeout: float = 10.0
    ):
        """Inicializa el cliente Sentiment.

        Args:
            base_url: URL base del servicio Sentiment
            timeout: Timeout en segundos para requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager entry."""
        self.http_client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.http_client:
            await self.http_client.aclose()

    async def analyze(
        self,
        text: str,
        user_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> SentimentResponse:
        """Analiza sentimiento, emoción y urgencia de un texto.

        Args:
            text: Texto a analizar
            user_id: Identificador del usuario
            user_context: Contexto adicional del usuario (opcional)
                - previous_sentiment: Sentimiento previo
                - conversation_count: Número de mensajes en la conversación

        Returns:
            SentimentResponse con el análisis completo

        Raises:
            httpx.HTTPError: Si hay error de comunicación

        Example:
            >>> response = await client.analyze(
            ...     text="I'm frustrated!",
            ...     user_id="telegram_123",
            ...     user_context={"previous_sentiment": "neutral", "conversation_count": 5}
            ... )
        """
        if not self.http_client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        # Preparar payload JSON
        payload = {
            "text": text,
            "user_id": user_id
        }

        if user_context:
            payload["user_context"] = user_context

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            logger.info(
                f"[Sentiment] Analyzing text for user_id={user_id}, "
                f"text_preview='{text[:50]}...'"
            )

            response = await self.http_client.post(
                f"{self.base_url}/analyze",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            # Parsear respuesta
            sentiment_response = SentimentResponse(
                success=True,
                polarity=result.get("polarity"),
                emotion=result.get("emotion"),
                urgency_level=result.get("urgency_level"),
                recommendation=result.get("recommendation")
            )

            logger.info(
                f"[Sentiment] ✅ Success - "
                f"Polarity: {sentiment_response.polarity_label} ({sentiment_response.polarity_score:.2f}), "
                f"Emotion: {sentiment_response.emotion_label} ({sentiment_response.emotion_score:.2f}), "
                f"Urgency: {sentiment_response.urgency_level}"
            )

            # Alert si es urgente
            if sentiment_response.is_urgent():
                logger.warning(
                    f"[Sentiment] ⚠️ URGENT - user_id={user_id}, "
                    f"urgency_level={sentiment_response.urgency_level}, "
                    f"recommendation={sentiment_response.recommendation}"
                )

            return sentiment_response

        except httpx.HTTPError as e:
            logger.error(f"[Sentiment] HTTP Error: {e}")
            return SentimentResponse(
                success=False,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[Sentiment] Unexpected error: {e}")
            return SentimentResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    async def analyze_simple(
        self,
        text: str,
        user_id: str
    ) -> SentimentResponse:
        """Versión simplificada de analyze sin contexto adicional.

        Args:
            text: Texto a analizar
            user_id: Identificador del usuario

        Returns:
            SentimentResponse con el análisis

        Example:
            >>> response = await client.analyze_simple(
            ...     text="I'm happy with this service",
            ...     user_id="telegram_123"
            ... )
        """
        return await self.analyze(text=text, user_id=user_id, user_context=None)

    async def health_check(self) -> bool:
        """Verifica si el servicio Sentiment está disponible.

        Returns:
            True si el servicio está healthy, False en caso contrario

        Example:
            >>> is_healthy = await client.health_check()
            >>> print(is_healthy)
            True
        """
        if not self.http_client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        try:
            response = await self.http_client.get(f"{self.base_url}/health")
            response.raise_for_status()
            result = response.json()
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"[Sentiment] Health check failed: {e}")
            return False
