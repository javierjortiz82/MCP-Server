#!/usr/bin/env python3
"""Main launcher para CLI adapter.

Este script lanza el adaptador CLI que usa ChatCore como núcleo.

Usage:
    python main_cli.py

    # Con memoria persistente:
    python main_cli.py

    # El programa pedirá tu email para habilitar memoria

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Add integrations to path
sys.path.insert(0, str(Path(__file__).parent))

from integrations.cli_adapter import CLIAdapter


async def main():
    """Main entry point para CLI adapter."""
    # Banner
    print("\n" + "=" * 70)
    print("💾 Sistema de Memoria Persistente")
    print("=" * 70)
    print("Para habilitar memoria persistente entre sesiones, ingresa tu email.")
    print("Presiona Enter para continuar sin memoria persistente.")
    print("=" * 70)

    # Pedir email (opcional)
    customer_email = input("\n📧 Tu email (opcional): ").strip()
    if not customer_email:
        customer_email = None
        print("ℹ️  Continuando sin memoria persistente")
    else:
        print(f"✅ Memoria habilitada para: {customer_email}")

    # Crear y ejecutar adaptador
    adapter = CLIAdapter()

    try:
        await adapter.initialize(customer_email=customer_email)
        await adapter.run()
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
    finally:
        await adapter.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
