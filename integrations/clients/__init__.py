"""Clients para servicios externos de procesamiento multimedia.

Este módulo contiene clientes HTTP para:
- ASRClient: Transcripción de voz a texto (Voice-ASR service)
- OCRClient: Extracción de texto desde imágenes/documentos
- SentimentClient: Análisis de sentimientos y urgencia

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from integrations.clients.asr_client import ASRClient
from integrations.clients.ocr_client import OCRClient
from integrations.clients.sentiment_client import SentimentClient

__all__ = ["ASRClient", "OCRClient", "SentimentClient"]
