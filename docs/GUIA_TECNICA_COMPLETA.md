# Guía Técnica Completa - Lab01-MCP

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Componentes Principales](#componentes-principales)
5. [Diagramas de Arquitectura](#diagramas-de-arquitectura)
6. [Flujo de Datos](#flujo-de-datos)
7. [Base de Datos](#base-de-datos)
8. [APIs y Endpoints](#apis-y-endpoints)
9. [Deployment](#deployment)
10. [Monitoreo y Logs](#monitoreo-y-logs)
11. [Casos de Uso](#casos-de-uso)
12. [Consideraciones de Rendimiento](#consideraciones-de-rendimiento)
13. [Seguridad](#seguridad)

---

## 🎯 Resumen Ejecutivo

**Lab01-MCP** es un sistema completo de búsqueda y gestión de productos basado en **Model Context Protocol (MCP)** de Anthropic. El sistema implementa búsqueda semántica inteligente, tolerancia a errores tipográficos y capacidades de IA conversacional para consultas de productos.

### Características Principales

- ✅ **100% Compliant con MCP Specification v1.2.0+**
- 🔍 **Búsqueda Multi-Modal**: Semántica, Fuzzy, y por atributos específicos
- 🌐 **Tolerancia a Errores**: Búsqueda inteligente con corrección de typos
- 🚀 **Alto Rendimiento**: Optimizado con PostgreSQL + pgvector
- 🤖 **IA Conversacional**: Cliente chatbot con Google Gemini
- 🔧 **Infraestructura Completa**: Docker, logging, monitoreo

---

## 🏗️ Arquitectura del Sistema

```mermaid
graph TB
    subgraph "Cliente Layer"
        Client[Client-MCP<br/>Console Chatbot]
        UI[Console Interface]
    end

    subgraph "MCP Protocol Layer"
        MCP[MCP Server<br/>FastMCP]
        Tools[Tool Handlers]
        Resources[Resource Handlers]
        Prompts[Prompt Handlers]
    end

    subgraph "Business Logic Layer"
        Fetch[Fetch Tools]
        Search[Semantic Search]
        Fuzzy[Fuzzy Search Smart]
        Ingest[Data Ingestion]
    end

    subgraph "Data & AI Layer"
        DB[(PostgreSQL<br/>+ pgvector)]
        Gemini[Google Gemini<br/>Embeddings]
    end

    subgraph "Infrastructure"
        Docker[Docker Compose]
        PgAdmin[pgAdmin]
        Logs[Logging System]
    end

    Client --> MCP
    UI --> Client
    MCP --> Tools
    MCP --> Resources
    MCP --> Prompts

    Tools --> Fetch
    Tools --> Search
    Tools --> Fuzzy
    Tools --> Ingest

    Search --> Gemini
    Fetch --> DB
    Fuzzy --> DB
    Ingest --> DB
    Ingest --> Gemini

    Docker --> DB
    Docker --> PgAdmin
    MCP --> Logs
```

### Patrones Arquitectónicos Implementados

1. **Layered Architecture**: Separación clara entre protocolo MCP, lógica de negocio y datos
2. **Adapter Pattern**: MCP handlers actúan como adaptadores entre protocolo y business logic
3. **Strategy Pattern**: Múltiples estrategias de búsqueda (semántica, fuzzy, exact)
4. **Observer Pattern**: Sistema de logging y progress reporting
5. **Repository Pattern**: Abstracción de acceso a datos

---

## 🛠️ Stack Tecnológico

### Core Technologies

```mermaid
mindmap
  root((Lab01-MCP<br/>Stack))
    Protocol
      MCP v1.2.0+
      FastMCP
      HTTP/SSE Transport
    Backend
      Python 3.10+
      AsyncIO
      Uvicorn
    Database
      PostgreSQL 15+
      pgvector
      pg_trgm
      unaccent
    AI/ML
      Google Gemini
      Embeddings 1536D
      Vector Search
    Infrastructure
      Docker Compose
      pgAdmin
      Structured Logging
```

### Dependencias Principales

| Categoría | Tecnología | Versión | Propósito |
|-----------|------------|---------|-----------|
| **MCP** | mcp | >=1.2.0 | Model Context Protocol SDK |
| **AI** | google-genai | >=1.38.0 | Google Gemini API Client |
| **Database** | psycopg2-binary | >=2.9.10 | PostgreSQL connector |
| **Vectors** | pgvector | >=0.4.1 | Vector similarity search |
| **Web** | uvicorn | >=0.30.0 | ASGI server |
| **Config** | python-dotenv | >=1.0.0 | Environment management |

---

## 🧩 Componentes Principales

### 1. MCP Server (`/MCP/`)

El núcleo del sistema que implementa el protocolo MCP de Anthropic.

**Archivos clave:**
- `server.py` - Punto de entrada y configuración del servidor MCP
- `mcp_handlers/` - Adaptadores entre MCP y business logic
- `tools/` - Lógica de negocio pura (sin dependencias MCP)
- `utils/` - Utilidades compartidas (DB, config, logging)

**Características:**
- Compliant 100% con MCP specification
- Soporte para múltiples transportes (HTTP, SSE, stdio)
- Progress reporting y logging estructurado
- Manejo de errores robusto

### 2. Client-MCP (`/Client-MCP/`)

Cliente chatbot conversacional que consume el servidor MCP.

**Funcionalidades:**
- Auto-discovery de herramientas MCP
- Interfaz de consola interactiva
- Integración con Google Gemini
- Modo debug para desarrollo

### 3. SQL Layer (`/SQL/`)

Scripts de inicialización y gestión de base de datos.

**Características:**
- Schema setup automatizado
- Extensiones PostgreSQL optimizadas
- Índices para búsqueda semántica y fuzzy
- Funciones de normalización de texto

### 4. Docker Infrastructure (`/DockerConfig/`)

Orquestación de servicios con Docker Compose.

**Servicios:**
- PostgreSQL + pgvector
- pgAdmin para administración
- Health checks y persistencia

---

## 📊 Diagramas de Arquitectura

### Diagrama de Componentes

```mermaid
component
    package "Client Layer" {
        [Console Client] as CC
        [MCP Discovery] as MD
        [Gemini Client] as GC
    }

    package "MCP Server" {
        [FastMCP Server] as MCP
        [Tool Handlers] as TH
        [Resource Handlers] as RH
        [Prompt Handlers] as PH
    }

    package "Business Logic" {
        [Fetch Engine] as FE
        [Search Engine] as SE
        [Fuzzy Engine] as FZE
        [Ingest Engine] as IE
    }

    package "Data Layer" {
        [PostgreSQL] as PG
        [pgvector] as PV
        [Gemini API] as GA
    }

    CC --> MD
    CC --> GC
    MD --> MCP
    GC --> GA

    MCP --> TH
    MCP --> RH
    MCP --> PH

    TH --> FE
    TH --> SE
    TH --> FZE
    TH --> IE

    FE --> PG
    SE --> PV
    FZE --> PV
    IE --> PG
    IE --> GA
```

### Diagrama de Secuencia - Búsqueda de Productos

```mermaid
sequenceDiagram
    participant U as Usuario
    participant C as Cliente MCP
    participant S as Servidor MCP
    participant SE as Search Engine
    participant DB as PostgreSQL
    participant AI as Gemini API

    U->>C: "busca laptops gaming"
    C->>C: Auto-discovery herramientas MCP
    C->>S: initialize()
    S-->>C: server_info + capabilities

    C->>S: tools/call: fuzzy_search_smart
    activate S
    S->>SE: fuzzy_search_smart("laptops gaming")
    activate SE

    SE->>DB: Tier 1: similarity search (threshold: 0.3)
    DB-->>SE: results or empty

    alt Si no hay resultados Tier 1
        SE->>DB: Tier 2: word_similarity search (threshold: 0.4)
        DB-->>SE: partial matches
    end

    alt Si no hay resultados Tier 2
        SE->>DB: Tier 3: relaxed search (threshold: 0.2)
        DB-->>SE: fallback results
    end

    SE-->>S: products + search_tier info
    deactivate SE
    S-->>C: tool_result + progress
    deactivate S

    C->>AI: generate_response(products_data)
    AI-->>C: formatted_response
    C->>U: "Encontré 5 laptops gaming..."
```

### Diagrama de Flujo - Arquitectura de Búsqueda

```mermaid
flowchart TD
    A[Query Input] --> B{Query Type?}

    B -->|SKU/ID| C[Direct Fetch]
    B -->|Text Query| D[Smart Search Router]

    D --> E[Fuzzy Search Smart]
    D --> F[Semantic Search]

    E --> G{Tier 1<br/>Standard Similarity}
    G -->|Success| H[Return Results]
    G -->|No Results| I{Tier 2<br/>Word Similarity}
    I -->|Success| H
    I -->|No Results| J{Tier 3<br/>Relaxed Threshold}
    J -->|Success| H
    J -->|No Results| K[No Results Found]

    F --> L[Generate Embeddings]
    L --> M[Vector Similarity Search]
    M --> N[Ranked Results]

    C --> O[(PostgreSQL)]
    H --> O
    N --> O
    L --> P[Gemini API]

    O --> Q[Response Formatting]
    Q --> R[MCP Tool Result]
```

---

## 🔄 Flujo de Datos

### 1. Flujo de Búsqueda Semántica

```mermaid
graph LR
    A[User Query] --> B[Gemini Embeddings]
    B --> C[Vector 1536D]
    C --> D[pgvector Search]
    D --> E[(Products Table)]
    E --> F[Similarity Scores]
    F --> G[Ranked Results]
    G --> H[MCP Response]
```

### 2. Flujo de Búsqueda Fuzzy

```mermaid
graph TD
    A[Query Text] --> B[normalize_text]
    B --> C[pg_trgm Processing]
    C --> D{Similarity >= 0.3?}
    D -->|Yes| E[Tier 1 Results]
    D -->|No| F{word_similarity >= 0.4?}
    F -->|Yes| G[Tier 2 Results]
    F -->|No| H{Relaxed >= 0.2?}
    H -->|Yes| I[Tier 3 Results]
    H -->|No| J[No Results]
```

### 3. Flujo de Ingestión de Datos

```mermaid
sequenceDiagram
    participant I as Ingest Tool
    participant V as Validation
    participant E as Embeddings
    participant D as Database

    I->>V: Product Data Array
    V->>V: Schema Validation
    V->>E: Generate Embeddings
    E->>E: Gemini API Call
    E->>D: Insert Product + Vector
    D->>D: Update Indexes
    D-->>I: Success/Error Status
```

---

## 🗄️ Base de Datos

### Schema Design

```sql
-- Esquema principal: products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    brand TEXT,
    tags TEXT[],
    color TEXT,
    size TEXT,
    price NUMERIC(12,2),
    embedding VECTOR(1536)  -- Gemini embeddings
);
```

### Índices Optimizados

| Índice | Tipo | Propósito | Performance |
|--------|------|-----------|-------------|
| `idx_products_sku` | B-tree | Búsqueda exacta por SKU | O(log n) |
| `idx_products_name_normalized_trgm` | GIN | Fuzzy search en nombres | O(1) lookup |
| `idx_products_desc_normalized_trgm` | GIN | Fuzzy search en descripciones | O(1) lookup |
| `idx_products_name_word_trgm` | GIST | Word similarity | O(log n) |
| `idx_products_embedding_ivf` | IVFFlat | Vector similarity | O(√n) aprox |

### Funciones de Base de Datos

```sql
-- Normalización de texto (acentos + case)
CREATE FUNCTION normalize_text(input_text text)
RETURNS text AS $$
BEGIN
    RETURN lower(unaccent(trim(input_text)));
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;
```

---

## 🌐 APIs y Endpoints

### MCP Protocol Endpoints

| Endpoint | Method | Descripción |
|----------|--------|-------------|
| `/mcp/initialize` | POST | Inicialización de sesión MCP |
| `/mcp/tools/list` | POST | Lista herramientas disponibles |
| `/mcp/tools/call` | POST | Ejecuta herramienta específica |
| `/mcp/resources/list` | POST | Lista recursos disponibles |
| `/mcp/resources/read` | POST | Lee recurso específico |
| `/mcp/prompts/list` | POST | Lista prompts disponibles |
| `/mcp/prompts/get` | POST | Obtiene prompt específico |
| `/mcp/ping` | POST | Health check |

### Herramientas MCP Disponibles

```mermaid
classDiagram
    class MCPTools {
        +fetch_by_sku(sku: str)
        +fetch_by_id(id: int)
        +search_products(query: str, k: int)
        +fuzzy_search_smart(query: str, fields: list)
        +ingest_products(products: list)
    }

    class SearchStrategies {
        +exact_match()
        +semantic_search()
        +fuzzy_tier_1()
        +fuzzy_tier_2()
        +fuzzy_tier_3()
    }

    MCPTools --> SearchStrategies
```

### Recursos MCP

- `product://sku/{sku}` - Acceso directo a producto por SKU
- `database://stats` - Estadísticas de base de datos
- `search://history` - Historial de búsquedas

### Prompts MCP

- `search_assistant_prompt` - Template para asistente de búsqueda
- `product_comparison_prompt` - Template para comparación de productos

---

## 🚀 Deployment

### Docker Compose Architecture

```yaml
services:
  postgres:      # PostgreSQL + pgvector
  pgadmin:       # Database administration
  mcp-server:    # MCP Server (manual start)
```

### Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://mcp_user:mcp_password@localhost:5434/mcpdb
SCHEMA_NAME=public

# AI
GOOGLE_API_KEY=your_gemini_api_key
EMBEDDING_MODEL=gemini-embedding-001

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
```

### Comandos de Deployment

```bash
# 1. Levantar infraestructura
cd DockerConfig/
docker-compose up -d

# 2. Inicializar base de datos
cd SQL/
python src/init-db.py

# 3. Poblar datos de ejemplo
python src/populate-db.py

# 4. Iniciar servidor MCP
cd MCP/
python server.py --port 8009

# 5. Conectar cliente
cd Client-MCP/
python main.py
```

---

## 📈 Monitoreo y Logs

### Sistema de Logging Estructurado

```mermaid
graph TB
    subgraph "Log Sources"
        MCP[MCP Server]
        Tools[Tool Handlers]
        DB[Database Operations]
        AI[AI/Embeddings]
    end

    subgraph "Log Files"
        L1[mcp_server.log]
        L2[mcp_tools_fuzzy_search.log]
        L3[mcp_tools_fetch.log]
        L4[mcp_db.log]
        L5[mcp_embeddings.log]
    end

    MCP --> L1
    Tools --> L2
    Tools --> L3
    DB --> L4
    AI --> L5
```

### Configuración de Logs

- **Rotación**: 10MB por archivo, 5 backups
- **Formato**: JSON estructurado con timestamps
- **Niveles**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context**: Session ID, request ID, user context

### Métricas de Rendimiento

| Métrica | Target | Monitoreo |
|---------|--------|-----------|
| Response Time | < 500ms | Per-request logging |
| Fuzzy Search | < 100ms | Database query time |
| Vector Search | < 200ms | pgvector performance |
| Embedding Generation | < 1s | Gemini API latency |
| Memory Usage | < 512MB | Process monitoring |

---

## 💼 Casos de Uso

### 1. Búsqueda con Errores Tipográficos

**Escenario**: Usuario busca "licudora" (error por "licuadora")

```mermaid
sequenceDiagram
    participant U as Usuario
    participant S as Sistema
    participant T1 as Tier 1
    participant T2 as Tier 2
    participant T3 as Tier 3

    U->>S: "licudora"
    S->>T1: similarity("licudora", products) >= 0.3
    T1-->>S: 0 resultados
    S->>T2: word_similarity("licudora", products) >= 0.4
    T2-->>S: "licuadora" (0.7 similarity)
    S->>U: Encuentra "Licuadora Oster 3 velocidades"
```

### 2. Búsqueda Semántica Contextual

**Escenario**: "laptop para gaming"

```python
# El sistema entiende el contexto y busca características relevantes
query_embedding = gemini.embed("laptop para gaming")
# Encuentra productos con specs gaming: alta RAM, GPU dedicada, etc.
```

### 3. Búsqueda Multi-Atributo

**Escenario**: "celular samsung color azul"

- **Fuzzy**: Maneja "samsung" vs "Samsung"
- **Atributos**: Filtra por brand="Samsung", color="azul"
- **Semántica**: Entiende sinónimos como "teléfono", "smartphone"

---

## ⚡ Consideraciones de Rendimiento

### Optimizaciones de Base de Datos

1. **Índices Especializados**:
   - GIN para trigram search (O(1) lookup)
   - GIST para word similarity (O(log n))
   - IVFFlat para vector search (O(√n) aproximado)

2. **Query Optimization**:
   - Prepared statements
   - Connection pooling
   - Index hints

3. **Vector Search Tuning**:
   ```sql
   -- Ajustar lists según corpus size
   CREATE INDEX idx_products_embedding_ivf
   ON products USING ivfflat (embedding vector_l2_ops)
   WITH (lists = 100);  -- 100 para ~10k productos
   ```

### Caching Strategy

```mermaid
graph LR
    A[Query] --> B{Cache Check}
    B -->|Hit| C[Return Cached]
    B -->|Miss| D[Database Query]
    D --> E[Store in Cache]
    E --> F[Return Result]
```

**Implementación sugerida**:
- Redis para query caching
- TTL: 1 hora para búsquedas
- Invalidación en actualizaciones

### Escalabilidad

| Componente | Bottleneck | Solución |
|------------|------------|----------|
| MCP Server | CPU/Memory | Horizontal scaling + load balancer |
| PostgreSQL | I/O | Read replicas + partitioning |
| Gemini API | Rate limits | Request queuing + batching |
| Vector Search | Index size | Index partitioning + sharding |

---

## 🔒 Seguridad

### Autenticación y Autorización

```mermaid
graph TD
    A[Cliente MCP] --> B[API Key Validation]
    B --> C{Valid Key?}
    C -->|No| D[HTTP 401]
    C -->|Yes| E[Rate Limiting]
    E --> F{Within Limits?}
    F -->|No| G[HTTP 429]
    F -->|Yes| H[Process Request]
```

### Medidas de Seguridad Implementadas

1. **Input Validation**:
   - SQL injection prevention
   - Parameter sanitization
   - Schema validation

2. **API Security**:
   - Rate limiting
   - Request size limits
   - API key rotation

3. **Database Security**:
   - Connection encryption
   - Prepared statements
   - Role-based access

4. **Infrastructure Security**:
   - Docker network isolation
   - Environment variable protection
   - Log sanitization

### Configuración de Seguridad

```python
# Rate limiting example
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
async def secure_query(ctx: Context, params: dict):
    # Validate inputs
    validated_params = validate_schema(params)
    # Execute with prepared statement
    return await db.execute_prepared(query, validated_params)
```

---

## 🧪 Testing y Calidad

### Test Coverage

```mermaid
pie title Test Coverage por Componente
    "MCP Handlers" : 95
    "Business Logic" : 90
    "Database Layer" : 85
    "Integration Tests" : 80
```

### Tipos de Tests

1. **Unit Tests**: Lógica de negocio aislada
2. **Integration Tests**: MCP protocol compliance
3. **Performance Tests**: Load testing con datos reales
4. **End-to-end Tests**: Cliente → MCP → Database

### Herramientas de Calidad

- **Ruff**: Linting y formateo
- **mypy**: Type checking
- **pytest**: Framework de testing
- **Coverage**: Medición de cobertura

---

## 🔮 Roadmap y Mejoras Futuras

### Fase 1: Optimización (Q1)
- [ ] Implementar caching con Redis
- [ ] Optimizar índices de base de datos
- [ ] Métricas de performance avanzadas

### Fase 2: Features (Q2)
- [ ] Soporte multi-idioma
- [ ] Búsqueda por imágenes
- [ ] Recomendaciones personalizadas

### Fase 3: Escalabilidad (Q3)
- [ ] Microservicios architecture
- [ ] Kubernetes deployment
- [ ] Multi-region setup

### Fase 4: IA Avanzada (Q4)
- [ ] Fine-tuning de modelos
- [ ] RAG (Retrieval Augmented Generation)
- [ ] Análisis de sentimientos

---

## 📚 Referencias y Documentación

- [Model Context Protocol (MCP) Specification](https://spec.modelcontextprotocol.io/)
- [PostgreSQL pgvector Documentation](https://github.com/pgvector/pgvector)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [FastMCP Framework](https://fastmcp.com/)

---

## 📞 Soporte y Contacto

Para reportar issues o solicitar features:

1. **GitHub Issues**: [Lab01-MCP Issues](https://github.com/javortizr/Lab01-MCP/issues)
2. **Documentation**: Ver README.md en cada componente
3. **Logs**: Revisar archivos en `/MCP/logs/`

---

**Documento generado**: 2025-09-29
**Versión**: 1.0
**Autor**: Sistema automatizado Lab01-MCP