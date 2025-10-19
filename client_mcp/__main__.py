#!/usr/bin/env python3
"""Lab01-MCP Multi-Agent System.

Main entry point for the Lab01-MCP system with multi-agent routing support.
This implementation provides:
- Feature flag for gradual rollout (ENABLE_AGENT_ROUTING)
- Multi-agent routing (sales, booking, general)
- Full compliance with MCP specifications

Usage:
    # Single-agent mode (SalesAgent only):
    ENABLE_AGENT_ROUTING=false python -m client_mcp

    # Multi-agent mode (Router + specialized agents):
    ENABLE_AGENT_ROUTING=true python -m client_mcp

Features:
    - AgentRouter: Intent classification (sales/booking/general)
    - Sales Agent: Product queries and recommendations
    - Booking Agent: Appointment management
    - General Agent: FAQ and company information
    - Official Anthropic MCP SDK
    - Gradual rollout capability
    - Advanced prompt engineering

Author: Lab01-MCP Team
Updated: 2025-10-11
Version: 2.0.0 (Multi-Agent)
"""

import asyncio
import sys
from pathlib import Path

# Explicit import to avoid sys.path conflicts across different modules
try:
    from importlib.util import spec_from_file_location, module_from_spec

    settings_path = Path(__file__).parent / "config" / "settings.py"
    spec = spec_from_file_location("client_mcp_settings_main", settings_path)
    if spec and spec.loader:
        _settings_module = module_from_spec(spec)
        spec.loader.exec_module(_settings_module)
        settings = _settings_module.settings
    else:
        raise ImportError("Failed to load settings module")
except (ImportError, AttributeError):
    # Fallback: try standard imports
    try:
        from .config.settings import settings
    except ImportError:
        # Fallback for direct execution: python __main__.py
        from config.settings import settings

try:
    from .core.agent_orchestrator import AgentOrchestrator
except ImportError:
    # Fallback for direct execution
    from core.agent_orchestrator import AgentOrchestrator


async def main():
    """Main entry point with multi-agent orchestrator."""
    # Create orchestrator (automatically checks ENABLE_AGENT_ROUTING flag)
    orchestrator = AgentOrchestrator()

    # Ask for customer email for persistent memory (optional)
    print("\n💾 Sistema de Memoria Persistente")
    print("=" * 70)
    print("Para habilitar memoria persistente entre sesiones, ingresa tu email.")
    print("Presiona Enter para continuar sin memoria persistente.")
    print("=" * 70)

    customer_email = input("📧 Tu email (opcional): ").strip()
    if not customer_email:
        customer_email = None
        print("ℹ️  Continuando sin memoria persistente")
    else:
        print(f"✅ Memoria habilitada para: {customer_email}")

    try:
        # Initialize orchestrator and agents (with optional memory)
        await orchestrator.initialize(customer_email=customer_email)

        # Run interactive chat
        await orchestrator.run_interactive()

    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")

    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

    finally:
        # Cleanup resources
        await orchestrator.cleanup()


if __name__ == "__main__":
    # Display startup banner
    mode = "MULTI-AGENT" if settings.ENABLE_AGENT_ROUTING else "SINGLE-AGENT (SalesAgent)"

    print("🚀 Lab01-MCP - Multi-Agent Sales & Booking System")
    print("=" * 70)
    print(f"Mode: {mode}")
    print("=" * 70)

    asyncio.run(main())
