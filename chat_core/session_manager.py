"""Session Manager - Gestión de sesiones multi-canal.

Este módulo maneja el estado de sesiones para diferentes canales
(CLI, Telegram, Web, etc.) sin duplicar lógica.

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Session:
    """Representa una sesión de conversación.

    Attributes:
        session_id: Identificador único de sesión (ej: "telegram_123", "cli_1")
        customer_email: Email del usuario (opcional, para memoria persistente)
        metadata: Metadatos adicionales del canal (ej: chat_id, username)
        created_at: Timestamp de creación
        last_activity: Timestamp de última actividad
        message_count: Contador de mensajes procesados en esta sesión
        previous_sentiment: Sentimiento del mensaje anterior (para análisis contextual)
    """

    session_id: str
    customer_email: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    previous_sentiment: str = "neutral"

    def update_activity(self) -> None:
        """Actualiza el timestamp de última actividad."""
        self.last_activity = datetime.now()

    def increment_message_count(self) -> int:
        """Incrementa el contador de mensajes y retorna el nuevo valor.

        Returns:
            Nuevo contador de mensajes

        Example:
            >>> session = Session(session_id="test")
            >>> session.increment_message_count()
            1
            >>> session.increment_message_count()
            2
        """
        self.message_count += 1
        return self.message_count

    def update_sentiment(self, sentiment: str) -> None:
        """Actualiza el sentimiento previo para análisis contextual.

        Args:
            sentiment: Nuevo sentimiento ("positive", "negative", "neutral")

        Example:
            >>> session = Session(session_id="test")
            >>> session.update_sentiment("positive")
            >>> session.previous_sentiment
            'positive'
        """
        self.previous_sentiment = sentiment

    def get_user_context(self) -> dict[str, Any]:
        """Retorna contexto del usuario para análisis de sentimientos.

        Returns:
            Diccionario con previous_sentiment y conversation_count

        Example:
            >>> session = Session(session_id="test")
            >>> session.message_count = 5
            >>> session.previous_sentiment = "neutral"
            >>> context = session.get_user_context()
            >>> context["conversation_count"]
            5
        """
        return {
            "previous_sentiment": self.previous_sentiment,
            "conversation_count": self.message_count
        }


class SessionManager:
    """Gestor de sesiones para múltiples canales.

    Mantiene un registro de sesiones activas y permite crear/recuperar
    sesiones por session_id.

    Attributes:
        sessions: Diccionario de sesiones activas por session_id

    Example:
        >>> manager = SessionManager()
        >>> session = manager.get_or_create_session(
        ...     session_id="telegram_123",
        ...     customer_email="user@example.com",
        ...     metadata={"chat_id": 123, "username": "john"}
        ... )
        >>> session.session_id
        'telegram_123'
    """

    def __init__(self):
        """Inicializa el gestor con diccionario vacío de sesiones."""
        self.sessions: dict[str, Session] = {}

    def get_or_create_session(
        self,
        session_id: str,
        customer_email: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Session:
        """Obtiene una sesión existente o crea una nueva.

        Args:
            session_id: Identificador único de sesión
            customer_email: Email del usuario (opcional)
            metadata: Metadatos adicionales (opcional)

        Returns:
            Objeto Session existente o recién creado

        Example:
            >>> manager = SessionManager()
            >>> session = manager.get_or_create_session("cli_1")
            >>> session.session_id
            'cli_1'
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.update_activity()
            return session

        session = Session(
            session_id=session_id,
            customer_email=customer_email,
            metadata=metadata or {}
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Obtiene una sesión existente.

        Args:
            session_id: Identificador de sesión

        Returns:
            Objeto Session si existe, None en caso contrario

        Example:
            >>> manager = SessionManager()
            >>> session = manager.get_session("nonexistent")
            >>> session is None
            True
        """
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Elimina una sesión.

        Args:
            session_id: Identificador de sesión a eliminar

        Returns:
            True si se eliminó, False si no existía

        Example:
            >>> manager = SessionManager()
            >>> manager.get_or_create_session("test")
            >>> manager.delete_session("test")
            True
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_active_sessions_count(self) -> int:
        """Retorna el número de sesiones activas.

        Returns:
            Número de sesiones activas

        Example:
            >>> manager = SessionManager()
            >>> manager.get_or_create_session("s1")
            >>> manager.get_active_sessions_count()
            1
        """
        return len(self.sessions)

    def clear_all(self) -> None:
        """Elimina todas las sesiones (útil para testing).

        Example:
            >>> manager = SessionManager()
            >>> manager.get_or_create_session("s1")
            >>> manager.clear_all()
            >>> manager.get_active_sessions_count()
            0
        """
        self.sessions.clear()
