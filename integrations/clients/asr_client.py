"""ASRClient - Cliente para Voice-ASR Service.

Cliente HTTP para el servicio de transcripción de voz a texto.

Service endpoint: http://localhost:8002/transcribe
Method: POST (Multipart Form-Data)

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

import uuid
from typing import Optional, Union
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
class ASRResponse:
    """Respuesta del servicio ASR.

    Attributes:
        success: Si la transcripción fue exitosa
        transcription: Texto transcrito
        language: Idioma detectado
        confidence: Nivel de confianza (0.0-1.0)
        error: Mensaje de error (si success=False)
        error_code: Código de error (si success=False)
    """
    success: bool
    transcription: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class ASRClient:
    """Cliente para Voice-ASR Service.

    Este cliente maneja la comunicación con el servicio de transcripción
    de voz a texto (ASR - Automatic Speech Recognition).

    Attributes:
        base_url: URL base del servicio ASR
        timeout: Timeout para requests HTTP en segundos
        http_client: Cliente HTTP httpx

    Example:
        >>> client = ASRClient()
        >>> async with client:
        ...     response = await client.transcribe(
        ...         audio_bytes=audio_data,
        ...         client_id="telegram_123",
        ...         language_hint="es"
        ...     )
        ...     if response.success:
        ...         print(response.transcription)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        timeout: float = 30.0
    ):
        """Inicializa el cliente ASR.

        Args:
            base_url: URL base del servicio ASR
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

    async def transcribe(
        self,
        audio_bytes: bytes,
        client_id: str,
        language_hint: Optional[str] = None,
        quality_preference: str = "balanced"
    ) -> ASRResponse:
        """Transcribe audio a texto.

        Args:
            audio_bytes: Bytes del archivo de audio (.ogg)
            client_id: Identificador del cliente (chat_id)
            language_hint: Sugerencia de idioma ("en", "es", etc.) o None para auto-detección
            quality_preference: Preferencia de calidad ("fast", "balanced", "accurate")

        Returns:
            ASRResponse con el resultado de la transcripción

        Raises:
            httpx.HTTPError: Si hay error de comunicación

        Example:
            >>> response = await client.transcribe(
            ...     audio_bytes=audio_data,
            ...     client_id="telegram_123",
            ...     language_hint="es",
            ...     quality_preference="balanced"
            ... )
        """
        if not self.http_client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        # Preparar archivos y datos para multipart/form-data
        files = {
            'audio_file': ('voice_message.ogg', audio_bytes, 'audio/ogg')
        }

        data = {
            'client_id': client_id,
            'quality_preference': quality_preference
        }

        # Solo incluir language_hint si se proporciona (permite auto-detección)
        if language_hint is not None:
            data['language_hint'] = language_hint

        headers = {
            'X-Request-ID': str(uuid.uuid4())
        }

        try:
            lang_info = f"language={language_hint}" if language_hint else "language=AUTO-DETECT"
            logger.info(
                f"[ASR] Transcribing audio for client_id={client_id}, "
                f"{lang_info}, quality={quality_preference}"
            )

            response = await self.http_client.post(
                f"{self.base_url}/transcribe",
                files=files,
                data=data,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            # Parsear respuesta exitosa
            if result.get("success"):
                data_obj = result.get("data", {})
                asr_response = ASRResponse(
                    success=True,
                    transcription=data_obj.get("transcription"),
                    language=data_obj.get("language"),
                    confidence=data_obj.get("confidence")
                )

                logger.info(
                    f"[ASR] ✅ Success - Transcription: '{asr_response.transcription}' "
                    f"(confidence: {asr_response.confidence:.2f})"
                )

                return asr_response
            else:
                # Respuesta con error
                asr_response = ASRResponse(
                    success=False,
                    error=result.get("error", "Unknown error"),
                    error_code=result.get("error_code", "UNKNOWN")
                )

                logger.warning(
                    f"[ASR] ❌ Failed - Error: {asr_response.error} "
                    f"(code: {asr_response.error_code})"
                )

                return asr_response

        except httpx.HTTPError as e:
            logger.error(f"[ASR] HTTP Error: {e}")
            return ASRResponse(
                success=False,
                error=f"HTTP error: {str(e)}",
                error_code="HTTP_ERROR"
            )
        except Exception as e:
            logger.error(f"[ASR] Unexpected error: {e}")
            return ASRResponse(
                success=False,
                error=f"Unexpected error: {str(e)}",
                error_code="UNEXPECTED_ERROR"
            )

    async def health_check(self) -> bool:
        """Verifica si el servicio ASR está disponible.

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
            logger.error(f"[ASR] Health check failed: {e}")
            return False
