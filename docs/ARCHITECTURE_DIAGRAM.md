# Diagrama de Arquitectura Modular Multi-Canal

## Vista General

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CANALES / CHANNELS                             │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐ │
│  │  CLI User    │    │ Telegram User│    │  Future: Web/Discord     │ │
│  │              │    │              │    │                          │ │
│  │  Terminal    │    │  Telegram    │    │  WebSocket/REST API      │ │
│  │  stdin/out   │    │  Messages    │    │  Browser/Mobile App      │ │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────────────┘ │
└─────────┼────────────────────┼─────────────────────┼───────────────────┘
          │                    │                     │
          │                    │                     │
┌─────────▼────────────────────▼─────────────────────▼───────────────────┐
│                        ADAPTER LAYER                                    │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐ │
│  │ CLIAdapter   │    │TelegramAdapter│   │  WebAdapter (futuro)     │ │
│  │              │    │              │    │                          │ │
│  │ • read stdin │    │ • webhook/   │    │ • WebSocket handler      │ │
│  │ • print out  │    │   polling    │    │ • REST endpoints         │ │
│  │ • /commands  │    │ • /commands  │    │ • Session management     │ │
│  │              │    │ • typing ind.│    │                          │ │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────────────┘ │
└─────────┼────────────────────┼─────────────────────┼───────────────────┘
          │                    │                     │
          │   session_id       │  session_id         │  session_id
          │   user_message     │  user_message       │  user_message
          │   customer_email   │  customer_email     │  customer_email
          │                    │                     │
          └────────────────────┼─────────────────────┘
                               │
                               │ process_message()
                               │
┌──────────────────────────────▼─────────────────────────────────────────┐
│                          CORE LAYER                                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                        ChatCore                                 │   │
│  │                                                                  │   │
│  │  • process_message(session_id, message, email)                 │   │
│  │  • get_or_create_session() → Session                           │   │
│  │  • get_or_create_orchestrator() → AgentOrchestrator            │   │
│  │  • cleanup_session(session_id)                                 │   │
│  │  • cleanup_all()                                                │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │           SessionManager                                 │  │   │
│  │  │                                                           │  │   │
│  │  │  sessions: {                                             │  │   │
│  │  │    "cli_abc123": Session(...),                           │  │   │
│  │  │    "telegram_456": Session(...),                         │  │   │
│  │  │    "web_789": Session(...)                               │  │   │
│  │  │  }                                                        │  │   │
│  │  │                                                           │  │   │
│  │  │  orchestrators: {                                        │  │   │
│  │  │    "cli_abc123": AgentOrchestrator(...),                 │  │   │
│  │  │    "telegram_456": AgentOrchestrator(...),               │  │   │
│  │  │    "web_789": AgentOrchestrator(...)                     │  │   │
│  │  │  }                                                        │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               │ orchestrator.process_query()
                               │
┌──────────────────────────────▼─────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                                  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   AgentOrchestrator                             │   │
│  │                                                                  │   │
│  │  1. Intent Classification (AgentRouter)                        │   │
│  │     ├─► "sales"   → Route to SalesAgent                        │   │
│  │     ├─► "booking" → Route to BookingAgent                      │   │
│  │     └─► "general" → Route to GeneralAgent                      │   │
│  │                                                                  │   │
│  │  2. Agent Execution                                             │   │
│  │     • Maintain conversation history                            │   │
│  │     • Call Gemini API with context                             │   │
│  │     • Extract function calls                                    │   │
│  │     • Execute MCP tools if needed                              │   │
│  │     • Return natural language response                         │   │
│  │                                                                  │   │
│  │  3. Memory Management (if customer_email provided)             │   │
│  │     • Session memory (conversation_messages)                   │   │
│  │     • User memory (cross-session, user_memory_blocks)          │   │
│  │     • Agent transitions (agent_context_transfers)              │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┬──────────────────────────┘
                   │                          │
                   │                          │
         ┌─────────▼──────────┐      ┌───────▼────────────┐
         │   Gemini API       │      │  MCP Connector     │
         │   (LLM)            │      │  (Tools)           │
         │                    │      │                    │
         │ • Gemini 2.5 Flash │      │ • search()         │
         │ • Function calling │      │ • fuzzy_search()   │
         │ • Multi-turn chat  │      │ • create_appt()    │
         │                    │      │ • get_memory()     │
         └────────────────────┘      └───────┬────────────┘
                                             │
                                             │
                                    ┌────────▼──────────┐
                                    │  PostgreSQL DB    │
                                    │                   │
                                    │ • products        │
                                    │ • appointments    │
                                    │ • memory_blocks   │
                                    │ • sessions        │
                                    └───────────────────┘
