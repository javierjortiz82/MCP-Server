"""OCRClient - Cliente para Image Analysis Service.

Cliente HTTP para el servicio de análisis de imágenes y documentos.
Soporta OCR automático y detección de objetos.

Service endpoint: http://localhost:8004/analyze
Method: POST (application/json)

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

import base64
from typing import Optional
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
class OCRResponse:
    """Respuesta del servicio OCR.

    Attributes:
        success: Si la extracción fue exitosa
        text: Texto extraído del documento/imagen
        confidence: Nivel de confianza (0.0-1.0)
        error: Mensaje de error (si success=False)
    """
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None


class OCRClient:
    """Cliente para OCR-Multilang Service.

    Este cliente maneja la comunicación con el servicio de extracción
    de texto desde imágenes y documentos (OCR - Optical Character Recognition).

    Soporta: PDF, JPG, PNG, DOCX

    Attributes:
        base_url: URL base del servicio OCR
        timeout: Timeout para requests HTTP en segundos
        http_client: Cliente HTTP httpx

    Example:
        >>> client = OCRClient()
        >>> async with client:
        ...     response = await client.extract(
        ...         file_bytes=image_data,
        ...         file_type="jpg",
        ...         client_id="telegram_123"
        ...     )
        ...     if response.success:
        ...         print(response.text)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8004",
        timeout: float = 60.0  # OCR puede tardar más
    ):
        """Inicializa el cliente OCR.

        Args:
            base_url: URL base del servicio OCR
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

    async def extract(
        self,
        file_bytes: bytes,
        file_type: str,
        client_id: str,
        quality: str = "balanced",
        language_hints: Optional[str] = None
    ) -> OCRResponse:
        """Extrae texto desde un archivo (imagen o documento).

        Args:
            file_bytes: Bytes del archivo
            file_type: Tipo de archivo ("pdf", "jpg", "png", "docx")
            client_id: Identificador del cliente (chat_id)
            quality: Calidad del procesamiento ("fast", "balanced", "accurate")
            language_hints: Idiomas esperados, ej: "en,es" (opcional)

        Returns:
            OCRResponse con el texto extraído

        Raises:
            httpx.HTTPError: Si hay error de comunicación

        Example:
            >>> response = await client.extract(
            ...     file_bytes=pdf_data,
            ...     file_type="pdf",
            ...     client_id="telegram_123",
            ...     quality="balanced"
            ... )
        """
        if not self.http_client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        # Codificar archivo en base64
        file_data_b64 = base64.b64encode(file_bytes).decode("utf-8")

        # Adaptar client_id al formato requerido: "user_id:chat_id"
        # Si ya tiene ":", lo dejamos; si no, usamos "telegram:client_id"
        if ":" not in client_id:
            formatted_client_id = f"telegram:{client_id}"
        else:
            formatted_client_id = client_id

        # Preparar payload JSON para el servicio de análisis
        payload = {
            "file_data": file_data_b64,
            "file_type": file_type.lower(),
            "client_id": formatted_client_id,
            "mode": "auto",  # auto, ocr, detection, both
            "quality": quality,
            "enable_preprocessing": True,
            "classification_threshold": 0.8,
            "max_detection_results": 10,
            "min_detection_confidence": 0.5
        }

        # Convertir language_hints de string "en,es" a lista ["en", "es"]
        if language_hints:
            if isinstance(language_hints, str):
                payload["language_hints"] = [lang.strip() for lang in language_hints.split(",")]
            else:
                payload["language_hints"] = language_hints

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            logger.info(
                f"[Analyze] Processing {file_type} for client_id={formatted_client_id}, "
                f"mode=auto, quality={quality}"
            )

            response = await self.http_client.post(
                f"{self.base_url}/analyze",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            # Parsear respuesta de AnalyzeResponse
            # Campos: result, classification, ocr_result, detection_result, processing_time, etc.

            # Caso 1: Error explícito
            if "error" in result:
                error_message = result.get("message", result.get("error", "Unknown error"))
                ocr_response = OCRResponse(
                    success=False,
                    error=error_message
                )
                logger.warning(f"[Analyze] ❌ Failed - Error: {ocr_response.error}")
                return ocr_response

            # Caso 2: Respuesta exitosa de AnalyzeResponse
            # El campo "result" contiene el texto unificado (OCR o descripción de objeto)
            text = result.get("result") or ""
            confidence = None

            # Extraer confidence de ocr_result si existe
            ocr_result = result.get("ocr_result")
            if ocr_result:
                confidence = ocr_result.get("confidence")
                # Si result está vacío pero hay texto en ocr_result, usarlo
                if not text and ocr_result.get("text"):
                    text = ocr_result.get("text")

            # Si no hay ocr_result, intentar de detection_result
            detection_result = result.get("detection_result")
            if detection_result:
                objects = detection_result.get("objects", [])
                if objects:
                    # Usar el score del primer objeto detectado
                    if confidence is None:
                        confidence = objects[0].get("score")
                    # Si result está vacío pero hay objetos detectados, usar el nombre
                    if not text:
                        text = objects[0].get("name", "")

            # Obtener clasificación para logging
            classification = result.get("classification", {})
            classification_type = classification.get("classification", "unknown")

            ocr_response = OCRResponse(
                success=True,
                text=text,
                confidence=confidence
            )

            text_preview = text[:100] if text else ""
            confidence_str = f"{confidence:.2f}" if confidence is not None else "N/A"
            logger.info(
                f"[Analyze] ✅ Success ({classification_type}) - "
                f"Result: {len(text or '')} chars (confidence: {confidence_str}) - "
                f"Preview: '{text_preview}...'"
            )

            return ocr_response

        except httpx.HTTPError as e:
            logger.error(f"[Analyze] HTTP Error: {e}")
            return OCRResponse(
                success=False,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[Analyze] Unexpected error: {e}")
            return OCRResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    async def extract_from_photo(
        self,
        photo_bytes: bytes,
        client_id: str,
        quality: str = "balanced"
    ) -> OCRResponse:
        """Método conveniente para extraer texto desde foto.

        Args:
            photo_bytes: Bytes de la imagen
            client_id: Identificador del cliente
            quality: Calidad del procesamiento

        Returns:
            OCRResponse con el texto extraído

        Example:
            >>> response = await client.extract_from_photo(
            ...     photo_bytes=image_data,
            ...     client_id="telegram_123"
            ... )
        """
        # Telegram generalmente envía fotos como JPG
        return await self.extract(
            file_bytes=photo_bytes,
            file_type="jpg",
            client_id=client_id,
            quality=quality
        )

    async def extract_from_document(
        self,
        document_bytes: bytes,
        file_extension: str,
        client_id: str,
        quality: str = "balanced"
    ) -> OCRResponse:
        """Método conveniente para extraer texto desde documento.

        Args:
            document_bytes: Bytes del documento
            file_extension: Extensión del archivo (sin punto, ej: "pdf")
            client_id: Identificador del cliente
            quality: Calidad del procesamiento

        Returns:
            OCRResponse con el texto extraído

        Example:
            >>> response = await client.extract_from_document(
            ...     document_bytes=pdf_data,
            ...     file_extension="pdf",
            ...     client_id="telegram_123"
            ... )
        """
        return await self.extract(
            file_bytes=document_bytes,
            file_type=file_extension.lower().replace('.', ''),
            client_id=client_id,
            quality=quality
        )

    async def health_check(self) -> bool:
        """Verifica si el servicio OCR está disponible.

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
            logger.error(f"[Analyze] Health check failed: {e}")
            return False
