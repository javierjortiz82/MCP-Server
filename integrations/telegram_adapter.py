"""Telegram Adapter - Bot de Telegram para ChatCore.

Este adaptador implementa un bot de Telegram que usa ChatCore
como núcleo de conversación, permitiendo comunicación sin
duplicar lógica de negocio.

Dependencies:
    pip install python-telegram-bot

Configuration:
    Set TELEGRAM_BOT_TOKEN in environment or .env file

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

import os
import sys
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


class TelegramAdapter:
    """Adaptador de Telegram para ChatCore.

    Este adaptador:
    - Recibe mensajes de Telegram
    - Genera session_id único por chat_id
    - Procesa mensajes vía ChatCore
    - Envía respuestas a Telegram
    - Maneja comandos /start, /help, /clear

    Attributes:
        chat_core: Instancia de ChatCore
        token: Token del bot de Telegram
        application: Application de python-telegram-bot

    Example:
        >>> adapter = TelegramAdapter(token="YOUR_BOT_TOKEN")
        >>> await adapter.initialize()
        >>> await adapter.run()
    """

    def __init__(self, token: Optional[str] = None):
        """Inicializa el adaptador de Telegram.

        Args:
            token: Token del bot de Telegram (opcional, puede venir de env)

        Raises:
            ValueError: Si no se proporciona token ni existe TELEGRAM_BOT_TOKEN
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")

        if not self.token:
            raise ValueError(
                "Telegram bot token not provided. "
                "Set TELEGRAM_BOT_TOKEN environment variable or pass token parameter."
            )

        self.chat_core = ChatCore()
        self.application: Optional[Application] = None

    async def initialize(self) -> None:
        """Inicializa ChatCore y configura el bot de Telegram."""
        # Inicializar ChatCore
        await self.chat_core.initialize()

        # Crear aplicación de Telegram (token ya validado en __init__)
        if not self.token:
            raise RuntimeError("Token not available during initialization")

        self.application = Application.builder().token(self.token).build()

        # Registrar handlers
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("clear", self._cmd_clear))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

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

    # ==================== Handlers ====================

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para comando /start.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        if not update.message:
            return

        await update.message.reply_text(
            "👋 ¡Hola! Soy el asistente de Lab01-MCP.\n\n"
            "Puedo ayudarte con:\n"
            "• Búsqueda de productos\n"
            "• Reservas de citas\n"
            "• Información general\n\n"
            "Comandos:\n"
            "/help - Mostrar ayuda\n"
            "/clear - Reiniciar conversación\n\n"
            "¿En qué puedo ayudarte?"
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
            "📖 Comandos disponibles:\n\n"
            "/start - Iniciar conversación\n"
            "/help - Mostrar esta ayuda\n"
            "/clear - Reiniciar conversación\n\n"
            "Simplemente escríbeme tu pregunta y te ayudaré."
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

        await update.message.reply_text("✅ Conversación reiniciada")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: ARG002
        """Handler para mensajes de texto.

        Args:
            update: Update de Telegram
            context: Contexto de la conversación (unused)
        """
        # Validaciones
        if not update.message or not update.message.text or not update.effective_chat or not update.effective_user:
            return

        # Extraer información del mensaje
        user_message = update.message.text
        chat_id = update.effective_chat.id
        user = update.effective_user

        # Generar session_id único para este chat
        session_id = self._generate_session_id(chat_id)

        # Usar username o ID como customer_email (opcional)
        customer_email = user.username if user.username else f"telegram_user_{user.id}"

        # Metadata adicional
        metadata = {
            "chat_id": chat_id,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        try:
            # Indicar que el bot está escribiendo
            await update.message.chat.send_action("typing")

            # Procesar mensaje vía ChatCore
            response = await self.chat_core.process_message(
                session_id=session_id,
                user_message=user_message,
                customer_email=customer_email,
                metadata=metadata
            )

            # Enviar respuesta
            await update.message.reply_text(response)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Lo siento, ocurrió un error al procesar tu mensaje.\n\n"
                f"Error: {str(e)}"
            )

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
