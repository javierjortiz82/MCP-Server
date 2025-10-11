#!/usr/bin/env python3
"""
Odiseo Bot - Intelligent Sales Agent

Main entry point for Odiseo Bot using the official Anthropic MCP SDK.
This implementation is 100% compliant with MCP specifications.

Usage:
    python main.py

Features:
    - Odiseo Bot: Intelligent sales agent with emotional intelligence
    - Official Anthropic MCP SDK
    - Full compliance with MCP specifications
    - Autodiscovery of MCP tools
    - Advanced prompt engineering (600+ lines)
    - Clean and maintainable code
"""

import asyncio
import sys

# Support both direct execution and module execution
try:
    from .core.odiseo_bot import OdiseoBot
except ImportError:
    # Fallback for direct execution: python __main__.py
    from core.odiseo_bot import OdiseoBot


async def main():
    """Main entry point for Odiseo Bot with official MCP SDK."""
    bot = OdiseoBot()

    try:
        # Initialize bot
        await bot.initialize()

        # Run interactive chat
        await bot.run_interactive()

    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")

    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

    finally:
        # Cleanup resources
        await bot.cleanup()


if __name__ == "__main__":
    print("🚀 Odiseo Bot - Intelligent Sales Agent")
    print("=" * 50)
    asyncio.run(main())
