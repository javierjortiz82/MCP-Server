# Odiseo Bot - CLI Tool Guide

**Version**: 1.0.0
**Created**: 2025-10-12
**Tool**: `scripts/odiseo_cli.py`
**Purpose**: Interactive command-line interface for OdiseoBotV2

---

## Overview

The Odiseo CLI Tool provides an interactive command-line interface for chatting with OdiseoBotV2. It replaces the CLI functionality from Legacy OdiseoBot with a standalone, modern implementation.

### Features

- ✅ **Interactive chat loop** - Chat with the bot via terminal
- ✅ **Debug mode** - Toggle detailed logging on/off
- ✅ **Metrics display** - View execution statistics
- ✅ **Help system** - Built-in help and examples
- ✅ **History management** - Clear conversation history
- ✅ **Powered by V2** - Uses OdiseoBotV2 (BaseAgent)

---

## Quick Start

### Basic Usage

```bash
# Run from project root
cd /home/javort/Lab01-MCP
python3 scripts/odiseo_cli.py
```

### First Time Setup

```bash
# Ensure dependencies are installed
pip install google-genai>=1.41.0

# Make script executable (optional)
chmod +x scripts/odiseo_cli.py

# Run
./scripts/odiseo_cli.py
```

---

## Commands

The CLI tool supports the following commands:

| Command | Description | Example |
|---------|-------------|---------|
| `/help` | Show detailed help information | Just type: `/help` |
| `/debug` | Toggle debug mode (show/hide technical details) | Just type: `/debug` |
| `/metrics` | Display execution metrics and statistics | Just type: `/metrics` |
| `/clear` | Clear conversation history | Just type: `/clear` |
| `/exit` | Exit the CLI tool | Just type: `/exit` |

---

## Usage Examples

### Example 1: Basic Product Search

```
$ python3 scripts/odiseo_cli.py

══════════════════════════════════════════════════════════════════════
🌟 ODISEO BOT - Tu Vendedor Inteligente
══════════════════════════════════════════════════════════════════════
💡 Soy Odiseo, experto en ayudarte a encontrar productos perfectos
🚀 Powered by OdiseoBotV2 (BaseAgent)
──────────────────────────────────────────────────────────────────────

💬 Comandos: /help, /debug, /metrics, /clear, /exit
👋 ¡Hola! ¿Qué producto buscas hoy?

👤 Tú: Busco una laptop gaming

🤔 Procesando...

🤖 Bot: 🔍 Encontré varias laptops gaming excelentes. Aquí están las primeras opciones:

1. 💻 **Laptop Gaming HP OMEN 16**
   📝 Intel Core i7-13700HX, NVIDIA RTX 4070 8GB...
   🏷️ SKU: COMP-0060
   💵 Precio: $1,899.99

2. 💻 **Laptop Gaming ASUS ROG Strix**
   ...

👤 Tú: /exit

👋 ¡Hasta luego!

✅ Recursos liberados correctamente
```

---

### Example 2: Using Debug Mode

```
👤 Tú: /debug

🐛 Modo debug activado

👤 Tú: Busco laptops

🤔 Procesando...
[DEBUG] Executing tool: fuzzy_search_smart
[DEBUG] Parameters: {"query": "laptops", "limit": 20}
[DEBUG] Tool execution time: 15.2ms
[DEBUG] Results: 19 products found

🤖 Bot: [response...]
```

---

### Example 3: Viewing Metrics

```
👤 Tú: /metrics

══════════════════════════════════════════════════════════════════════
📊 MÉTRICAS DE EJECUCIÓN - ODISEO BOT
══════════════════════════════════════════════════════════════════════

🎯 Resumen General:
  Total de llamadas: 3
  Exitosas: 3
  Fallidas: 0
  Tasa de éxito: 100.00%
  Herramientas únicas: 2

🔝 Herramientas Más Usadas:
  1. fuzzy_search_smart: 2 llamadas
  2. search_products: 1 llamadas

⏱️  Herramientas Más Lentas:
  1. search_products: 630.25ms promedio
  2. fuzzy_search_smart: 15.60ms promedio

💾 Estado del Cache:
  Herramientas en cache: 5
  Cache válido: Sí

──────────────────────────────────────────────────────────────────────
```

---

## Help System

