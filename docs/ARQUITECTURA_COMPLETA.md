# MCP-Server: Análisis Arquitectónico Completo

**Fecha:** 2025-11-11  
**Proyecto:** MCP-Server (Multi-Agent Model Context Protocol)  
**Rama Actual:** feat/integration-services  
**Estado:** Funcional y Listo para Producción

---

## INDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estructura de Directorios](#estructura-de-directorios)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Comunicación](#flujo-de-comunicación)
5. [Sistema de Memoria](#sistema-de-memoria)
6. [Configuración Crítica](#configuración-crítica)
7. [Startup y Inicialización](#startup-e-inicialización)
8. [Troubleshooting](#troubleshooting)

---

## Resumen Ejecutivo

El MCP-Server es un **sistema de IA multi-agente** que implementa el protocolo MCP (Model Context Protocol) de Anthropic con las siguientes características:

### Componentes Principales

```
┌──────────────────────────────────┐
│      CLIENTE CLI                 │
│  (client_mcp/__main__.py)         │
│  - Input/output de usuario       │
│  - Orquestación multi-agente     │
│  - Conexión MCP vía HTTP         │
└──────────────────────────────────┘
            │ HTTP
            │ JSON-RPC 2.0
            ↓
┌──────────────────────────────────┐
│   SERVIDOR MCP                   │
│  (mcp_server/server.py)          │
│  - FastMCP + uvicorn             │
│  - Herramientas de búsqueda      │
│  - Persistencia de memoria       │
│  - PostgreSQL backend            │
└──────────────────────────────────┘
            │
            ↓
┌──────────────────────────────────┐
│   AGENTES (Gemini)               │
│  (agent/src/multi_agent/)        │
│  - SalesAgent                    │
│  - BookingAgent                  │
│  - GeneralAgent                  │
│  - AgentRouter (clasificador)    │
└──────────────────────────────────┘
```

### Características Clave

- **Comunicación**: Cliente ↔ Servidor MCP vía HTTP (JSON-RPC 2.0)
- **Inteligencia**: Gemini API para reasoning + generación
- **Orquestación**: Multi-agente con routing automático por intent
- **Memoria**: Persistente (PostgreSQL) y transferible entre sesiones
- **Búsqueda**: Difusa (pg_trgm) + semántica (embeddings)
- **Escalabilidad**: Stateless HTTP, preparado para producción

---

## Estructura de Directorios

```
MCP-Server/
│
├── client_mcp/                    # CLIENTE MCP (CLI)
│   ├── __main__.py               # Punto de entrada: asyncio.run(main())
│   ├── config/
│   │   └── settings.py           # Config Pydantic v2 (GOOGLE_API_KEY, MCP_BASE_URL, etc)
│   ├── core/                     # Lógica principal
│   │   ├── agent_orchestrator.py # Orquestador (CLAVE)
│   │   ├── mcp_connector.py      # Cliente HTTP/stdio
│   │   ├── conversation_manager.py # Gestión de historial
│   │   ├── tool_executor.py      # Ejecutor de function_calls
│   │   ├── response_processor.py # Procesador respuestas
│   │   ├── tool_cache.py         # Cache de herramientas
│   │   └── [otros]
│   ├── interfaces/
│   │   ├── cli/                  # CLI interactivo
│   │   └── telegram/             # Bot Telegram
│   ├── observability/            # Métricas y logs
│   └── utils/
│
├── mcp_server/                    # SERVIDOR MCP (FastMCP)
│   ├── server.py                 # Punto de entrada: uvicorn
│   ├── config/
│   │   └── settings.py           # Config (SCHEMA_NAME, DB_URL)
│   ├── mcp_handlers/             # Registradores de tools
│   │   ├── product_handlers.py   # "search", "fuzzy_search"
│   │   ├── booking_handlers.py   # "create_appointment"
│   │   ├── resource_handlers.py  # Recursos URI
│   │   └── prompt_handlers.py    # Plantillas de prompts
│   ├── tools/                    # Implementación de tools
│   │   ├── search.py             # SQL + normalización
│   │   ├── fuzzy_search.py       # pg_trgm + unaccent
│   │   ├── bookings.py           # CRUD appointments
│   │   ├── fetch.py              # Fetch genérico
│   │   └── ingest.py             # Ingesta datos
│   ├── utils/
│   │   ├── db.py                 # Conexión PostgreSQL
│   │   ├── memory_manager.py     # Persistencia memoria (CLAVE)
│   │   ├── context_transfer.py   # Handoff entre agentes
│   │   ├── semantic_extractor.py # Extractor facts (Gemini)
│   │   ├── language_context.py   # Context idioma
│   │   ├── embeddings.py         # Búsqueda semántica
│   │   └── logger.py
│   ├── locales/                  # Traducciones (en/, es/)
│   └── tests/
│
├── agent/                         # SISTEMA MULTI-AGENTE (Gemini)
│   └── src/
│       ├── multi_agent/          # Orquestación
│       │   ├── agent_router.py      # Clasificador intents
│       │   ├── agent_factory.py     # Factory pattern
│       │   ├── sales_agent.py       # Agente ventas
│       │   ├── booking_agent.py     # Agente reservas
│       │   ├── general_agent.py     # Agente general/FAQ
│       │   └── prompt_manager.py    # Gestor prompts
│       └── gemini_agent/         # BaseAgent
│           ├── base_agent.py        # Clase base (wrapper Gemini)
│           ├── agent.py             # Implementación
│           ├── config/
│           │   └── settings.py
│           └── utils/
│
├── demo_agent/                   # FastAPI backend integrado
│   ├── routes/
│   ├── models/
│   ├── services/
│   └── [otros]
│
├── email_service/                # Servicio correo (RabbitMQ worker)
│   ├── clients/
│   ├── models/
│   ├── worker/
│   └── observability/
│
├── SQL/                          # Migraciones PostgreSQL
│   ├── 00_init/
│   ├── 01_ddl/
│   │   ├── booking/
│   │   ├── memory/               # Tablas de memoria
│   │   └── utils/
│   ├── 02_functions/             # Functions PostgreSQL
│   ├── 02_migrations/
│   ├── 03_indexes/
│   └── 04_seed/
│
├── prompts/                      # Plantillas de prompts
│   ├── templates/
│   │   ├── base/                 # Prompts base
│   │   ├── sales_agent/
│   │   ├── booking_agent/
│   │   └── general_agent/
│   └── config/
│
├── docs/                         # Documentación
├── scripts/                      # Scripts de utilidad
├── Makefile                      # Automatización
├── pyproject.toml               # Config Python
└── requirements.txt             # Dependencias
```

---

## Componentes Principales

### 1. CLIENTE MCP (client_mcp/)

**Responsabilidad**: Interfaz de usuario y orquestación de agentes

**Flujo Clave**:
```
python -m client_mcp
  ↓
main() → AgentOrchestrator.initialize(customer_email)
  ↓
MCPConnector crea conexión HTTP a servidor
  ↓
AgentFactory crea AgentRouter + agentes
  ↓
run_interactive() → bucle input/output
  ├─ AgentRouter clasifica intent
  ├─ Selecciona agente (Sales/Booking/General)
  ├─ Agente procesa (con herramientas MCP si necesita)
  └─ Respuesta natural al usuario
```

**Archivos Clave**:

| Archivo | Clase | Propósito |
|---------|-------|----------|
| `__main__.py` | `main()` | asyncio.run() - entrada |
| `config/settings.py` | `Settings` | Pydantic v2 config |
| `core/agent_orchestrator.py` | `AgentOrchestrator` | Orquestación (CLAVE) |
| `core/mcp_connector.py` | `MCPConnector` | Cliente MCP HTTP |

**Flujo AgentOrchestrator.initialize()**:
```python
async def initialize(self, customer_email=None):
    # 1. Conecta a servidor MCP
    self.mcp_connector = MCPConnector(settings.mcp_base_url)
    await self.mcp_connector.__aenter__()
    
    # 2. Descubre herramientas
    self.tools = await self.mcp_connector.list_tools()
    
    # 3. Carga memoria si customer_email
    if customer_email:
        self.memory = MemoryManager.load_user_memory(customer_email)
    
    # 4. Crea agentes
    self.router = AgentFactory.create_router(
        tools=self.tools,
        memory=self.memory
    )
```

---

### 2. SERVIDOR MCP (mcp_server/)

**Responsabilidad**: Exponer herramientas vía HTTP, persistencia de datos

**Flujo Clave**:
```
python -m mcp_server.server --port 8009
  ↓
FastMCP initialization
  ├─ product_handlers.init() → registra "search", "fuzzy_search"
  ├─ booking_handlers.init() → registra "create_appointment"
  └─ otros handlers
  ↓
db.init_db() → valida PostgreSQL, extensiones, functions
  ↓
uvicorn.run(app, host="0.0.0.0", port=8009)
  ├─ Escucha /mcp → JSON-RPC 2.0 requests
  └─ Escucha /health → status check
```

**Archivos Clave**:

| Archivo | Propósito |
|---------|----------|
| `server.py` | FastMCP + uvicorn setup |
| `mcp_handlers/product_handlers.py` | Registra herramientas búsqueda |
| `tools/search.py` | Implementación búsqueda |
| `utils/memory_manager.py` | Persistencia memoria |

**Endpoints MCP**:
```
POST /mcp
Content-Type: application/json

Listar herramientas:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}

Llamar herramienta:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "laptop"}
  }
}
```

---

### 3. SISTEMA MULTI-AGENTE (agent/src/)

**Responsabilidad**: Reasoning con Gemini API, decisiones inteligentes

**Estructura**:
```
AgentRouter (clasifica intent)
  ├─ SalesAgent (productos)
  ├─ BookingAgent (reservas)
  ├─ GeneralAgent (FAQ)
  └─ Todos heredan de BaseAgent (Gemini wrapper)
```

**Flujo AgentRouter**:
```python
class AgentRouter(BaseAgent):
    async def classify_intent(self, query: str) -> Intent:
        # Prompt: "Clasifica este mensaje como sales, booking o general"
        # Gemini analiza y retorna Intent.SALES | BOOKING | GENERAL
```

**Flujo SalesAgent**:
```python
class SalesAgent(BaseAgent):
    async def process(self, query: str):
        # 1. Inyectados: MCP tools + memory blocks
        # 2. Llama Gemini con system_prompt
        # 3. Si Gemini dice "necesito search":
        #    - Genera function_call: {tool: "search", args: {...}}
        #    - MCPConnector.call_tool() lo ejecuta
        #    - Resultado inyectado en conversation_history
        # 4. Llama Gemini de nuevo con resultado
        # 5. Genera respuesta natural
```

---

## Flujo de Comunicación

### Secuencia Completa: Usuario pregunta "Quiero un laptop"

```
1. USUARIO → CLIENTE
   Input: "Quiero un laptop"

2. CLIENTE → AgentOrchestrator
   query = "Quiero un laptop"

3. AgentOrchestrator → AgentRouter
   Classify intent(query) → Intent.SALES

4. AgentOrchestrator → SalesAgent
   Inyecta: MCP tools, memory blocks previos

5. SalesAgent → Gemini API
   system_prompt + conversation_history + "Quiero un laptop"
   
   Gemini analiza y decide:
   "Debo buscar laptops en el inventario"
   → Genera function_call: {tool: "search", args: {query: "laptop"}}

6. SalesAgent → MCPConnector
   Detecta function_call, llama call_tool("search", {query: "laptop"})

7. MCPConnector → MCP Server (HTTP POST)
   POST /mcp
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "tools/call",
     "params": {
       "name": "search",
       "arguments": {"query": "laptop"}
     }
   }

8. MCP Server → ProductHandler.search()
   ├─ Normaliza: "laptop" → normalize_text("laptop")
   ├─ Búsqueda: SELECT * FROM products WHERE ... (pg_trgm)
   ├─ Resultado: [{id: 1, name: "Dell XPS", price: 2000}, ...]
   └─ MemoryManager guarda en conversation_messages + memory_blocks

9. MCP Server → MCPConnector (JSON response)
   {
     "result": {
       "content": [
         {
           "type": "text",
           "text": "[{...productos...}]"
         }
       ]
     }
   }

10. MCPConnector → SalesAgent
    Tool result inyectado en conversation_history

11. SalesAgent → Gemini API (continue conversation)
    Prompt: "Aquí están los resultados de la búsqueda: [...]"
    
    Gemini genera:
    "Te encontré estos laptops: Dell XPS 15 ($2000), HP Pavilion ($1200)..."

12. SalesAgent → AgentOrchestrator
    response_text = "Te encontré estos laptops: ..."

13. AgentOrchestrator → USUARIO (stdout)
    print("Te encontré estos laptops: ...")

14. Vuelve a step 2 (input de usuario)
```

### Diagrama ASCII Completo

```
┌──────────────┐
│    USUARIO   │ "Quiero un laptop"
└───────┬──────┘
        │ input()
        ↓
┌──────────────────────────────────────────────────────┐
│              CLIENT_MCP (/client_mcp/)                │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ AgentOrchestrator                              │ │
│  │  1. Clasifica intent → AgentRouter             │ │
│  │  2. Selecciona agente → SalesAgent             │ │
│  │  3. Llama agente.process(query)                │ │
│  └────────────────────────────────────────────────┘ │
│                       │                              │
│  ┌────────────────────┼─────────────────────────┐   │
│  │ SalesAgent (Gemini + MCP Tools)              │   │
│  │  1. Llama Gemini API con system_prompt       │   │
│  │  2. Gemini: "Necesito buscar laptops"        │   │
│  │  3. Genera function_call {tool: "search"}    │   │
│  │  4. MCPConnector.call_tool("search", {...})  │   │
│  └────────────────────┬─────────────────────────┘   │
└───────────────────────┼──────────────────────────────┘
                        │ HTTP POST /mcp
                        │ JSON-RPC: method="tools/call"
                        ↓
┌──────────────────────────────────────────────────────┐
│           MCP_SERVER (/mcp_server/)                  │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ FastMCP (Anthropic SDK)                        │ │
│  │  - Recibe JSON-RPC request                     │ │
│  │  - method="tools/call", name="search"          │ │
│  │  - Delega a ProductHandler                     │ │
│  └────────────────────┬──────────────────────────┘ │
│                       │                              │
│  ┌────────────────────▼──────────────────────────┐ │
│  │ ProductHandler.search()                       │ │
│  │  1. Valida parámetros                         │ │
│  │  2. Ejecuta tools/search.py                   │ │
│  │  3. SQL: SELECT * FROM products WHERE ...     │ │
│  │  4. Retorna JSON                              │ │
│  └────────────────────┬──────────────────────────┘ │
│                       │                              │
│  ┌────────────────────▼──────────────────────────┐ │
│  │ MemoryManager                                 │ │
│  │  - Guarda: conversation_messages              │ │
│  │  - Extrae: memory blocks vía SemanticExtractor│ │
│  │  - Inserta: user_memory_blocks                │ │
│  └────────────────────┬──────────────────────────┘ │
│                       │                              │
│  ┌────────────────────▼──────────────────────────┐ │
│  │ PostgreSQL Database                           │ │
│  │  ├─ products                                  │ │
│  │  ├─ conversation_messages                     │ │
│  │  ├─ agent_memory_blocks                       │ │
│  │  └─ user_memory_blocks                        │ │
│  └────────────────────────────────────────────────┘ │
└────────────────────┬──────────────────────────────┘
                     │ JSON response: [productosJSON]
                     ↓
┌──────────────────────────────────────────────────────┐
│            CLIENT_MCP (continuación)                 │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ SalesAgent (loop Gemini)                       │ │
│  │  1. Recibe: [{Dell XPS, $2000}, {HP, $1200}] │ │
│  │  2. Llama Gemini: "Aquí están los resultados" │ │
│  │  3. Gemini genera: "Te encontré estos laptops" │ │
│  │  4. Retorna respuesta natural                  │ │
│  └────────────────────┬──────────────────────────┘ │
│                       │                              │
│  ┌────────────────────▼──────────────────────────┐ │
│  │ AgentOrchestrator.run_interactive()           │ │
│  │  - Recibe respuesta                           │ │
│  │  - Print al usuario                           │ │
│  │  - Vuelve a input()                           │ │
│  └────────────────────┬──────────────────────────┘ │
└──────────────────────┼─────────────────────────────┘
                       │ stdout
                       ↓
              ┌────────────────┐
              │  USUARIO RECIBE│
              │ "Te encontré..." │
              └────────────────┘
```

---

## Sistema de Memoria

### Arquitectura de Memoria

```
┌──────────────────────────────────────┐
│   MEMORIA EN RAM (Short-term)        │
├──────────────────────────────────────┤
│  BaseAgent.conversation_history      │
│  - Últimas 10 turns (user + model)   │
│  - Tipo: list[types.Content]         │
│  - Propósito: Acelerar respuestas    │
└──────────────────────────────────────┘
            ↓ Sincroniza con
┌──────────────────────────────────────┐
│   POSTGRESQL (Long-term)             │
├──────────────────────────────────────┤
│  conversation_messages               │
│  - Todas las interacciones           │
│  - session_id, role, agent_name      │
│                                      │
│  agent_memory_blocks                 │
│  - Memory blocks por sesión          │
│  - block_label, block_value, priority│
│                                      │
│  user_memory_blocks                  │
│  - Cross-session (PK: customer_email)│
│  - Cargados al inicio de sesión      │
│                                      │
│  agent_context_transfers             │
│  - Auditoria de handoffs             │
│  - from_agent, to_agent, reason      │
└──────────────────────────────────────┘
```

### Ciclo de Vida de Memoria

```
SESIÓN 1: Usuario new, entra con email "john@example.com"
│
├─ AgentOrchestrator.initialize(customer_email="john@example.com")
│  └─ MemoryManager.load_user_memory("john@example.com")
│     └─ SELECT * FROM user_memory_blocks WHERE customer_email = ...
│        └─ Resultado: [] (empty, primera vez)
│
├─ Usuario: "Quiero laptop gaming con presupuesto $1500"
├─ SalesAgent procesa
├─ MemoryManager.store_memory_block():
│  ├─ session_id = uuid_sesion_1
│  ├─ block_label = "product_interest"
│  ├─ block_value = "Gaming laptop, budget $1500"
│  ├─ priority = 7
│  └─ INSERT INTO agent_memory_blocks
│
├─ SemanticExtractor.extract_from_conversation():
│  ├─ Analiza conversation_messages
│  ├─ Llama Gemini: "Extrae facts importantes"
│  ├─ Gemini retorna: "User wants gaming laptop, $1500 budget"
│  └─ INSERT INTO user_memory_blocks (PK: john@example.com)
│
└─ SESSION 1 END

SESIÓN 2: 3 días después, user regresa
│
├─ Usuario entra email: "john@example.com"
├─ AgentOrchestrator.initialize(customer_email="john@example.com")
├─ MemoryManager.load_user_memory("john@example.com"):
│  └─ SELECT * FROM user_memory_blocks
│  └─ Resultado: [{
│       block_label: "product_interest",
│       block_value: "Gaming laptop, budget $1500",
│       priority: 7
│     }]
│
├─ Inyecta memory_blocks en agentes
├─ SalesAgent ya sabe preferencias del user
├─ Usuario: "¿Cuál es la mejor opción?"
├─ SalesAgent (con memoria): "Basándome en tu preferencia anterior de gaming laptop..."
│
└─ Nueva session_id = uuid_sesion_2
   └─ Inserta en conversation_messages (sesión nueva)
   └─ PERO reutiliza user_memory_blocks (persistente)
```

### Tabla de Bases de Datos

```sql
-- TABLA 1: conversation_messages (sesión actual)
CREATE TABLE test.conversation_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,           -- agrupa por sesión
    role VARCHAR(10) NOT NULL,          -- 'user' | 'model'
    agent_name VARCHAR(50),             -- 'sales' | 'booking' | 'general'
    message_text TEXT NOT NULL,         -- contenido
    tool_calls JSONB,                   -- herramientas usadas
    created_at TIMESTAMP DEFAULT NOW()
);

-- TABLA 2: agent_memory_blocks (sesión)
CREATE TABLE test.agent_memory_blocks (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    block_label VARCHAR(100) NOT NULL,  -- "product_interest", "budget", etc.
    block_value TEXT NOT NULL,          -- contenido LLM-extracted
    priority INTEGER CHECK (0 <= priority <= 10),
    agent_scope VARCHAR(50),            -- "shared", "sales", "booking", "general"
    created_at TIMESTAMP DEFAULT NOW()
);

-- TABLA 3: user_memory_blocks (cross-session)
CREATE TABLE test.user_memory_blocks (
    customer_email VARCHAR(255) PRIMARY KEY,  -- PK
    block_label VARCHAR(100) NOT NULL,
    block_value TEXT NOT NULL,
    priority INTEGER CHECK (0 <= priority <= 10),
    source_session_id UUID,             -- para auditoria
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TABLA 4: agent_context_transfers (auditoria handoff)
CREATE TABLE test.agent_context_transfers (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    from_agent VARCHAR(50) NOT NULL,    -- 'sales', 'booking', etc.
    to_agent VARCHAR(50) NOT NULL,
    transfer_reason TEXT,               -- por qué ocurrió handoff
    memory_blocks_transferred INTEGER,  -- cantidad de blocks
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Configuración Crítica

### Variables de Entorno (client_mcp/.env)

```bash
# Google AI Configuration
GOOGLE_API_KEY=gsk_...                    # API key para Gemini
MODEL=gemini-2.5-flash                    # Modelo a usar
TEMPERATURE=0.2                           # Baja variabilidad (0-2)
MAX_OUTPUT_TOKENS=2048                    # Tokens máximos

# MCP Server Connection
MCP_BASE_URL=http://localhost:8009/mcp    # URL servidor
MCP_TIMEOUT=30                            # Timeout segundos

# Database (DEBE COINCIDIR CON mcp_server)
DATABASE_URL=postgresql://mcp_user:mcp_password@localhost:5434/mcpdb
SCHEMA_NAME=test

# Feature Flags
ENABLE_AGENT_ROUTING=true                 # Activa multi-agente
ENABLE_MEMORY_PERSISTENCE=true
LOG_LEVEL=INFO
```

### Variables de Entorno (mcp_server/.env)

```bash
# Database (DEBE COINCIDIR CON client_mcp)
DATABASE_URL=postgresql://mcp_user:mcp_password@localhost:5434/mcpdb
SCHEMA_NAME=test

# Google AI (para embeddings y semantic extraction)
GOOGLE_API_KEY=gsk_...
EMBEDDING_MODEL=gemini-embedding-001

# Server Configuration
DEBUG=true
LOG_LEVEL=INFO
```

### Validación Crítica

```
PUNTO CRÍTICO 1: DATABASE_URL
- client_mcp/.env DATABASE_URL = mcp_server/.env DATABASE_URL
- Si no coinciden → Memory no sincroniza entre cliente y servidor

PUNTO CRÍTICO 2: SCHEMA_NAME
- client_mcp/.env SCHEMA_NAME = mcp_server/.env SCHEMA_NAME
- Si no coinciden → Consultas SQL fallan

PUNTO CRÍTICO 3: MCP_BASE_URL
- Client debe conocer dónde está el servidor
- Formato: http://host:puerto/mcp
- Si es incorrecto → "Connection refused"

PUNTO CRÍTICO 4: GOOGLE_API_KEY
- Tanto cliente como servidor necesitan key válida
- Cliente: para Gemini API (agentes)
- Servidor: para embeddings + semantic extraction

✅ VALIDACIÓN
Las siguientes líneas deben retornar sin errores:

# 1. Verificar conexión DB
psql -c "SELECT 1" $DATABASE_URL

# 2. Verificar schema
psql -c "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'test')" $DATABASE_URL

# 3. Verificar Google API
curl https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY | jq

# 4. Verificar MCP server
curl http://localhost:8009/health | jq .status
```

---

## Startup e Inicialización

### Paso 1: Iniciar Servidor MCP

```bash
# Terminal 1
cd /home/javort/alfredo/MCP-Server
python -m mcp_server.server --port 8009
```

**Output esperado**:
```
INFO:mcp_server.utils.logger:Starting REFACTORED MCP server with transport: streamable-http
INFO:mcp_server.utils.logger:Protocol version support: ...
INFO:mcp_server.utils.logger:REFACTORED MCP server accessible at http://0.0.0.0:8009/mcp
INFO:mcp_server.utils.logger:✅ Health check endpoint available at http://0.0.0.0:8009/health
```

**Verificar**:
```bash
curl http://localhost:8009/health | jq .status
# Output: "healthy"
```

### Paso 2: Iniciar Cliente MCP

```bash
# Terminal 2
cd /home/javort/alfredo/MCP-Server
python -m client_mcp
```

**Flujo de inicialización**:
```
🚀 Lab01-MCP - Multi-Agent Sales & Booking System
================================================== 
Mode: MULTI-AGENT
==================================================

💾 Sistema de Memoria Persistente
=================================
Para habilitar memoria persistente entre sesiones, ingresa tu email.
Presiona Enter para continuar sin memoria persistente.
=================================

📧 Tu email (opcional): john@example.com
✅ Memoria habilitada para: john@example.com

[Iniciando...]
Tu mensaje: _
```

### Paso 3: Usar el Sistema

```
Tu mensaje: Quiero comprar un laptop gaming
[Agent Router clasifica: SALES]
[SalesAgent procesa...]
[Genera function_call: search(query="laptop gaming")]
[MCP Server busca en PostgreSQL]
[Retorna productos: Dell XPS, HP Gaming...]
Te encontré estos laptops gaming:
- Dell XPS 15: $2000
- HP Gaming Laptop: $1200
¿Te interesa alguno?

Tu mensaje: Sí, quiero el Dell XPS y agendar una demo
[Agent Router clasifica: BOOKING]
[Handoff: SalesAgent → BookingAgent]
[ContextTransferHandler transfiere memory blocks]
[BookingAgent recibe contexto previo]
Perfecto! Vi que te interesa el Dell XPS 15. ¿Cuándo puedes venir a verlo?

Tu mensaje: Mañana a las 10am
[BookingAgent procesa...]
Excelente! He agendado tu demostración para mañana a las 10am. Te hemos enviado una confirmación a john@example.com
```

### Logs en Tiempo Real

```bash
# Terminal 3
tail -f logs/mcp_server.log

# Terminal 4
tail -f logs/client_mcp.log
```

---

## Troubleshooting

### Problema: "Connection refused" al conectar a servidor

```bash
# 1. Verificar que servidor está corriendo
lsof -i :8009
# Debe mostrar: python ... (LISTEN)

# 2. Si no está corriendo
python -m mcp_server.server --port 8009

# 3. Verificar conectividad
curl http://localhost:8009/health
# Debe retornar: {"status": "healthy", ...}
```

### Problema: "Database connection failed"

```bash
# 1. Verificar que PostgreSQL está corriendo
pg_isready -h localhost -p 5434
# Output: localhost:5434 - accepting connections

# 2. Conectar manualmente
psql -h localhost -p 5434 -U mcp_user -d mcpdb

# 3. Verificar variables de entorno
env | grep DATABASE_URL
# Debe mostrar: postgresql://mcp_user:mcp_password@localhost:5434/mcpdb

# 4. Verificar .env files
cat /home/javort/alfredo/MCP-Server/mcp_server/.env | grep DATABASE_URL
cat /home/javort/alfredo/MCP-Server/client_mcp/.env | grep DATABASE_URL
# Deben ser idénticas
```

### Problema: "Tools not discovered"

```bash
# 1. Verificar que servidor tiene herramientas registradas
curl -s -X POST http://localhost:8009/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }' | jq '.result.tools | length'
# Debe retornar: número > 0

# 2. Si retorna error, revisar logs del servidor
tail -20 logs/mcp_server.log
# Buscar: "product_handlers.init()"
```

### Problema: "Missing extensions: pg_trgm"

```bash
# 1. Conectar a base de datos
psql -h localhost -p 5434 -U mcp_user -d mcpdb

# 2. Crear extensiones
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS vector;

# 3. Verificar
SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'unaccent', 'vector');
# Output: pg_trgm | unaccent | vector
```

### Problema: "Schema does not exist"

```bash
# 1. Verificar que schema existe
psql -h localhost -p 5434 -U mcp_user -d mcpdb \
  -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'test';"

# 2. Si no existe, crear
psql -h localhost -p 5434 -U mcp_user -d mcpdb \
  -c "CREATE SCHEMA IF NOT EXISTS test;"

# 3. Crear tablas (si no existen)
# Ver: SQL/01_ddl/memory/ para scripts DDL
```

---

## Resumen de Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENTE MCP                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ AgentOrchestrator.run_interactive()              │  │
│  │  - Lee: input("Tu mensaje:")                     │  │
│  │  - AgentRouter: clasifica intent                 │  │
│  │  - Selecciona: agente especializado              │  │
│  │  - MCPConnector: llama herramientas servidor     │  │
│  │  - Gemini API: reasoning + generación            │  │
│  │  - Print: respuesta natural                      │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP JSON-RPC 2.0
                   │ POST /mcp
                   ↓
┌─────────────────────────────────────────────────────────┐
│                   SERVIDOR MCP                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ FastMCP (Anthropic SDK)                          │  │
│  │  - Recibe: JSON-RPC 2.0 requests                │  │
│  │  - Delega: ProductHandler.search(), etc.         │  │
│  │  - PostgreSQL: búsqueda productos                │  │
│  │  - MemoryManager: persiste contexto              │  │
│  │  - Retorna: JSON response                        │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │ JSON response
                   ↓
                AGENTES GEMINI
                (Reasoning +
                 Function Calls)
```

**Tecnologías Clave**:
- Client: Python async/await + Gemini API
- Server: FastMCP + uvicorn + PostgreSQL
- Agentes: Google GenAI (Gemini 2.5 Flash)
- Memoria: PostgreSQL (persistente) + RAM (cache)
- Búsqueda: pg_trgm (fuzzy) + embeddings (semántica)

**Estado**: Funcional y listo para producción

