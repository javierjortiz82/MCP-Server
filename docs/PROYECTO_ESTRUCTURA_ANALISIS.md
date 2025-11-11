# ANALISIS ESTRUCTURAL DEL PROYECTO Lab01-MCP

## RESUMEN EJECUTIVO

**Tipo de Proyecto**: Sistema Multi-Agente conversacional basado en MCP (Model Context Protocol)  
**Arquitectura**: Backend puro (sin frontend tradicional)  
**Lenguaje**: Python 3.12  
**AI Engine**: Google Gemini 2.5 Flash  
**Protocolo**: MCP (Anthropic's Model Context Protocol)  
**Base de Datos**: PostgreSQL con búsqueda semántica y fuzzy search

---

## CLAVE 1: NO TIENE FRONTEND (React/Next.js/Material-UI)

Este proyecto **NO contiene**:
- Componentes React o Next.js
- Material-UI, shadcn UI, o cualquier librería UI
- Interfaz gráfica web
- CSS o estilos (excepto para reportes HTML de test coverage)

**Tiene**: Backend conversacional que retorna texto formateado para ser consumido por clientes MCP externos.

---

## ARQUITECTURA DE CAPAS

```
┌──────────────────────────────────────┐
│  CLIENTE MCP (client_mcp/)           │
│  - Agent Orchestrator                │
│  - Conversation Manager              │
│  - Response Processor/Validator      │
│  - Tool Executor                     │
└──────────────────────────────────────┘
           ↕ (HTTP REST)
┌──────────────────────────────────────┐
│  AGENTES (agent/src/)                │
│  - Router Agent (clasificación)      │
│  - Sales Agent (búsqueda productos)  │
│  - Booking Agent (reservas)          │
│  - General Agent (FAQ)               │
└──────────────────────────────────────┘
           ↕ (MCP Protocol)
┌──────────────────────────────────────┐
│  MCP SERVER (mcp_server/)            │
│  - Product Tools (fetch, search)     │
│  - Booking Tools                     │
│  - Resource Handlers                 │
│  - FastMCP Protocol Handler          │
└──────────────────────────────────────┘
           ↕ (SQL)
┌──────────────────────────────────────┐
│  DATABASE (PostgreSQL)               │
│  - products + embeddings             │
│  - bookings                          │
│  - pagination contexts               │
└──────────────────────────────────────┘
```

---

## COMPONENTES PRINCIPALES

### 1. Cliente MCP (`client_mcp/`)

| Archivo | Función |
|---------|---------|
| `core/agent_orchestrator.py` | Orquesta agentes, routing |
| `core/conversation_manager.py` | Gestión de contexto conversacional |
| `core/response_processor.py` | Post-procesa respuestas Gemini |
| `core/response_validator.py` | Valida SKUs (anti-alucinación) |
| `core/tool_executor.py` | Ejecuta herramientas MCP |
| `core/function_call_handler.py` | Maneja function calls de Gemini |
| `core/debug_formatter.py` | Formatea información debug |
| `core/pagination_manager.py` | Gestiona paginación de resultados |
| `observability/metrics.py` | Métricas de ejecución de herramientas |

**Archivos de Configuración**:
- `config/settings.py`: Configuración Pydantic v2 (Gemini, MCP, logging)
- `.env`: Variables de entorno

### 2. Sistemas de Agentes (`agent/src/`)

**PromptManager** (`multi_agent/prompt_manager.py`):
- Jinja2 OBLIGATORIO para templates
- Carga prompts desde `/prompts/templates/`
- A/B Testing integrado (determinístico por user_id)
- Soporte multilingüe automático

**Cuatro Agentes**:

#### AgentRouter (`agent_router.py`)
```python
Intent(Enum):
    SALES = "sales"       # Búsqueda de productos
    BOOKING = "booking"   # Reservas
    GENERAL = "general"   # Preguntas generales
```
- Temperatura = 0 (determinístico)
- Usa prompts externos via PromptManager
- Memory integration opcional

#### SalesAgent (`sales_agent.py`)
- Busca productos: semántica, fuzzy, exacta
- Paginación inteligente (4 o 6 items)
- A/B Testing para tamaño paginación

#### BookingAgent (`booking_agent.py`)
- Gestiona reservas
- A/B Testing: confirmación directa vs resumen

#### GeneralAgent (`general_agent.py`)
- Preguntas frecuentes
- A/B Testing: respuestas detalladas vs concisas

### 3. MCP Server (`mcp_server/`)

**Herramientas Disponibles** (`mcp_handlers/product_handlers.py`):

| Herramienta | Velocidad | Caso de Uso |
|-------------|-----------|-----------|
| `fetch_by_sku` | ~9ms | SKU exacto |
| `fuzzy_search_smart` | ~10.8ms | Nombre con typos/categoría |
| `search_products` | ~490ms | Búsqueda semántica |
| `fetch_by_id` | ~9ms | ID exacto |

**fuzzy_search_smart - Estrategia de 4 Tiers**:
```
Tier 1: Trigram similarity (threshold=0.3)
   ↓ (si falla)
Tier 2: Word similarity ponderada (threshold=0.4)
   - name: 2.0 (prioritario)
   - category: 1.5
   - description: 1.0
   - brand: 1.0
   ↓ (si falla)
Tier 2.5: Token-based (posición ponderada)
   ↓ (si falla)
Tier 3: Fallback relaxed (threshold=0.2)
```

**Características**:
- Insensible a acentos (cámara = camara)
- Insensible a mayúsculas/minúsculas
- Categorías: Computación, Audio, Gaming, Hogar, etc.

### 4. Gestión de Prompts (`prompts/`)

**Estructura**:
```
prompts/
├── templates/
│   ├── base/                    # Gemini multilingual
│   │   ├── router_classification.jinja2
│   │   ├── sales_agent/
│   │   ├── booking_agent/
│   │   └── general_agent/
│   ├── booking_agent/modules/   # Módulos especializados
│   └── sales_agent/modules/
├── data/
│   ├── services.yaml
│   ├── business_info.yaml
│   └── policies.yaml
└── config/
    └── prompt_versions.yaml     # Versionado + A/B testing
```

**PromptManager Métodos**:
```python
get_router_prompt(version, user_lang)
get_sales_prompt(pagination_page_size, user_id)     # A/B testing
get_booking_prompt(show_pre_confirmation_summary, user_id)  # A/B testing
get_general_prompt(response_detail_level, user_id)  # A/B testing
```

---

## FORMATOS DE RESPUESTA

### Respuesta de Producto
```json
{
  "id": 1,
  "sku": "COMP-0038",
  "name": "Gaming Laptop Pro",
  "description": "...",
  "category": "Computación",
  "brand": "TechBrand",
  "tags": ["gaming", "laptop"],
  "color": "Negro",
  "size": "15.6 pulgadas",
  "price": 1299.99,
  "max_similarity": 0.95,
  "search_tier": "standard"
}
```

### Respuesta de Chatbot Formateada
```
---
Hola! Te ayudaré a encontrar la laptop perfecta...

1. **Gaming Laptop Pro** (COMP-0038)
   - Precio: $1,299
   - GPU: RTX 4060

---
🔧 **DEBUG INFO**
• Tool: search_products
• Tiempo: 145.32ms
• Resultados: 2 encontrados
• Estado: ✅ Éxito
```

---

## FLUJO DE PROCESAMIENTO (Ejemplo: "Busco laptop gaming")

```
1. User Query
   ↓
2. Agent Router
   Clasifica: SALES intent
   ↓
3. PromptManager
   Carga: base/sales_agent/sales_agent.jinja2
   Inyecta: contexto MCP, paginación=4
   ↓
4. Gemini 2.5 Flash
   Recibe system prompt + query
   Planifica: Usar search_products
   ↓
5. Function Call
   {"name": "search_products", "arguments": {"query": "laptop gaming", "k": 5}}
   ↓
6. MCP Server Tool Execution
   Genera embedding de query
   Busca vector similarity en BD
   Retorna top 5 resultados
   ↓
7. ResponseProcessor
   Valida SKUs ✓
   Limpia artefactos JSON ✓
   Agrega debug info ✓
   ↓
8. Respuesta Formateada
   Al usuario
```

---

## CONFIGURACIÓN

### Google Gemini (client_mcp/config/settings.py)
```python
MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 2048
TOP_K = 40
TOP_P = 0.95
```

### MCP Server
```python
MCP_HOST = "localhost"
MCP_PORT = 8009
```

### A/B Testing (prompts/config/prompt_versions.yaml)
```yaml
ab_testing:
  enabled: false
  experiments:
    - name: "sales_pagination_6_products"
      agent: "sales"
      version_a_params: {pagination_page_size: 4}
      version_b_params: {pagination_page_size: 6}
```

---

## TECNOSTACK

**Backend**:
- Python 3.12
- Google Gemini AI (2.5 Flash)
- MCP (Model Context Protocol) by Anthropic
- FastMCP (FastAPI-based MCP)

**Base de Datos**:
- PostgreSQL
  - pg_trgm (trigram search para fuzzy matching)
  - Vector embeddings (Gemini embeddings)
  - UNaccent (búsqueda insensible a acentos)

**Librerías**:
```
google-genai>=0.4.0           # Gemini API
mcp>=1.0.0                    # MCP Protocol
fastmcp>=0.5.0                # MCP Server
pydantic>=2.0.0               # Validación
pydantic-settings>=2.0.0      # Settings management
psycopg2-binary>=2.9.0        # PostgreSQL driver
jinja2>=3.1.0                 # Template engine
pyyaml>=6.0                   # YAML parser
```

**NO utiliza**:
- React, Next.js
- Material-UI, shadcn UI
- CSS frameworks (Tailwind, etc.)

---

## CARACTERÍSTICAS CLAVE

### 1. Anti-Alucinación
`ResponseValidator` valida que SKUs mencionados existan en BD. Si no, regenera respuesta.

### 2. A/B Testing
Integrado en PromptManager con bucketing determinístico por user_id:
- Sales: paginación 4 vs 6 productos
- Booking: confirmación directa vs resumen
- General: respuestas detalladas vs concisas

### 3. Búsqueda Multi-Estrategia
- **Semántica**: Por necesidad/beneficio (search_products)
- **Fuzzy**: Por nombre con typos (fuzzy_search_smart con 4 tiers)
- **Exacta**: Por SKU (fetch_by_sku)

### 4. Multilingüe
Gemini detecta automáticamente el idioma de la query y responde en ese idioma.

### 5. Paginación Inteligente
Gestiona contexto de búsqueda en BD, permite navegar resultados.

### 6. Observabilidad
- Métricas de ejecución de herramientas
- Debug info formateado
- Logging estructurado

---

## ARCHIVOS PRINCIPALES REFERENCIADOS

**Frontend/Chat Responses**:
- `/home/javort/Lab01-MCP/client_mcp/core/response_processor.py`
- `/home/javort/Lab01-MCP/client_mcp/core/debug_formatter.py`
- `/home/javort/Lab01-MCP/client_mcp/core/response_validator.py`

**API Backend**:
- `/home/javort/Lab01-MCP/mcp_server/server.py`
- `/home/javort/Lab01-MCP/mcp_server/mcp_handlers/product_handlers.py`

**Templates de Chat**:
- `/home/javort/Lab01-MCP/prompts/templates/base/sales_agent/sales_agent.jinja2`
- `/home/javort/Lab01-MCP/prompts/templates/base/booking_agent/booking_agent.jinja2`

**Gestión de Prompts**:
- `/home/javort/Lab01-MCP/agent/src/multi_agent/prompt_manager.py`

**Agentes**:
- `/home/javort/Lab01-MCP/agent/src/multi_agent/agent_router.py`
- `/home/javort/Lab01-MCP/agent/src/multi_agent/sales_agent.py`
- `/home/javort/Lab01-MCP/agent/src/multi_agent/booking_agent.py`

---

## CONCLUSIÓN

Este es un **backend conversacional pure con 4 agentes especializados**, sin interfaz gráfica. Los componentes de "respuesta del chatbot" son:

1. **ResponseProcessor**: Post-procesa salida de Gemini
2. **ResponseValidator**: Valida información (anti-alucinación)
3. **DebugFormatter**: Formatea información de depuración
4. **Templates Jinja2**: Define estructura de respuestas por agente

No hay UI framework - es un sistema backend que espera ser consumido por clientes MCP externos a través de HTTP/MCP protocol.

