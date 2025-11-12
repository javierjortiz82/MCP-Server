#!/usr/bin/env python3
"""Main launcher para Telegram adapter.

Este script lanza el bot de Telegram que usa ChatCore como núcleo.

Configuration:
    Set TELEGRAM_BOT_TOKEN in environment or .env file

Usage:
    # Usando variable de entorno:
    export TELEGRAM_BOT_TOKEN="your_bot_token_here"
    python main_telegram.py

    # O usando .env:
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
    python main_telegram.py

Dependencies:
    pip install python-telegram-bot

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

import asyncio
import os
import sys
from pathlib import Path

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add integrations to path
sys.path.insert(0, str(Path(__file__).parent))

from integrations.telegram_adapter import TelegramAdapter


async def main():
    """Main entry point para Telegram adapter."""
    print("\n" + "=" * 70)
    print("🤖 Lab01-MCP Telegram Bot")
    print("=" * 70)
    print("Powered by ChatCore - Arquitectura modular multi-canal")
    print("=" * 70)

    # Verificar token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN not found")
        print("\nConfigura tu token de esta forma:")
        print("  1. Crear bot en @BotFather (Telegram)")
        print("  2. Copiar el token")
        print("  3. Ejecutar: export TELEGRAM_BOT_TOKEN='tu_token_aqui'")
        print("     O agregar TELEGRAM_BOT_TOKEN=tu_token_aqui en .env")
        sys.exit(1)

    print(f"✅ Token configurado: {token[:10]}...{token[-4:]}")

    # Crear y ejecutar adaptador
    adapter = TelegramAdapter(token=token)

    try:
        await adapter.initialize()
        await adapter.run()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
