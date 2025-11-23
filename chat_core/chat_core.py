"""ChatCore - Núcleo central de conversación multi-canal.

Este módulo implementa el núcleo central que:
- Recibe mensajes de cualquier canal (CLI, Telegram, Web, etc.)
- Mantiene contexto por sesión
- Orquesta AgentOrchestrator (multi-agent routing)
- Llama a Gemini para generar respuestas
- Invoca MCP tools cuando es necesario
- Retorna respuestas en texto plano

Arquitectura:
    Canal (CLI/Telegram/Web)
        │
        ▼
    ChatCore.process_message(session_id, message)
        │
        ├─► AgentOrchestrator
        ├─► Gemini API
        └─► MCP Connector
        │
        ▼
    Respuesta (str)

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Add client_mcp to path for imports
client_mcp_path = Path(__file__).parent.parent / "client_mcp"
if str(client_mcp_path) not in sys.path:
    sys.path.insert(0, str(client_mcp_path))

# Add agent to path for imports
agent_path = Path(__file__).parent.parent / "agent" / "src"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from chat_core.session_manager import SessionManager, Session  # noqa: E402
from client_mcp.core.agent_orchestrator import AgentOrchestrator  # noqa: E402
from client_mcp.config.settings import settings  # noqa: E402
from client_mcp.utils.logger import get_logger  # noqa: E402

logger = get_logger("ChatCore", settings.LOG_LEVEL)


class ChatCore:
    """Núcleo central de conversación para múltiples canales.

    Esta clase encapsula toda la lógica de conversación y permite
    que diferentes canales (CLI, Telegram, Web, etc.) la reutilicen
    sin duplicar código.

    Attributes:
        session_manager: Gestor de sesiones multi-canal
        orchestrators: Diccionario de orchestrators por session_id

    Example:
        >>> core = ChatCore()
        >>> await core.initialize()
        >>> response = await core.process_message(
        ...     session_id="telegram_123",
        ...     user_message="Busco una laptop gaming",
        ...     customer_email="user@example.com"
        ... )
        >>> print(response)
        'Claro, te muestro nuestras laptops gaming...'
    """

    def __init__(self):
        """Inicializa ChatCore con gestor de sesiones vacío."""
        self.session_manager = SessionManager()
        # Cada sesión tiene su propio orchestrator para mantener contexto
        self.orchestrators: dict[str, AgentOrchestrator] = {}
        logger.info("ChatCore initialized")

    async def initialize(self) -> None:
        """Inicializa recursos globales (si es necesario).

        Este método puede ser usado para inicializar conexiones,
        pools, etc. Por ahora es placeholder.
        """
        logger.info("ChatCore global initialization complete")

    async def process_message(
        self,
        session_id: str,
        user_message: str,
        customer_email: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """Procesa un mensaje de usuario y retorna respuesta.

        Este es el punto de entrada principal para todos los canales.
        Maneja:
        1. Gestión de sesión
        2. Inicialización de orchestrator (si es primera vez)
        3. Procesamiento del mensaje vía AgentOrchestrator
        4. Retorno de respuesta en texto plano

        Args:
            session_id: Identificador único de sesión (ej: "telegram_123")
            user_message: Mensaje del usuario
            customer_email: Email del usuario (opcional, para memoria persistente)
            metadata: Metadatos adicionales del canal (opcional)

        Returns:
            Respuesta en texto plano para enviar al usuario

        Raises:
            Exception: Si hay error en procesamiento (propagado para manejo en adapter)

        Example:
            >>> core = ChatCore()
            >>> await core.initialize()
            >>> response = await core.process_message(
            ...     session_id="cli_session_1",
            ...     user_message="Hola",
            ...     customer_email="test@example.com"
            ... )
        """
        try:
            # 1. Obtener o crear sesión
            session = self.session_manager.get_or_create_session(
                session_id=session_id,
                customer_email=customer_email,
                metadata=metadata or {}
            )
            logger.info(f"Processing message for session: {session_id}")

            # 2. Get or create database session UUID for memory management
            # CRITICAL: The memory_manager needs the database UUID, not the transient session_id
            if hasattr(self, 'memory_manager') and self.memory_manager:
                db_session_id = self.memory_manager.get_or_create_session(
                    customer_email=customer_email,
                    session_id=session_id  # Pass transient session_id to track it
                )
                logger.info(f"Database session UUID: {db_session_id} (transient: {session_id})")
            else:
                db_session_id = None
                logger.debug("Memory manager not available, skipping database session creation")

            # 3. Obtener o crear orchestrator para esta sesión
            orchestrator = await self._get_or_create_orchestrator(session, db_session_id)

            # 4. Procesar mensaje usando el orchestrator
            response = await self._process_with_orchestrator(
                orchestrator=orchestrator,
                user_message=user_message,
                session=session
            )

            logger.info(f"Response generated for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {e}")
            return f"Lo siento, ocurrió un error al procesar tu mensaje: {str(e)}"

    async def _get_or_create_orchestrator(self, session: Session, db_session_id: Optional[str] = None) -> AgentOrchestrator:
        """Obtiene o crea un orchestrator para una sesión.

        Cada sesión tiene su propio orchestrator para mantener
        el contexto de conversación independiente.

        Args:
            session: Objeto Session
            db_session_id: Optional database session UUID for memory management

        Returns:
            AgentOrchestrator para esta sesión

        Note:
            Los orchestrators se crean lazy (solo cuando se necesitan)
            Si db_session_id está disponible, se pasa al orchestrator para memoria persistente.
            CRITICAL: Cache key uses db_session_id (not transient session_id) to detect
            when a session is archived and needs to be recreated.
        """
        # CRITICAL: Use db_session_id as cache key, NOT transient session_id
        # This ensures that if DB session is archived, a new orchestrator is created
        cache_key = db_session_id or session.session_id

        if cache_key not in self.orchestrators:
            logger.info(f"Creating new orchestrator for session: {cache_key}")
            orchestrator = AgentOrchestrator()
            await orchestrator.initialize(
                customer_email=session.customer_email,
                db_session_id=db_session_id
            )
            self.orchestrators[cache_key] = orchestrator
        else:
            logger.debug(f"Reusing existing orchestrator for session: {cache_key}")

        return self.orchestrators[cache_key]

    async def _process_with_orchestrator(
        self,
        orchestrator: AgentOrchestrator,
        user_message: str,
        session: Session
    ) -> str:
        """Procesa mensaje usando el orchestrator.

        Args:
            orchestrator: AgentOrchestrator de la sesión
            user_message: Mensaje del usuario
            session: Objeto Session

        Returns:
            Respuesta en texto plano

        Note:
            Este método puede ser extendido para agregar:
            - Logging de métricas
            - Rate limiting
            - Filtrado de contenido
            - etc.
        """
        # Actualizar actividad de sesión
        session.update_activity()

        # Procesar mensaje vía orchestrator
        # El orchestrator maneja:
        # - Clasificación de intent (AgentRouter)
        # - Selección de agente (Sales/Booking/General)
        # - Llamadas a Gemini
        # - Invocación de MCP tools
        # - Gestión de memoria persistente

        response = await orchestrator.process_query(user_message)

        return response

    async def cleanup_session(self, session_id: str) -> None:
        """Limpia recursos de una sesión específica.

        Args:
            session_id: Identificador de sesión a limpiar

        Note:
            Útil cuando un usuario finaliza conversación explícitamente
            o cuando hay timeout de sesión.
        """
        logger.info(f"Cleaning up session: {session_id}")

        # Cleanup orchestrator
        if session_id in self.orchestrators:
            orchestrator = self.orchestrators[session_id]
            await orchestrator.cleanup()
            del self.orchestrators[session_id]

        # Eliminar sesión
        self.session_manager.delete_session(session_id)

        logger.info(f"Session cleanup complete: {session_id}")

    async def cleanup_all(self) -> None:
        """Limpia todos los recursos (para shutdown).

        Note:
            Debe llamarse al finalizar la aplicación para liberar recursos.
        """
        logger.info("Cleaning up all ChatCore resources")

        # Cleanup all orchestrators
        for session_id, orchestrator in list(self.orchestrators.items()):
            await orchestrator.cleanup()

        self.orchestrators.clear()
        self.session_manager.clear_all()

        logger.info("ChatCore cleanup complete")

    def get_active_sessions_count(self) -> int:
        """Retorna número de sesiones activas.

        Returns:
            Número de sesiones activas

        Example:
            >>> core = ChatCore()
            >>> count = core.get_active_sessions_count()
            >>> print(count)
            0
        """
        return self.session_manager.get_active_sessions_count()