Type `/help` to see detailed information:

```
══════════════════════════════════════════════════════════════════════
📚 AYUDA - ODISEO BOT
══════════════════════════════════════════════════════════════════════

🎯 ¿Qué puedo hacer por ti?
  • Buscar productos por nombre, marca o categoría
  • Encontrar productos específicos por código SKU
  • Recomendar productos según tus necesidades
  • Búsqueda inteligente con tolerancia a errores tipográficos
  • Paginación de resultados (di 'más' para ver más)

💬 Comandos especiales:
  /help    - Mostrar esta ayuda
  /debug   - Alternar modo debug (ver detalles técnicos)
  /metrics - Ver métricas de ejecución de herramientas
  /clear   - Borrar historial de conversación
  /exit    - Salir del chat

🔧 Herramientas MCP activas: 5
   Herramientas disponibles:
   1. search_products
   2. fuzzy_search_smart
   3. fetch_by_sku
   4. fetch_by_id
   5. ingest_products

💡 Ejemplos de consultas:
  • "Busco una laptop gaming"
  • "Quiero el producto con SKU LAPTOP-001"
  • "Necesito algo para diseño gráfico profesional"
  • "Tienes laptops ultraligeras?" (tolera errores)
  • "Muéstrame más opciones" (después de una búsqueda)

📊 Estadísticas de esta sesión:
  • Mensajes enviados: 3
  • Modo debug: Desactivado
  • Session ID: a1b2c3d4...

──────────────────────────────────────────────────────────────────────
```

---

## Configuration

The CLI tool uses OdiseoBotV2 configuration from:

```
client_mcp/config/settings.py
```

### Environment Variables

Configure behavior via `.env` file:

```bash
# Model selection
MODEL=gemini-2.5-flash

# MCP server
MCP_HOST=localhost
MCP_PORT=8000

# Features
ENABLE_CONTEXT_CACHING=true
ENABLE_THINKING=true
ENABLE_METRICS=true
ENABLE_VALIDATION=true

# Performance
TEMPERATURE=0.7
TOP_K=40
TOP_P=0.95
MAX_OUTPUT_TOKENS=8192

# Pagination
PAGINATION_PAGE_SIZE=4
PAGINATION_TTL_HOURS=24
```

---

## Troubleshooting

### Issue 1: Import Error

**Error**:
```
❌ Error: Cannot import OdiseoBotV2
```

**Solution**:
```bash
# Ensure agent/src is in Python path
export PYTHONPATH=/home/javort/Lab01-MCP/agent/src:$PYTHONPATH
python3 scripts/odiseo_cli.py
```

---

### Issue 2: MCP Server Unreachable

**Error**:
```
⚠️ MCP server unreachable at http://localhost:8000/mcp
```

**Solution**:
```bash
# Start MCP server first
cd mcp_server
python3 server.py

# Then run CLI in another terminal
python3 scripts/odiseo_cli.py
```

---

### Issue 3: No Metrics Available

**Error**:
```
📊 Métricas no disponibles (Tool Executor no inicializado)
```

**Solution**:
```bash
# Enable metrics in .env
echo "ENABLE_METRICS=true" >> .env

# Restart CLI
python3 scripts/odiseo_cli.py
```

---

## Advanced Usage

### Custom User ID

```python
# Edit scripts/odiseo_cli.py, line ~343
# Or run with custom user:
python3 -c "
import asyncio
from scripts.odiseo_cli import OdiseoCLI

async def main():
    cli = OdiseoCLI(user_id='custom_user_123', debug_mode=True)
    await cli.initialize()
    await cli.run_interactive()

asyncio.run(main())
"
```

---

### Programmatic Usage

```python
import asyncio
from scripts.odiseo_cli import OdiseoCLI

async def example():
    # Initialize CLI
    cli = OdiseoCLI(user_id="api_user", debug_mode=False)
    await cli.initialize()

    # Send single message (no interactive loop)
    if cli.bot:
        response = await cli.bot.send_message("Busco laptops")
        print(response)

    # Cleanup
    await cli.cleanup()

asyncio.run(example())
```

---

## Comparison: Legacy vs CLI Tool

