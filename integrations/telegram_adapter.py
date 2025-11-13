"""Telegram Adapter - Bot de Telegram con soporte multimedia para ChatCore.

Este adaptador implementa un bot de Telegram completo que:
- Maneja mensajes de texto, voz, imágenes y documentos
- Convierte contenido multimedia a texto usando servicios ASR/OCR
- Analiza sentimientos y urgencia en todos los mensajes
- Escala conversaciones urgentes a soporte humano
- Usa ChatCore como núcleo de conversación

Dependencies:
    pip install python-telegram-bot httpx

Configuration:
    Set TELEGRAM_BOT_TOKEN in environment or .env file
    Optional: TELEGRAM_SUPPORT_GROUP_ID for escalation

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 2.0.0
"""

from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# Telegram imports
try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    from telegram.error import BadRequest
except ImportError:
    raise ImportError(
        "python-telegram-bot not installed. "
        "Install with: pip install python-telegram-bot"
    )

# Add chat_core to path
chat_core_path = Path(__file__).parent.parent
if str(chat_core_path) not in sys.path:
    sys.path.insert(0, str(chat_core_path))

from chat_core import ChatCore  # noqa: E402
from integrations.clients import ASRClient, OCRClient, SentimentClient  # noqa: E402

logger = logging.getLogger(__name__)


