#!/usr/bin/env python3
"""Odiseo Bot - Interactive CLI Tool.

Standalone CLI wrapper for OdiseoBotV2 with interactive mode,
help, and metrics display.

This script replaces the CLI functionality from Legacy OdiseoBot,
allowing users to interact with the bot via command line.

Usage:
    python3 scripts/odiseo_cli.py

Commands:
    /help    - Show help information
    /debug   - Toggle debug mode
    /metrics - Show execution metrics
    /clear   - Clear conversation history
    /exit    - Exit the program

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Add agent src to path for imports
agent_src = Path(__file__).parent.parent / "agent" / "src"
if str(agent_src) not in sys.path:
    sys.path.insert(0, str(agent_src))

try:
    from multi_agent import OdiseoBotV2
except ImportError as e:
    print(f"❌ Error: Cannot import OdiseoBotV2: {e}")
    print("Make sure you're running from the project root and agent/src is accessible.")
    sys.exit(1)


class OdiseoCLI:
    """Interactive CLI for OdiseoBotV2.

    Provides a command-line interface with:
    - Interactive chat loop
    - Debug mode toggle
    - Help information
    - Execution metrics
    - Conversation history management

    Example:
        >>> cli = OdiseoCLI()
        >>> await cli.initialize()
        >>> await cli.run_interactive()
    """

    def __init__(self, user_id: str = "cli_user", debug_mode: bool = False):
        """Initialize CLI wrapper.

        Args:
            user_id: User ID for session tracking (default: "cli_user")
            debug_mode: Enable debug mode from start (default: False)
        """
        self.bot: OdiseoBotV2 | None = None
        self.debug_mode = debug_mode
        self.user_id = user_id
        self.conversation_count = 0

    async def initialize(self) -> None:
        """Initialize OdiseoBotV2.

        Raises:
            RuntimeError: If bot initialization fails
        """
        try:
            print("🔄 Initializing Odiseo Bot...")
            self.bot = OdiseoBotV2(user_id=self.user_id, debug_mode=self.debug_mode)
            await self.bot.initialize()
            print("✅ Bot initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize bot: {e}")
            raise RuntimeError(f"Bot initialization failed: {e}") from e

    async def run_interactive(self) -> None:
        """Run interactive chat loop.

        Main loop for CLI interaction. Handles user input and commands.
        """
        self._print_banner()
        self._print_help_quick()

        while True:
            try:
                # Get user input
                user_input = input("\n👤 Tú: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if not await self._handle_command(user_input.lower()):
                        break  # Exit requested
                    continue

                # Send message to bot
                await self._process_message(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break

            except Exception as e:
                print(f"\n❌ Error: {e}")
                if self.debug_mode:
                    import traceback

                    traceback.print_exc()

    async def _handle_command(self, command: str) -> bool:
        """Handle CLI commands.

        Args:
            command: Command string (e.g., "/help", "/exit")

        Returns:
            True to continue loop, False to exit
        """
        if command == "/exit":
            print("👋 ¡Hasta luego!")
            return False

        elif command == "/debug":
            self.debug_mode = not self.debug_mode
            if self.bot:
                self.bot.debug_mode = self.debug_mode
            status = "activado" if self.debug_mode else "desactivado"
            print(f"🐛 Modo debug {status}")

        elif command == "/help":
            self.show_help()

        elif command == "/metrics":
            self.show_metrics()

        elif command == "/clear":
            await self._clear_history()

        else:
            print(f"❌ Comando desconocido: {command}")
            print("   Usa /help para ver comandos disponibles")

        return True

    async def _process_message(self, user_input: str) -> None:
        """Process user message and display bot response.

        Args:
            user_input: User's message
        """
        if not self.bot:
            print("❌ Bot no inicializado")
            return

        try:
            print("🤔 Procesando...")
            response = await self.bot.send_message(user_input)
            self.conversation_count += 1
            print(f"\n🤖 Bot: {response}")

        except Exception as e:
            print(f"\n❌ Error procesando mensaje: {e}")
            if self.debug_mode:
                import traceback

                traceback.print_exc()

    async def _clear_history(self) -> None:
        """Clear conversation history."""
        if not self.bot:
            print("❌ Bot no inicializado")
            return

        self.bot.conversation_history = []
        self.conversation_count = 0
        print("✅ Historial de conversación borrado")

    def _print_banner(self) -> None:
        """Print welcome banner."""
        print("\n" + "═" * 70)
        print("🌟 ODISEO BOT - Tu Vendedor Inteligente")
        print("═" * 70)
        print("💡 Soy Odiseo, experto en ayudarte a encontrar productos perfectos")
        print("🚀 Powered by OdiseoBotV2 (BaseAgent)")
        print("─" * 70)

    def _print_help_quick(self) -> None:
        """Print quick help."""
        print("\n💬 Comandos: /help, /debug, /metrics, /clear, /exit")
        print("👋 ¡Hola! ¿Qué producto buscas hoy?\n")

    def show_help(self) -> None:
        """Show detailed help information."""
        print("\n" + "═" * 70)
        print("📚 AYUDA - ODISEO BOT")
        print("═" * 70)
        print("\n🎯 ¿Qué puedo hacer por ti?")
        print("  • Buscar productos por nombre, marca o categoría")
        print("  • Encontrar productos específicos por código SKU")
        print("  • Recomendar productos según tus necesidades")
        print("  • Búsqueda inteligente con tolerancia a errores tipográficos")
        print("  • Paginación de resultados (di 'más' para ver más)")

        print("\n💬 Comandos especiales:")
        print("  /help    - Mostrar esta ayuda")
        print("  /debug   - Alternar modo debug (ver detalles técnicos)")
        print("  /metrics - Ver métricas de ejecución de herramientas")
        print("  /clear   - Borrar historial de conversación")
        print("  /exit    - Salir del chat")

        if self.bot:
            tool_count = len(self.bot.mcp_tools) if self.bot.mcp_tools else 0
            print(f"\n🔧 Herramientas MCP activas: {tool_count}")
            if self.bot.mcp_tools:
                print("   Herramientas disponibles:")
                for i, tool in enumerate(self.bot.mcp_tools[:5], 1):
                    print(f"   {i}. {tool.name}")
                if len(self.bot.mcp_tools) > 5:
                    print(f"   ... y {len(self.bot.mcp_tools) - 5} más")

        print("\n💡 Ejemplos de consultas:")
        print('  • "Busco una laptop gaming"')
        print('  • "Quiero el producto con SKU LAPTOP-001"')
        print('  • "Necesito algo para diseño gráfico profesional"')
        print('  • "Tienes laptops ultraligeras?" (tolera errores)')
        print('  • "Muéstrame más opciones" (después de una búsqueda)')

        print("\n📊 Estadísticas de esta sesión:")
        print(f"  • Mensajes enviados: {self.conversation_count}")
        print(f"  • Modo debug: {'Activado' if self.debug_mode else 'Desactivado'}")
        if self.bot and hasattr(self.bot, "session_id"):
            print(f"  • Session ID: {str(self.bot.session_id)[:8]}...")

        print("─" * 70 + "\n")

    def show_metrics(self) -> None:
        """Show execution metrics."""
        if not self.bot:
            print("\n📊 Métricas no disponibles (Bot no inicializado)")
            return

        if not self.bot.tool_executor:
            print("\n📊 Métricas no disponibles (Tool Executor no inicializado)")
            print("   Las métricas requieren ENABLE_METRICS=true en configuración")
            return

        print("\n" + "═" * 70)
        print("📊 MÉTRICAS DE EJECUCIÓN - ODISEO BOT")
        print("═" * 70)

        try:
            stats = self.bot.tool_executor.get_stats()

            # Summary
            if "summary" in stats:
                summary = stats["summary"]
                print("\n🎯 Resumen General:")
                print(f"  Total de llamadas: {summary.get('total_tool_calls', 0)}")
                print(f"  Exitosas: {summary.get('successful_calls', 0)}")
                print(f"  Fallidas: {summary.get('failed_calls', 0)}")
                print(f"  Tasa de éxito: {summary.get('success_rate_percent', 0):.2f}%")
                print(f"  Herramientas únicas: {summary.get('unique_tools_used', 0)}")

            # Most used tools
            most_used = self.bot.tool_executor.get_most_used_tools(5)
            if most_used:
                print("\n🔝 Herramientas Más Usadas:")
                for i, (tool_name, count) in enumerate(most_used, 1):
                    print(f"  {i}. {tool_name}: {count} llamadas")

            # Slowest tools
            slowest = self.bot.tool_executor.get_slowest_tools(5)
            if slowest:
                print("\n⏱️  Herramientas Más Lentas:")
                for i, (tool_name, avg_time) in enumerate(slowest, 1):
                    print(f"  {i}. {tool_name}: {avg_time:.2f}ms promedio")

            # Error rates
            error_rates = self.bot.tool_executor.get_error_rate_by_tool()
            if error_rates:
                has_errors = any(rate > 0 for rate in error_rates.values())
                if has_errors:
                    print("\n❌ Tasas de Error:")
                    for tool_name, rate in error_rates.items():
                        if rate > 0:
                            print(f"  {tool_name}: {rate:.2f}%")

            # Cache stats
            cache_stats = self.bot.tool_executor.get_cache_stats()
            if cache_stats:
                print("\n💾 Estado del Cache:")
                print(
                    f"  Herramientas en cache: {cache_stats.get('total_tools_cached', 0)}"
                )
                print(
                    f"  Cache válido: {'Sí' if cache_stats.get('has_valid_snapshot') else 'No'}"
                )

            # Context cache info (if available)
            if self.bot.cached_content:
                print("\n🔄 Context Cache:")
                print("  Estado: Activo")
                if hasattr(self.bot.cached_content, "usage_metadata"):
                    tokens = self.bot.cached_content.usage_metadata.total_token_count
                    print(f"  Tokens cacheados: {tokens}")

        except Exception as e:
            print(f"\n❌ Error obteniendo métricas: {e}")
            if self.debug_mode:
                import traceback

                traceback.print_exc()

        print("─" * 70 + "\n")

    async def cleanup(self) -> None:
        """Cleanup bot resources."""
        if self.bot:
            try:
                await self.bot.cleanup()
                print("\n✅ Recursos liberados correctamente")
            except Exception as e:
                print(f"\n⚠️ Error durante cleanup: {e}")


async def main():
    """Main entry point for CLI tool.

    Initializes CLI, runs interactive loop, and handles cleanup.
    """
    cli = OdiseoCLI()

    try:
        await cli.initialize()
        await cli.run_interactive()
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await cli.cleanup()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
