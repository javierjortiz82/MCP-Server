"""Integrations - Adaptadores de canales para ChatCore.

Este módulo contiene adaptadores para diferentes canales de comunicación
que utilizan ChatCore como núcleo común:

- CLI Adapter: Interfaz de línea de comandos (refactorizado)
- Telegram Adapter: Bot de Telegram
- Futuros: Web UI, Discord, Slack, WhatsApp, etc.

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

__all__ = ["CLIAdapter", "TelegramAdapter"]
