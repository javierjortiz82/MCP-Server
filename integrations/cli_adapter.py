"""CLI Adapter - Adaptador de línea de comandos para ChatCore.

Este adaptador proporciona una interfaz CLI que usa ChatCore
como núcleo de conversación. Reemplaza el código monolítico
anterior manteniendo la misma funcionalidad.

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Add chat_core to path
chat_core_path = Path(__file__).parent.parent
if str(chat_core_path) not in sys.path:
    sys.path.insert(0, str(chat_core_path))

from chat_core import ChatCore  # noqa: E402


class CLIAdapter:
    """Adaptador de línea de comandos para ChatCore.

    Este adaptador:
    - Lee input de usuario desde stdin
    - Genera session_id único por ejecución
    - Procesa mensajes vía ChatCore
    - Muestra respuestas en stdout
    - Maneja comandos especiales (/quit, /help, /clear, /stats)

    Attributes:
        chat_core: Instancia de ChatCore
        session_id: Identificador único de sesión
        customer_email: Email del usuario (opcional)

    Example:
        >>> adapter = CLIAdapter()
        >>> await adapter.initialize(customer_email="user@example.com")
        >>> await adapter.run()
    """

    def __init__(self):
        """Inicializa el adaptador CLI."""
        self.chat_core = ChatCore()
        self.session_id = f"cli_{uuid.uuid4().hex[:8]}"
        self.customer_email: str | None = None

    async def initialize(self, customer_email: str | None = None) -> None:
        """Inicializa el adaptador y ChatCore.

        Args:
            customer_email: Email del usuario para memoria persistente (opcional)
        """
        self.customer_email = customer_email
        await self.chat_core.initialize()

    async def run(self) -> None:
        """Ejecuta el loop interactivo del CLI.

        Maneja:
        - Input de usuario
        - Comandos especiales (/quit, /help, /clear)
        - Procesamiento de mensajes vía ChatCore
        - Display de respuestas
        """
        self._print_welcome()

        while True:
            try:
                # Obtener input del usuario
                user_input = input("\n👤 You: ").strip()

                if not user_input:
                    continue

                # Manejar comandos especiales
                if user_input.startswith("/"):
                    if user_input == "/quit":
                        print("\n👋 ¡Hasta luego!")
                        break

                    elif user_input == "/help":
                        self._print_help()
                        continue

                    elif user_input == "/clear":
                        # Limpiar sesión actual y crear nueva
                        await self.chat_core.cleanup_session(self.session_id)
                        self.session_id = f"cli_{uuid.uuid4().hex[:8]}"
                        print("✅ Conversación reiniciada")
                        continue

                    elif user_input == "/stats":
                        count = self.chat_core.get_active_sessions_count()
                        print(f"\n📊 Estadísticas:")
                        print(f"  Sesiones activas: {count}")
                        continue

                    else:
                        print(f"❌ Comando desconocido: {user_input}")
                        print("   Usa /help para ver comandos disponibles")
                        continue

                # Procesar mensaje
                print("🤔 Procesando...")

                response = await self.chat_core.process_message(
                    session_id=self.session_id,
                    user_message=user_input,
                    customer_email=self.customer_email
                )

                print(f"\n🤖 Bot: {response}")

            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break

            except Exception as e:
                print(f"\n❌ Error: {e}")

    async def cleanup(self) -> None:
        """Limpia recursos al finalizar."""
        await self.chat_core.cleanup_all()

    def _print_welcome(self) -> None:
        """Muestra banner de bienvenida."""
        print("\n" + "=" * 70)
        print("🤖 Lab01-MCP Multi-Agent System (CLI)")
        print("=" * 70)
        print("Powered by ChatCore - Arquitectura modular multi-canal")
        print("\nComandos:")
        print("  /help    - Mostrar ayuda")
        print("  /clear   - Reiniciar conversación")
        print("  /stats   - Mostrar estadísticas")
        print("  /quit    - Salir")
        print("=" * 70)

    def _print_help(self) -> None:
        """Muestra mensaje de ayuda."""
        print("\n📖 Comandos disponibles:")
        print("  /help    - Mostrar esta ayuda")
        print("  /clear   - Reiniciar conversación")
        print("  /stats   - Mostrar estadísticas")
        print("  /quit    - Salir del programa")
