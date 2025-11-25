"""OCRClient - Cliente para OCR Service.

Cliente HTTP para el servicio de extracción de texto desde imágenes y documentos.

Service endpoint: http://localhost:8004/ocr
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

        # Preparar payload JSON para el nuevo servicio OCR
        payload = {
            "file_data": file_data_b64,
            "file_type": file_type.lower(),
            "client_id": formatted_client_id,
            "quality": quality,
            "enable_preprocessing": True,
            "return_confidence": True
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
                f"[OCR] Extracting text from {file_type} for client_id={formatted_client_id}, "
                f"quality={quality}"
            )

            response = await self.http_client.post(
                f"{self.base_url}/ocr",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            # Parsear respuesta según formato del servidor
            # El servidor OCR tiene 3 formatos posibles:

            # Caso 1: Éxito (formato real del servidor - tiene "text" sin "error")
            if "text" in result and "error" not in result:
                ocr_response = OCRResponse(
                    success=True,
                    text=result.get("text"),
                    confidence=result.get("confidence")
                )

                text_preview = ocr_response.text[:100] if ocr_response.text else ""
                logger.info(
                    f"[OCR] ✅ Success - Extracted {len(ocr_response.text or '')} chars "
                    f"(confidence: {ocr_response.confidence:.2f}) - Preview: '{text_preview}...'"
                )

                return ocr_response

            # Caso 2: Error (formato real del servidor - tiene campo "error")
            elif "error" in result:
                # El servidor envía "message" con el error legible
                error_message = result.get("message", result.get("error", "Unknown error"))

                ocr_response = OCRResponse(
                    success=False,
                    error=error_message
                )

                logger.warning(
                    f"[OCR] ❌ Failed - Error: {ocr_response.error} "
                    f"(code: {result.get('error', 'N/A')})"
                )

                return ocr_response

            # Caso 3: Formato documentado (por compatibilidad futura)
            elif "success" in result:
                if result.get("success"):
                    ocr_response = OCRResponse(
                        success=True,
                        text=result.get("text"),
                        confidence=result.get("confidence")
                    )

                    text_preview = ocr_response.text[:100] if ocr_response.text else ""
                    logger.info(
                        f"[OCR] ✅ Success (documented format) - Extracted {len(ocr_response.text or '')} chars "
                        f"(confidence: {ocr_response.confidence:.2f}) - Preview: '{text_preview}...'"
                    )

                    return ocr_response
                else:
                    ocr_response = OCRResponse(
                        success=False,
                        error=result.get("error", "Unknown error")
                    )

                    logger.warning(f"[OCR] ❌ Failed (documented format) - Error: {ocr_response.error}")

                    return ocr_response

            # Caso 4: Formato desconocido
            else:
                logger.error(
                    f"[OCR] ⚠️ Unknown response format from OCR service. "
                    f"Response keys: {list(result.keys())}"
                )

                ocr_response = OCRResponse(
                    success=False,
                    error="Invalid response format from OCR service"
                )

                return ocr_response

        except httpx.HTTPError as e:
            logger.error(f"[OCR] HTTP Error: {e}")
            return OCRResponse(
                success=False,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[OCR] Unexpected error: {e}")
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
            logger.error(f"[OCR] Health check failed: {e}")
            return False
