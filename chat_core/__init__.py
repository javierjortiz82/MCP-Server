"""ChatCore - Núcleo central de conversación.

Este módulo proporciona el núcleo central de conversación que:
- Encapsula toda la lógica de negocio de chat
- Gestiona sesiones por canal
- Orquesta llamadas a Gemini y MCP
- Provee una API simple para adaptadores de canales

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from chat_core.chat_core import ChatCore
from chat_core.session_manager import SessionManager

__all__ = ["ChatCore", "SessionManager"]
