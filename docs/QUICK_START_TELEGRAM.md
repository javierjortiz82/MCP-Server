# Quick Start: Telegram Bot

Guía rápida para levantar el bot de Telegram usando la nueva arquitectura modular.

## Pre-requisitos

1. Python 3.10+
2. Dependencias base instaladas (`pip install -r requirements.txt`)
3. Base de datos PostgreSQL configurada (para memoria persistente)
4. MCP Server corriendo (puerto 8009)

## Paso 1: Instalar Dependencias de Telegram

```bash
pip install -r requirements_telegram.txt
```

Esto instalará:
- `python-telegram-bot>=20.0` (SDK de Telegram)
- `python-dotenv>=1.0.0` (para variables de entorno)

## Paso 2: Crear Bot en Telegram

1. Abrir Telegram y buscar `@BotFather`
2. Enviar `/newbot`
3. Seguir instrucciones:
   - Nombre del bot: `Lab01-MCP Bot` (o el que quieras)
   - Username: `lab01_mcp_bot` (debe terminar en `_bot`)
4. Copiar el **token** que te da BotFather (ejemplo: `123456:ABC-DEF1234...`)

## Paso 3: Configurar Token

**Opción 1: Variable de entorno**

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234..."
```

**Opción 2: Archivo .env**

Crear archivo `.env` en la raíz del proyecto:

```bash
echo "TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234..." > .env
```

## Paso 4: Verificar MCP Server

Asegurarse de que el MCP Server esté corriendo:

```bash
# En otra terminal:
cd mcp_server
python -m mcp_server

# O usando Docker:
docker-compose up mcp-server
```

Verificar que responde en `http://localhost:8009`

## Paso 5: Lanzar Bot de Telegram

```bash
python main_telegram.py
```

Deberías ver:

```
======================================================================
🤖 Lab01-MCP Telegram Bot
======================================================================
Powered by ChatCore - Arquitectura modular multi-canal
======================================================================
✅ Token configurado: 123456:ABC...
✅ Telegram bot initialized
🚀 Starting Telegram bot...
   Press Ctrl+C to stop
```

## Paso 6: Probar el Bot

1. Buscar tu bot en Telegram (por el username que le diste)
2. Enviar `/start`
3. Probar comandos:

```
/start          - Mensaje de bienvenida
/help           - Ver comandos disponibles
/clear          - Reiniciar conversación

# Pruebas de conversación:
Busco una laptop gaming
¿Tienen laptops con RTX 4070?
Quiero agendar una cita para mañana
```

## Comandos del Bot

| Comando  | Descripción                    |
|----------|--------------------------------|
| `/start` | Iniciar conversación           |
| `/help`  | Mostrar ayuda                  |
| `/clear` | Reiniciar conversación         |

Simplemente escribe tu mensaje y el bot responderá usando:
- AgentRouter (clasificación de intent)
- Agentes especializados (Sales/Booking/General)
- Gemini 2.5 Flash (LLM)
- MCP Tools (búsqueda en PostgreSQL)

## Arquitectura

```
Usuario en Telegram
    │
    ▼
Telegram Adapter (telegram_adapter.py)
    │
    ▼
ChatCore (chat_core.py)
    │
    ├─► Session Manager (una sesión por chat_id)
    ├─► AgentOrchestrator (routing multi-agente)
    ├─► Gemini API
    └─► MCP Connector (herramientas de búsqueda)
    │
    ▼
Respuesta al usuario
```

## Gestión de Sesiones

- **Session ID**: `telegram_{chat_id}`
- **Memoria persistente**: Por `username` o `telegram_user_{user_id}`
- **Contexto**: Cada chat tiene su propio `AgentOrchestrator`
- **Cleanup**: Automático al usar `/clear`

## Troubleshooting

### Error: "TELEGRAM_BOT_TOKEN not found"

**Solución**: Verificar que la variable de entorno esté configurada:

```bash
echo $TELEGRAM_BOT_TOKEN
```

Si está vacío, configurar:

```bash
export TELEGRAM_BOT_TOKEN="tu_token_aqui"
```

### Error: "Connection to MCP server failed"

**Solución**: Verificar que el MCP Server esté corriendo:

```bash
curl http://localhost:8009/health
```

Si no responde, iniciar el servidor:

```bash
cd mcp_server
python -m mcp_server
```

### Bot no responde en Telegram

**Posibles causas:**

1. Token incorrecto → Verificar con BotFather
2. Bot no está corriendo → Verificar terminal donde ejecutaste `main_telegram.py`
3. Error en logs → Revisar salida de consola

### Error: "python-telegram-bot not installed"

**Solución**:

```bash
pip install -r requirements_telegram.txt
```

## Logs y Debugging

El bot muestra logs en tiempo real:

```
🚀 Starting Telegram bot...
✅ Telegram bot initialized
[INFO] Processing message for session: telegram_123456
[INFO] Response generated for session telegram_123456
```

Para debugging más detallado, configurar `LOG_LEVEL=DEBUG` en `.env`.

## Detener el Bot

Presionar `Ctrl+C` en la terminal donde está corriendo:

```
^C
👋 Stopping bot...
[INFO] Cleaning up all ChatCore resources
[INFO] ChatCore cleanup complete
```

## Próximos Pasos

1. **Personalizar mensajes**: Editar respuestas en `telegram_adapter.py`
2. **Agregar comandos**: Añadir handlers en `telegram_adapter.py`
3. **Métricas**: Integrar logging/telemetría
4. **Deploy**: Usar webhooks para producción (más eficiente que polling)

## Notas

- **Polling vs Webhooks**: Esta implementación usa polling (bueno para desarrollo). Para producción, considerar webhooks.
- **Rate limiting**: Telegram permite ~30 mensajes/segundo. ChatCore no tiene rate limiting built-in aún.
- **Memoria persistente**: Funciona igual que en CLI si el usuario proporciona username válido.

## Más Información

- Documentación completa: `docs/TELEGRAM_INTEGRATION.md`
- Arquitectura del proyecto: `docs/ARQUITECTURA_COMPLETA.md`
- python-telegram-bot docs: https://docs.python-telegram-bot.org/

---

**¡Listo!** Tu bot de Telegram está corriendo con la misma lógica que el CLI, sin duplicar código. 🚀
