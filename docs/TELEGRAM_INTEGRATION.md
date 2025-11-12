# Integración de Telegram - Arquitectura Modular

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         CANALES (Adapters)                       │
├─────────────────────┬─────────────────────┬─────────────────────┤
│   CLI Adapter       │  Telegram Adapter   │  Future: Web/Slack  │
│   (Existing)        │  (python-telegram)  │  (WhatsApp/Discord) │
└──────────┬──────────┴──────────┬──────────┴──────────┬──────────┘
           │                      │                     │
           └──────────────────────┼─────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │       ChatCore             │
                    │  (Núcleo de conversación)  │
                    │                            │
                    │  - process_message()       │
                    │  - manage_session()        │
                    │  - call_gemini()           │
                    │  - call_mcp_tools()        │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
          ┌─────────▼──────────┐    ┌──────────▼───────────┐
          │  AgentOrchestrator │    │   MCP Connector      │
          │  (Multi-agent)     │    │   (Tools/Memory)     │
          │                    │    │                      │
          │  - Router          │    │  - search()          │
          │  - SalesAgent      │    │  - fuzzy_search()    │
          │  - BookingAgent    │    │  - create_appt()     │
          │  - GeneralAgent    │    │  - Memory blocks     │
          └────────────────────┘    └──────────────────────┘
                    │
          ┌─────────▼──────────┐
          │   Gemini API       │
          │  (LLM responses)   │
          └────────────────────┘
```

## Componentes Principales

### 1. ChatCore (Núcleo)
**Responsabilidad**: Encapsula toda la lógica de conversación
- Mantiene contexto por sesión (`session_id`)
- Orquesta llamadas a Gemini
- Invoca herramientas MCP cuando es necesario
- Retorna respuestas en texto plano

**API**:
```python
async def process_message(
    session_id: str,
    user_message: str,
    customer_email: Optional[str] = None
) -> str:
    """Procesa un mensaje y retorna la respuesta."""
```

### 2. Adaptadores (Channels)
**Responsabilidad**: Interfaz con canales externos
- **CLI Adapter**: Lee de stdin/stdout
- **Telegram Adapter**: Usa `python-telegram-bot`
- **Futuro**: Web UI, Discord, Slack, WhatsApp

Cada adaptador:
1. Recibe input del usuario
2. Genera `session_id` único por conversación
3. Llama a `ChatCore.process_message()`
4. Envía respuesta al usuario

### 3. Gestión de Sesiones
- **CLI**: Una sesión por ejecución del programa
- **Telegram**: `session_id = f"telegram_{chat_id}"`
- **Web**: `session_id = f"web_{user_id}_{conversation_id}"`

## Flujo de Datos

```
Usuario (Telegram/CLI)
    │
    │ 1. Mensaje + session_id
    ▼
Adaptador (CLI/Telegram)
    │
    │ 2. process_message(session_id, message)
    ▼
ChatCore
    │
    ├─► 3a. Clasifica intent (AgentRouter)
    ├─► 3b. Selecciona agente (Sales/Booking/General)
    ├─► 3c. Llama Gemini con historial
    ├─► 3d. Si necesita datos → MCP Tools
    │
    │ 4. Retorna respuesta (str)
    ▼
Adaptador
    │
    │ 5. Envía respuesta formateada
    ▼
Usuario
```

## Cómo Agregar un Nuevo Canal

### Ejemplo: Discord Bot

1. **Crear adaptador** en `integrations/discord_adapter.py`:

```python
from chat_core import ChatCore
import discord

class DiscordAdapter:
    def __init__(self):
        self.chat_core = ChatCore()
        self.client = discord.Client()

    @client.event
    async def on_message(self, message):
        if message.author.bot:
            return

        # Genera session_id único
        session_id = f"discord_{message.author.id}_{message.channel.id}"

        # Procesa mensaje
        response = await self.chat_core.process_message(
            session_id=session_id,
            user_message=message.content,
            customer_email=message.author.email
        )

        # Envía respuesta
        await message.channel.send(response)
```

2. **Lanzar adaptador**:
```python
# main_discord.py
adapter = DiscordAdapter()
await adapter.initialize()
await adapter.run(token=DISCORD_TOKEN)
```

3. **Sin cambios en ChatCore** → La lógica sigue centralizada.

## Ventajas de esta Arquitectura

✅ **Reutilización**: Un solo `ChatCore` para todos los canales
✅ **Escalabilidad**: Agregar canales es trivial (solo adapters)
✅ **Mantenibilidad**: La lógica de negocio vive en un solo lugar
✅ **Testing**: Fácil mockear adapters para tests
✅ **Memoria persistente**: Funciona igual para todos los canales

## Estructura de Archivos Propuesta

```
MCP-Server/
├── chat_core/
│   ├── __init__.py
│   ├── chat_core.py          # Núcleo central
│   ├── session_manager.py    # Gestión de sesiones
│   └── mcp_client.py         # Cliente MCP (reutiliza código existente)
│
├── integrations/
│   ├── __init__.py
│   ├── cli_adapter.py        # Adaptador CLI (refactorizado)
│   ├── telegram_adapter.py   # Nuevo adaptador Telegram
│   └── base_adapter.py       # Clase base opcional
│
├── client_mcp/               # Código existente (reutilizado)
│   ├── core/
│   │   ├── agent_orchestrator.py  ← Usado por ChatCore
│   │   └── mcp_connector.py       ← Usado por ChatCore
│   └── ...
│
├── main_cli.py              # Launcher CLI
├── main_telegram.py         # Launcher Telegram
└── requirements_telegram.txt
```

## Dependencias Nuevas

```txt
# requirements_telegram.txt
python-telegram-bot>=20.0
```

## Configuración Telegram

```env
# .env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ENABLE_AGENT_ROUTING=true
```

---

**Próximos pasos**: Ver implementación en `/chat_core/` y `/integrations/`