class TelegramAdapter:
    """Adaptador de Telegram con soporte multimedia para ChatCore.

    Este adaptador:
    - Recibe mensajes de texto, voz, imágenes y documentos
    - Convierte multimedia a texto (ASR/OCR)
    - Analiza sentimientos y urgencia
    - Escala a soporte humano si es necesario
    - Procesa todo vía ChatCore
    - Envía respuestas a Telegram

    Attributes:
        chat_core: Instancia de ChatCore
        token: Token del bot de Telegram
        support_group_id: ID del grupo de soporte (opcional)
        application: Application de python-telegram-bot
        asr_client: Cliente para servicio ASR
        ocr_client: Cliente para servicio OCR
        sentiment_client: Cliente para análisis de sentimientos

    Example:
        >>> adapter = TelegramAdapter(token="YOUR_BOT_TOKEN")
        >>> await adapter.initialize()
        >>> await adapter.run()
    """

    def __init__(
        self,
        token: Optional[str] = None,
        support_group_id: Optional[str] = None
    ):
        """Inicializa el adaptador de Telegram.

        Args:
            token: Token del bot de Telegram (opcional, puede venir de env)
            support_group_id: ID del grupo de soporte para escalamiento (opcional)

        Raises:
            ValueError: Si no se proporciona token ni existe TELEGRAM_BOT_TOKEN
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")

        if not self.token:
            raise ValueError(
                "Telegram bot token not provided. "
                "Set TELEGRAM_BOT_TOKEN environment variable or pass token parameter."
            )

        self.support_group_id = support_group_id or os.getenv("TELEGRAM_SUPPORT_GROUP_ID")

        self.chat_core = ChatCore()
        self.application: Optional[Application] = None

        # Clientes para servicios externos (se inicializan al usarse)
        self.asr_client: Optional[ASRClient] = None
        self.ocr_client: Optional[OCRClient] = None
        self.sentiment_client: Optional[SentimentClient] = None

    async def initialize(self) -> None:
        """Inicializa ChatCore y configura el bot de Telegram."""
        # Inicializar ChatCore
        await self.chat_core.initialize()

        # Crear aplicación de Telegram (token ya validado en __init__)
        if not self.token:
            raise RuntimeError("Token not available during initialization")

        self.application = Application.builder().token(self.token).build()

        # Inicializar clientes de servicios externos
        self.asr_client = ASRClient()
        self.ocr_client = OCRClient()
        self.sentiment_client = SentimentClient()

        # Registrar handlers de comandos
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("clear", self._cmd_clear))

        # Registrar handlers multimedia (orden importa: más específico primero)
        self.application.add_handler(
            MessageHandler(filters.VOICE, self._handle_voice_message)
        )
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self._handle_photo_message)
        )
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self._handle_document_message)
        )
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        logger.info("✅ Telegram bot initialized with multimedia support")
        if self.support_group_id:
            logger.info(f"✅ Support escalation configured to group: {self.support_group_id}")
        else:
            logger.warning("⚠️ No support group configured (TELEGRAM_SUPPORT_GROUP_ID not set)")

        print("✅ Telegram bot initialized")

    async def run(self) -> None:
        """Ejecuta el bot de Telegram.

        Este método bloquea hasta que se detenga el bot.
        """
        if not self.application:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        print("🚀 Starting Telegram bot...")
        print("   Press Ctrl+C to stop")

        # Iniciar polling
        await self.application.initialize()
        await self.application.start()

        if self.application.updater:
            await self.application.updater.start_polling()
        else:
            raise RuntimeError("Updater not available")

        # Esperar hasta Ctrl+C
        try:
            import asyncio
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n👋 Stopping bot...")

        # Cleanup
        if self.application.updater:
            await self.application.updater.stop()

        await self.application.stop()
        await self.application.shutdown()
        await self.cleanup()

    async def cleanup(self) -> None:
        """Limpia recursos al finalizar."""
        await self.chat_core.cleanup_all()

        # Cerrar clientes HTTP
        if self.asr_client and hasattr(self.asr_client, 'http_client') and self.asr_client.http_client:
            await self.asr_client.http_client.aclose()
        if self.ocr_client and hasattr(self.ocr_client, 'http_client') and self.ocr_client.http_client:
            await self.ocr_client.http_client.aclose()
        if self.sentiment_client and hasattr(self.sentiment_client, 'http_client') and self.sentiment_client.http_client:
            await self.sentiment_client.http_client.aclose()

    # ==================== Command Handlers ====================

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para comando /start.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.message:
            return

        await update.message.reply_text(
            "*👋 Hi! I'm the Odiseo Assistant.*\n\n"
            "*✨ Features:*\n"
            "• 🎤 *Voice Message Processing* - Automatic transcription with language detection\n"
            "• 🖼️ *Image & Document OCR* - Extract text from photos and PDFs\n"
            "• 🌍 *Multilingual Support* - English, Spanish, French, German, Portuguese, Italian\n"
            "• 📊 *Sentiment Analysis* - Emotion detection and urgency assessment\n"
            "• 🚨 *Smart Escalation* - Automatic routing to support teams for urgent issues\n"
            "• 🤖 *AI-Powered Responses* - Powered by advanced language models\n"
            "• 📅 *Booking & Sales* - Integrated appointment scheduling and product inquiries\n\n"
            "*📋 Commands:*\n"
            "`/help` - Show help\n"
            "`/clear` - Reset conversation\n\n"
            "_How can I help you?_",
            parse_mode="Markdown"
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para comando /help.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.message:
            return

        await update.message.reply_text(
            "*📖 Available Commands:*\n\n"
            "`/start` - Start conversation\n"
            "`/help` - Show this help\n"
            "`/clear` - Reset conversation\n\n"
            "*Supported Input Types:*\n"
            "• 📝 *Text* - Write your query\n"
            "• 🎤 *Voice* - Send voice note\n"
            "• 📷 *Image* - Send photo with text\n"
            "• 📄 *Document* - Send PDF or DOCX\n\n"
            "_Just send me your message and I'll help you._",
            parse_mode="Markdown"
        )

    async def _cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para comando /clear.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.effective_chat or not update.message:
            return

        chat_id = update.effective_chat.id
        session_id = self._generate_session_id(chat_id)

        # Limpiar sesión
        await self.chat_core.cleanup_session(session_id)

        await update.message.reply_text(
            "*✅ Conversation reset!*",
            parse_mode="Markdown"
        )

    # ==================== Message Handlers ====================

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para mensajes de texto.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        # Validaciones
        if not update.message or not update.message.text or not update.effective_chat or not update.effective_user:
            return

        chat_id = update.effective_chat.id
        user = update.effective_user
        text = update.message.text

        logger.info(f"[chat_id={chat_id}] Processing text message...")

        try:
            # Indicar que el bot está escribiendo
            await update.message.chat.send_action("typing")

            # Procesar texto vía función centralizada
            response = await self._process_user_input(
                text=text,
                chat_id=chat_id,
                user=user,
                source_type="text"
            )

            # Enviar respuesta con fallback si Markdown falla
            try:
                await update.message.reply_text(response, parse_mode="Markdown")
            except BadRequest as e:
                if "Can't parse entities" in str(e):
                    logger.warning(f"[chat_id={chat_id}] Markdown parsing failed, sending as plain text")
                    await update.message.reply_text(response)
                else:
                    raise

        except Exception as e:
            logger.exception(f"[chat_id={chat_id}] Error processing text message: {e}")
            await update.message.reply_text(
                f"❌ *Sorry, an error occurred while processing your message.*\n\n"
                f"`Error: {str(e)}`",
                parse_mode="Markdown"
            )

    async def _handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para mensajes de voz.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.message or not update.message.voice or not update.effective_chat or not update.effective_user:
            return

        chat_id = update.effective_chat.id
        user = update.effective_user
        voice = update.message.voice

        logger.info(f"[chat_id={chat_id}] Processing voice message (duration: {voice.duration}s)...")

        try:
            start_time = time.time()

            # Indicar que el bot está procesando
            await update.message.chat.send_action("typing")
            processing_msg = await update.message.reply_text("🎤...")

            # Descargar archivo de voz
            voice_file = await voice.get_file()
            audio_bytes = await voice_file.download_as_bytearray()

            # Transcribir usando ASR
            if not self.asr_client:
                raise RuntimeError("ASR client not initialized")

            async with self.asr_client as asr:
                asr_response = await asr.transcribe(
                    audio_bytes=bytes(audio_bytes),
                    client_id=str(chat_id),
                    language_hint=None,  # Auto-detect language from audio
                    quality_preference="balanced"
                )

            # Actualizar mensaje con idioma detectado
            transcribing_messages = {
                "en": "🎤 Transcribing voice message...",
                "es": "🎤 Transcribiendo mensaje de voz...",
                "fr": "🎤 Transcription du message vocal...",
                "de": "🎤 Sprachnachricht transkribieren...",
                "pt": "🎤 Transcrevendo mensagem de voz...",
                "it": "🎤 Trascrizione del messaggio vocale...",
            }
            detected_lang = asr_response.language if asr_response.success and asr_response.language else "en"
            transcribing_text = transcribing_messages.get(detected_lang, transcribing_messages["en"])
            await processing_msg.edit_text(transcribing_text)

            if not asr_response.success or not asr_response.transcription:
                logger.warning(f"[chat_id={chat_id}] ASR failed: {asr_response.error}")
                await update.message.reply_text(
                    f"❌ *Couldn't transcribe the audio.*\n\n"
                    f"`Error: {asr_response.error or 'Unknown error'}`",
                    parse_mode="Markdown"
                )
                return

            duration = time.time() - start_time
            logger.info(
                f"[chat_id={chat_id}] ASR Success | "
                f"Confidence: {asr_response.confidence:.2f} | "
                f"Duration: {duration:.2f}s"
            )
            logger.info(f"[chat_id={chat_id}] Transcribed text: '{asr_response.transcription}'")

            # Procesar texto transcrito
            response = await self._process_user_input(
                text=asr_response.transcription,
                chat_id=chat_id,
                user=user,
                source_type="voice",
                metadata={
                    "asr_confidence": asr_response.confidence,
                    "asr_language": asr_response.language,
                    "voice_duration": voice.duration,
                    "transcription_time": duration
                }
            )

            # Eliminar mensaje de procesamiento y enviar respuesta con fallback
            await processing_msg.delete()
            try:
                await update.message.reply_text(response, parse_mode="Markdown")
            except BadRequest as e:
                if "Can't parse entities" in str(e):
                    logger.warning(f"[chat_id={chat_id}] Markdown parsing failed, sending as plain text")
                    await update.message.reply_text(response)
                else:
                    raise

        except Exception as e:
            logger.exception(f"[chat_id={chat_id}] Error processing voice message: {e}")
            await update.message.reply_text(
                f"❌ *Error processing voice message.*\n\n"
                f"`Error: {str(e)}`",
                parse_mode="Markdown"
            )

    async def _handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para mensajes con imágenes.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.message or not update.message.photo or not update.effective_chat or not update.effective_user:
            return

        chat_id = update.effective_chat.id
        user = update.effective_user

        logger.info(f"[chat_id={chat_id}] Processing photo message...")

        try:
            start_time = time.time()

            await update.message.chat.send_action("typing")
            await update.message.reply_text("📷 *Extracting text from image...*", parse_mode="Markdown")

            # Obtener la foto de mayor resolución
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            photo_bytes = await photo_file.download_as_bytearray()

            # Extraer texto usando OCR
            if not self.ocr_client:
                raise RuntimeError("OCR client not initialized")

            async with self.ocr_client as ocr:
                ocr_response = await ocr.extract_from_photo(
                    photo_bytes=bytes(photo_bytes),
                    client_id=str(chat_id),
                    quality="balanced"
                )

            if not ocr_response.success or not ocr_response.text:
                logger.warning(f"[chat_id={chat_id}] OCR failed: {ocr_response.error}")
                await update.message.reply_text(
                    f"❌ *Couldn't extract text from the image.*\n\n"
                    f"`Error: {ocr_response.error or 'No text found'}`",
                    parse_mode="Markdown"
                )
                return

            duration = time.time() - start_time
            logger.info(
                f"[chat_id={chat_id}] OCR Success | "
                f"Confidence: {ocr_response.confidence:.2f} | "
                f"Duration: {duration:.2f}s | "
                f"Text length: {len(ocr_response.text)} chars"
            )

            # Procesar texto extraído
            response = await self._process_user_input(
                text=ocr_response.text,
                chat_id=chat_id,
                user=user,
                source_type="photo",
                metadata={
                    "ocr_confidence": ocr_response.confidence,
                    "extraction_time": duration,
                    "image_size": f"{photo.width}x{photo.height}"
                }
            )

            # Enviar respuesta con fallback si Markdown falla
            try:
                await update.message.reply_text(response, parse_mode="Markdown")
            except BadRequest as e:
                if "Can't parse entities" in str(e):
                    logger.warning(f"[chat_id={chat_id}] Markdown parsing failed, sending as plain text")
                    await update.message.reply_text(response)
                else:
                    raise

        except Exception as e:
            logger.exception(f"[chat_id={chat_id}] Error processing photo: {e}")
            await update.message.reply_text(
                f"❌ *Error processing image.*\n\n"
                f"`Error: {str(e)}`",
                parse_mode="Markdown"
            )

    async def _handle_document_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para mensajes con documentos.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.message or not update.message.document or not update.effective_chat or not update.effective_user:
            return

        chat_id = update.effective_chat.id
        user = update.effective_user
        document = update.message.document

        logger.info(f"[chat_id={chat_id}] Processing document: {document.file_name}")

        try:
            # Validar extensión soportada
            file_extension = Path(document.file_name or "").suffix.lower().replace('.', '')
            supported_extensions = ["pdf", "docx", "png", "jpg", "jpeg"]

            if file_extension not in supported_extensions:
                await update.message.reply_text(
                    f"❌ *Unsupported format:* `.{file_extension}`\n\n"
                    f"*Supported formats:* `{', '.join(supported_extensions)}`",
                    parse_mode="Markdown"
                )
                return

            start_time = time.time()

            await update.message.chat.send_action("typing")
            await update.message.reply_text(f"📄 *Extracting text from* `{document.file_name}`*...*", parse_mode="Markdown")

            # Descargar documento
            doc_file = await document.get_file()
            doc_bytes = await doc_file.download_as_bytearray()

            # Extraer texto usando OCR
            if not self.ocr_client:
                raise RuntimeError("OCR client not initialized")

            async with self.ocr_client as ocr:
                ocr_response = await ocr.extract_from_document(
                    document_bytes=bytes(doc_bytes),
                    file_extension=file_extension,
                    client_id=str(chat_id),
                    quality="balanced"
                )

            if not ocr_response.success or not ocr_response.text:
                logger.warning(f"[chat_id={chat_id}] OCR failed: {ocr_response.error}")
                await update.message.reply_text(
                    f"❌ *Couldn't extract text from the document.*\n\n"
                    f"`Error: {ocr_response.error or 'No text found'}`",
                    parse_mode="Markdown"
                )
                return

            duration = time.time() - start_time
            logger.info(
                f"[chat_id={chat_id}] OCR Success | "
                f"Confidence: {ocr_response.confidence:.2f} | "
                f"Duration: {duration:.2f}s | "
                f"Text length: {len(ocr_response.text)} chars"
            )

            # Procesar texto extraído
            response = await self._process_user_input(
                text=ocr_response.text,
                chat_id=chat_id,
                user=user,
                source_type="document",
                metadata={
                    "ocr_confidence": ocr_response.confidence,
                    "extraction_time": duration,
                    "file_name": document.file_name,
                    "file_type": file_extension
                }
            )

            # Enviar respuesta con fallback si Markdown falla
            try:
                await update.message.reply_text(response, parse_mode="Markdown")
            except BadRequest as e:
                if "Can't parse entities" in str(e):
                    logger.warning(f"[chat_id={chat_id}] Markdown parsing failed, sending as plain text")
                    await update.message.reply_text(response)
                else:
                    raise

        except Exception as e:
            logger.exception(f"[chat_id={chat_id}] Error processing document: {e}")
            await update.message.reply_text(
                f"❌ *Error processing document.*\n\n"
                f"`Error: {str(e)}`",
                parse_mode="Markdown"
            )

    # ==================== Core Processing ====================

    async def _process_user_input(
        self,
        text: str,
        chat_id: int,
        user,
        source_type: str = "text",
        metadata: Optional[dict] = None
    ) -> str:
        """Función centralizada de procesamiento de entrada del usuario.

        Esta función:
        1. Analiza sentimientos y urgencia
        2. Escala a soporte si es necesario
        3. Procesa mensaje vía ChatCore
        4. Retorna respuesta

        Args:
            text: Texto a procesar (puede venir de texto, ASR, OCR)
            chat_id: ID del chat de Telegram
            user: Objeto User de Telegram
            source_type: Tipo de fuente ("text", "voice", "photo", "document")
            metadata: Metadatos adicionales (opcional)

        Returns:
            Respuesta en texto plano para el usuario

        Raises:
            Exception: Si hay error en procesamiento
        """
        session_id = self._generate_session_id(chat_id)
        customer_email = user.username if user.username else f"telegram_user_{user.id}"

        # Metadata completa
        full_metadata = {
            "chat_id": chat_id,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "source_type": source_type,
            **(metadata or {})
        }

        try:
            # Obtener sesión para contexto
            session = self.chat_core.session_manager.get_or_create_session(
                session_id=session_id,
                customer_email=customer_email,
                metadata=full_metadata
            )

            # Obtener contexto del usuario para análisis de sentimientos
            user_context = session.get_user_context()

            # 1. Analizar sentimiento con contexto completo
            if not self.sentiment_client:
                raise RuntimeError("Sentiment client not initialized")

            async with self.sentiment_client as sentiment:
                sentiment_response = await sentiment.analyze(
                    text=text,
                    user_id=str(chat_id),
                    user_context=user_context
                )

            if sentiment_response.success:
                logger.info(
                    f"[chat_id={chat_id}] Sentiment: {sentiment_response.polarity_label} "
                    f"({sentiment_response.polarity_score:.2f}) | "
                    f"Emotion: {sentiment_response.emotion_label} "
                    f"({sentiment_response.emotion_score:.2f}) | "
                    f"Urgency: {sentiment_response.urgency_level} | "
                    f"Context: prev={user_context['previous_sentiment']}, "
                    f"msg_count={user_context['conversation_count']}"
                )

                # Agregar sentimientos a metadata
                full_metadata["sentiment"] = {
                    "polarity": sentiment_response.polarity_label,
                    "polarity_score": sentiment_response.polarity_score,
                    "emotion": sentiment_response.emotion_label,
                    "emotion_score": sentiment_response.emotion_score,
                    "urgency_level": sentiment_response.urgency_level
                }

                # Actualizar sesión con nuevo sentimiento
                session.update_sentiment(sentiment_response.polarity_label)

                # 2. Escalar si es urgente
                if sentiment_response.is_urgent():
                    logger.warning(
                        f"[chat_id={chat_id}] ⚠️ URGENT ESCALATION TRIGGERED | "
                        f"Urgency: {sentiment_response.urgency_level} | "
                        f"Recommendation: {sentiment_response.recommendation}"
                    )
                    await self._escalate_to_support(
                        chat_id=chat_id,
                        user=user,
                        text=text,
                        sentiment=sentiment_response
                    )
            else:
                logger.warning(f"[chat_id={chat_id}] Sentiment analysis failed: {sentiment_response.error}")

            # Incrementar contador de mensajes
            session.increment_message_count()

            # 3. Procesar mensaje vía ChatCore (flujo normal)
            response = await self.chat_core.process_message(
                session_id=session_id,
                user_message=text,
                customer_email=customer_email,
                metadata=full_metadata
            )

            return response

        except Exception as e:
            logger.exception(f"[chat_id={chat_id}] Error in _process_user_input: {e}")
            raise

    async def _escalate_to_support(
        self,
        chat_id: int,
        user,
        text: str,
        sentiment
    ) -> None:
        """Escala conversación a grupo de soporte humano.

        Args:
            chat_id: ID del chat
            user: Objeto User de Telegram
            text: Texto del mensaje
            sentiment: Resultado del análisis de sentimientos
        """
        if not self.support_group_id:
            logger.warning(
                f"[chat_id={chat_id}] Escalation needed but no support group configured"
            )
            return

        try:
            # Formatear mensaje de alerta
            alert_message = (
                f"🚨 ESCALATION ALERT\n\n"
                f"User: {user.first_name} {user.last_name or ''} (@{user.username or 'N/A'})\n"
                f"Chat ID: {chat_id}\n"
                f"Urgency: {sentiment.urgency_level}\n"
                f"Polarity: {sentiment.polarity_label} ({sentiment.polarity_score:.2f})\n"
                f"Emotion: {sentiment.emotion_label} ({sentiment.emotion_score:.2f})\n\n"
                f"Message:\n{text}\n\n"
                f"Recommendation: {sentiment.recommendation}"
            )

            # Enviar alerta al grupo de soporte
            if self.application and self.application.bot:
                await self.application.bot.send_message(
                    chat_id=self.support_group_id,
                    text=alert_message
                )

            logger.info(f"[chat_id={chat_id}] Escalation alert sent to support group")

        except Exception as e:
            logger.error(f"[chat_id={chat_id}] Failed to escalate to support: {e}")

    # ==================== Helpers ====================

    def _generate_session_id(self, chat_id: int) -> str:
        """Genera session_id único para un chat de Telegram.

        Args:
            chat_id: ID del chat de Telegram

        Returns:
            session_id en formato "telegram_{chat_id}"

        Example:
            >>> adapter._generate_session_id(123456)
            'telegram_123456'
        """
        return f"telegram_{chat_id}"