```

## Flujo de Mensaje Completo

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. USUARIO ENVÍA MENSAJE                                               │
│     "Busco una laptop gaming con RTX 4070"                              │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  2. ADAPTER CAPTURA MENSAJE                                             │
│     • Genera session_id: "telegram_123456"                              │
│     • Extrae metadata: {chat_id, username, ...}                         │
│     • Identifica customer_email (si disponible)                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ process_message(
                             │   session_id="telegram_123456",
                             │   user_message="Busco una laptop...",
                             │   customer_email="user@example.com"
                             │ )
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  3. CHATCORE PROCESA                                                    │
│     • get_or_create_session("telegram_123456")                          │
│     • get_or_create_orchestrator(session)                               │
│     • orchestrator.process_query("Busco una laptop...")                 │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  4. ORCHESTRATOR CLASIFICA INTENT                                       │
│     • AgentRouter.classify("Busco una laptop...")                       │
│     • Result: Intent.SALES                                              │
│     • Route to: SalesAgent                                              │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  5. SALESAGENT PROCESA                                                  │
│     • Llama Gemini con conversación + tools disponibles                │
│     • Gemini: "Necesito buscar en DB → function_call: search()"        │
│     • SalesAgent ejecuta: mcp_client.search(query="laptop RTX 4070")   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  6. MCP CONNECTOR                                                       │
│     • HTTP POST a http://localhost:8009                                 │
│     • Ejecuta tool: search_products(query="laptop RTX 4070")           │
│     • PostgreSQL query con fuzzy matching                               │
│     • Retorna: [{id: 1, name: "Laptop ASUS ROG...", specs: ...}, ...]  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ function_response
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  7. GEMINI GENERA RESPUESTA NATURAL                                     │
│     • Recibe resultados de búsqueda                                     │
│     • Genera respuesta conversacional:                                  │
│       "Encontré 3 laptops gaming con RTX 4070:                          │
│        1. ASUS ROG Strix - $1,899                                       │
│        2. MSI Raider GE78 - $2,199                                      │
│        3. Alienware m16 - $2,499"                                       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  8. ORCHESTRATOR RETORNA A CHATCORE                                     │
│     • response: "Encontré 3 laptops gaming..."                          │
│     • Actualiza conversation_history                                    │
│     • Guarda en session_memory (si email disponible)                    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  9. CHATCORE RETORNA A ADAPTER                                          │
│     • return response: "Encontré 3 laptops gaming..."                   │
│     • Session.update_activity()                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  10. ADAPTER ENVÍA RESPUESTA AL USUARIO                                 │
│      • Telegram: message.reply_text(response)                           │
│      • CLI: print(f"🤖 Bot: {response}")                                │
│      • Web: ws.send(json.dumps({response}))                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Gestión de Sesiones

```
┌─────────────────────────────────────────────────────────────────┐
│                     SessionManager                               │
│                                                                   │
│  sessions = {                                                    │
│    "cli_abc123": Session(                                        │
│        session_id="cli_abc123",                                  │
│        customer_email="user1@example.com",                       │
│        metadata={},                                              │
│        created_at=2025-11-11 10:00:00,                           │
│        last_activity=2025-11-11 10:05:23                         │
│    ),                                                            │
│                                                                   │
│    "telegram_456789": Session(                                   │
│        session_id="telegram_456789",                             │
│        customer_email="telegram_user_456789",                    │
│        metadata={                                                │
│          "chat_id": 456789,                                      │
│          "username": "john_doe",                                 │
│          "first_name": "John",                                   │
│          "last_name": "Doe"                                      │
│        },                                                        │
│        created_at=2025-11-11 09:30:00,                           │
│        last_activity=2025-11-11 10:10:45                         │
│    )                                                             │
│  }                                                               │
│                                                                   │
│  orchestrators = {                                               │
│    "cli_abc123": AgentOrchestrator(                              │
│        session_id="mem_session_123",                             │
│        customer_email="user1@example.com",                       │
│        routing_enabled=True,                                     │
│        # Agentes: SalesAgent, BookingAgent, GeneralAgent         │
│    ),                                                            │
│                                                                   │
│    "telegram_456789": AgentOrchestrator(                         │
│        session_id="mem_session_456",                             │
│        customer_email="telegram_user_456789",                    │
│        routing_enabled=True,                                     │
│        # Agentes: SalesAgent, BookingAgent, GeneralAgent         │
│    )                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Relación con Base de Datos

```
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│                                                                   │
│  Schema: lab01 (configurable via SCHEMA_NAME)                   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  products                                               │    │
│  │  • id, name, description, price, category, specs        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  appointments                                           │    │
│  │  • id, customer_email, date, time, status              │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  sessions (memoria persistente)                         │    │
│  │  • session_id, customer_email, language, created_at    │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  conversation_messages (historial por sesión)          │    │
│  │  • session_id, role, content, timestamp                 │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  agent_memory_blocks (memoria de sesión)               │    │
│  │  • session_id, key, value, agent_name                   │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  user_memory_blocks (memoria cross-session)            │    │
│  │  • customer_email, key, value, created_at               │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  agent_context_transfers (auditoría de handoffs)       │    │
│  │  • from_agent, to_agent, session_id, reason, timestamp │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Extensibilidad: Agregar un Nuevo Canal

```
┌─────────────────────────────────────────────────────────────────┐
│  1. CREAR NUEVO ADAPTER                                          │
│                                                                   │
│     integrations/discord_adapter.py:                            │
│                                                                   │
│     class DiscordAdapter:                                        │
│         def __init__(self):                                      │
│             self.chat_core = ChatCore()                          │
│                                                                   │
│         async def on_message(self, message):                     │
│             session_id = f"discord_{message.author.id}"          │
│             response = await self.chat_core.process_message(     │
│                 session_id=session_id,                           │
│                 user_message=message.content,                    │
│                 customer_email=message.author.email              │
│             )                                                    │
│             await message.channel.send(response)                 │
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  2. CREAR LAUNCHER                                               │
│                                                                   │
│     main_discord.py:                                            │
│                                                                   │
│     adapter = DiscordAdapter()                                   │
│     await adapter.initialize()                                   │
│     await adapter.run(token=DISCORD_TOKEN)                       │
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  3. SIN CAMBIOS EN CHATCORE                                      │
│                                                                   │
│     ✅ Toda la lógica de negocio sigue en ChatCore              │
│     ✅ AgentOrchestrator se reutiliza automáticamente           │
│     ✅ Memoria persistente funciona igual                        │
│     ✅ MCP tools disponibles sin configuración extra             │
└─────────────────────────────────────────────────────────────────┘
```

---

**Arquitectura diseñada para:**
- ✅ Escalabilidad horizontal (múltiples canales)
- ✅ Separación de responsabilidades (adapters vs core)
- ✅ Reutilización de código (un solo ChatCore)
- ✅ Mantenibilidad (cambios en un solo lugar)
- ✅ Extensibilidad (agregar canales es trivial)