| Feature | Legacy OdiseoBot | CLI Tool |
|---------|------------------|----------|
| **Implementation** | Built into `odiseo_bot.py` | Standalone `scripts/odiseo_cli.py` |
| **Bot Version** | Legacy or V2 (mixed) | Always OdiseoBotV2 |
| **Lines of Code** | ~200 lines (embedded) | ~350 lines (standalone) |
| **Help System** | Basic | Comprehensive |
| **Metrics** | Basic | Detailed |
| **Maintainability** | Coupled with bot | Decoupled |
| **Testing** | Hard to test | Easy to test |
| **Extensibility** | Limited | High |

---

## Testing the CLI Tool

### Automated Test

```bash
# Run automated test
python3 /tmp/test_cli.py

# Expected output:
# ✅ ALL CLI TESTS PASSED
```

### Manual Test Checklist

- [ ] CLI starts without errors
- [ ] Can send messages and get responses
- [ ] `/help` command works
- [ ] `/debug` toggles debug mode
- [ ] `/metrics` shows statistics
- [ ] `/clear` clears history
- [ ] `/exit` exits cleanly
- [ ] Error messages are clear

---

## Migration from Legacy

If you were using Legacy OdiseoBot's `run_interactive()` method:

### Before (Legacy)

```python
from client_mcp.core.odiseo_bot import OdiseoBot

async def main():
    bot = OdiseoBot(debug_mode=False)
    await bot.initialize()
    await bot.run_interactive()  # Built-in CLI
    await bot.cleanup()
```

### After (CLI Tool)

```bash
# Just run the standalone CLI
python3 scripts/odiseo_cli.py
```

Or programmatically:

```python
from scripts.odiseo_cli import OdiseoCLI

async def main():
    cli = OdiseoCLI(debug_mode=False)
    await cli.initialize()
    await cli.run_interactive()  # Same interface
    # Cleanup is automatic
```

---

## Performance

### Initialization Time

- **Cold start**: ~2-3 seconds (MCP connection + context cache)
- **Warm start**: ~1 second (if MCP already running)

### Memory Usage

- **Baseline**: ~150MB (Python + dependencies)
- **With context cache**: +~50MB (cached tokens)
- **Per conversation**: +~1-2MB per 100 messages

### Response Time

- **First query**: ~5-10 seconds (includes tool execution)
- **Subsequent queries**: ~2-5 seconds (with cache)
- **Pagination**: <100ms (client-side)

---

## Best Practices

### 1. Start MCP Server First

```bash
# Terminal 1: MCP Server
cd mcp_server
python3 server.py

# Terminal 2: CLI Tool
python3 scripts/odiseo_cli.py
```

---

### 2. Use Debug Mode for Development

```bash
# Enable debug from start
python3 scripts/odiseo_cli.py
# Then: /debug
```

---

### 3. Monitor Metrics Regularly

```bash
# Check metrics periodically
# In CLI: /metrics
```

---

### 4. Clear History for New Topics

```bash
# Before changing topics
# In CLI: /clear
```

---

## Future Enhancements

Potential features for future versions:

- [ ] Command history (arrow keys)
- [ ] Autocomplete for commands
- [ ] Colored output (rich library)
- [ ] Save conversation to file
- [ ] Load previous conversation
- [ ] Multi-user support
- [ ] Web UI wrapper

---

## Support

### Documentation

- **CLI Guide**: `docs/CLI_TOOL_GUIDE.md` (this file)
- **Migration Guide**: `docs/MIGRATION_ODISEOBOT_V2.md`
- **V2 Architecture**: `agent/docs/NOTAS_CLAUDE.md`

### Issues

Report issues with CLI tool:
1. Check troubleshooting section
2. Enable debug mode (`/debug`)
3. Capture error messages
4. Create issue with details

---

## Changelog

### Version 1.0.0 (2025-10-12)

**Initial Release**:
- ✅ Interactive chat loop
- ✅ All commands (/help, /debug, /metrics, /clear, /exit)
- ✅ OdiseoBotV2 integration
- ✅ Comprehensive help system
- ✅ Detailed metrics display
- ✅ Error handling
- ✅ Automatic cleanup

**Replaces**: Legacy OdiseoBot `run_interactive()`, `_show_help()`, `show_metrics()` methods

---

**Author**: Lab01-MCP Team
**Created**: 2025-10-12
**Version**: 1.0.0
**Status**: ✅ Production Ready
