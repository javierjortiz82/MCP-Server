# DockerConfig - Docker Configuration

> Production-ready Docker configuration for Lab01-MCP microservices architecture

[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Docker Compose](https://img.shields.io/badge/docker--compose-2.20+-2496ED?logo=docker)](https://docs.docker.com/compose/)

This directory contains Docker configuration files for deploying the Lab01-MCP intelligent sales platform as containerized microservices.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Services](#-services)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Networking](#-networking)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

### ⚠️ IMPORTANT: Two Docker Configurations

This directory provides:
1. **Local Docker Compose** (`docker-compose.yml` in this directory) - PostgreSQL + pgAdmin only (development)
2. **Dockerfiles** for the main project `docker-compose.yml` (production deployment)

---

## 🏗️ Architecture

### Services Architecture Diagram

```mermaid
graph TB
    subgraph External["🌐 External Access"]
        User["👤 Users"]
        Admin["👨‍💼 Administrators"]
    end

    subgraph Production["🚀 Production Stack (Root docker-compose.yml)"]
        direction TB

        subgraph Gateway["Gateway Layer"]
            Nginx["🌐 Nginx<br/>Reverse Proxy<br/>Port: 80/443"]
        end

        subgraph Application["Application Layer"]
            ClientMCP["🤖 Client MCP<br/>Odiseo Bot<br/>Port: Internal"]
            MCPServer["🔌 MCP Server<br/>FastMCP API<br/>Port: 3000"]
            AgentService["🧠 Gemini Agent<br/>AI Service<br/>Port: 8000"]
        end

        subgraph Data["Data Layer"]
            Postgres["💾 PostgreSQL 16<br/>+ pgvector<br/>Port: 5434"]
            Redis["⚡ Redis<br/>Cache Layer<br/>Port: 6379"]
        end

        subgraph Management["Management Layer"]
            PgAdmin["📊 pgAdmin 4<br/>DB Management<br/>Port: 5050"]
        end
    end

    subgraph Local["🛠️ Local Dev Stack (DockerConfig/)"]
        LocalPostgres["💾 PostgreSQL 16<br/>Dev Database<br/>Port: 5434"]
        LocalPgAdmin["📊 pgAdmin 4<br/>Dev UI<br/>Port: 8090"]
    end

    User -->|"HTTP/HTTPS"| Nginx
    Admin -->|"Web UI"| PgAdmin
    Admin -->|"Web UI"| LocalPgAdmin

    Nginx -->|"Route /api"| MCPServer
    Nginx -->|"Route /chat"| ClientMCP

    ClientMCP -->|"MCP Protocol"| MCPServer
    ClientMCP -->|"AI Requests"| AgentService
    ClientMCP -->|"Cache"| Redis

    MCPServer -->|"SQL Queries"| Postgres
    AgentService -->|"Read/Write"| Postgres

    PgAdmin -.->|"Manage"| Postgres
    LocalPgAdmin -.->|"Manage"| LocalPostgres

    style External fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style Production fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    style Gateway fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Application fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style Data fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style Management fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style Local fill:#e0f2f1,stroke:#004d40,stroke-width:2px
```

### Network Topology

```mermaid
graph LR
    subgraph Internet["🌐 Internet"]
        Client[Web Browser]
    end

    subgraph DockerNetwork["🔗 lab01_network (Bridge Network)"]
        direction TB

        subgraph Services["Container Services"]
            nginx[nginx:alpine<br/>container_name: nginx]
            client[client-mcp<br/>Python 3.11]
            mcp[mcp-server<br/>FastMCP]
            agent[gemini-agent<br/>Python 3.11]
            postgres[(postgres:16<br/>+ pgvector)]
            redis[redis:alpine]
            pgadmin[pgadmin4]
        end

        nginx -->|"Internal DNS<br/>mcp-server:3000"| mcp
        nginx -->|"Internal DNS<br/>client-mcp:8080"| client

        client -->|"mcp-server:3000"| mcp
        client -->|"agent:8000"| agent
        client -->|"redis:6379"| redis

        mcp -->|"postgres:5432"| postgres
        agent -->|"postgres:5432"| postgres

        pgadmin -->|"postgres:5432"| postgres
    end

    Client -->|"Port 80/443"| nginx

    style Internet fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style DockerNetwork fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    style Services fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

### Deployment Flow

```mermaid
flowchart TD
    Start([🚀 Start Deployment]) --> CheckEnv{".env<br/>Configured?"}

    CheckEnv -->|❌ No| ConfigEnv["📝 Configure .env<br/>- GOOGLE_API_KEY<br/>- POSTGRES_PASSWORD<br/>- Database settings"]
    CheckEnv -->|✅ Yes| CheckDocker{Docker<br/>Installed?}

    ConfigEnv --> CheckDocker

    CheckDocker -->|❌ No| InstallDocker[Install Docker<br/>& Docker Compose]
    CheckDocker -->|✅ Yes| ChooseMode{Deployment<br/>Mode?}

    InstallDocker --> ChooseMode

    ChooseMode -->|Development| LocalStack["🛠️ Local Stack<br/>cd DockerConfig<br/>docker-compose up -d"]
    ChooseMode -->|Production| ProdStack["🚀 Production Stack<br/>cd Lab01-MCP<br/>docker-compose up -d"]

    LocalStack --> InitDB["Initialize Database<br/>cd ../SQL<br/>./scripts/deploy.sh"]
    ProdStack --> InitDB

    InitDB --> HealthCheck["🏥 Health Checks<br/>- PostgreSQL: 5434<br/>- MCP Server: 3000<br/>- Nginx: 80"]

    HealthCheck --> Verify{All Services<br/>Healthy?}

    Verify -->|❌ Failed| Logs["📋 Check Logs<br/>docker-compose logs -f"]
    Verify -->|✅ Success| Ready["✅ System Ready<br/>- Access via localhost<br/>- Check pgAdmin: 5050<br/>- Test API endpoints"]

    Logs --> Troubleshoot["🔧 Troubleshoot<br/>- Check ports<br/>- Verify credentials<br/>- Review configs"]
    Troubleshoot --> Verify

    Ready --> End([🎉 Deployment Complete])

    style Start fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style Ready fill:#c8e6c9,stroke:#1b5e20,stroke-width:3px
    style End fill:#a5d6a7,stroke:#388e3c,stroke-width:3px
    style CheckEnv fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style CheckDocker fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style ChooseMode fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style Verify fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Logs fill:#ffcdd2,stroke:#c62828,stroke-width:2px
```

---

## 🚀 Quick Start

### Opción 1: Proyecto Completo (Recomendado)
```bash
cd /home/javort/Lab01-MCP
docker-compose up -d  # Inicia TODOS los servicios
```

### Opción 2: Solo Base de Datos (Este Directorio)
```bash
cd /home/javort/Lab01-MCP/DockerConfig
docker-compose up -d  # Solo PostgreSQL + pgAdmin
```

## 📊 Services

### Service Comparison Matrix

| Service | Production Stack | Local Dev Stack | Port (External) | Port (Internal) |
|---------|-----------------|-----------------|-----------------|-----------------|
| **PostgreSQL** | ✅ Yes | ✅ Yes | 5434 | 5432 |
| **pgAdmin** | ✅ Yes (dev profile) | ✅ Yes | 5050 / 8090 | 80 |
| **MCP Server** | ✅ Yes | ❌ No | 3000 | 3000 |
| **Client MCP** | ✅ Yes | ❌ No | Internal | 8080 |
| **Gemini Agent** | ✅ Yes | ❌ No | Internal | 8000 |
| **Redis** | ✅ Yes (cache profile) | ❌ No | 6379 | 6379 |
| **Nginx** | ✅ Yes (prod profile) | ❌ No | 80/443 | 80 |

### Production Stack (Root docker-compose.yml)

**File Location:** `/home/javort/Lab01-MCP/docker-compose.yml`

**Included Services:**
- 🐘 **PostgreSQL 16** + pgvector - Main database
- 🔌 **MCP Server** (FastMCP) - Tool execution engine
- 🤖 **Client MCP** (Odiseo Bot) - AI conversation agent
- 🧠 **Gemini Agent** - AI service provider
- 📊 **pgAdmin 4** - Database management UI
- ⚡ **Redis** - Caching layer
- 🌐 **Nginx** - Reverse proxy & load balancer

**Profiles:**
- `default` - Core services (PostgreSQL, MCP, Client, Agent)
- `dev` - Development tools (pgAdmin)
- `cache` - Redis caching
- `production` - Full stack with Nginx

### Local Development Stack (DockerConfig/)

**File Location:** `/home/javort/Lab01-MCP/DockerConfig/docker-compose.yml`

**Minimal Stack for DB Development:**

#### 🐘 PostgreSQL
| Property | Value |
|----------|-------|
| **Port** | 5434 (external) → 5432 (internal) |
| **Database** | `mcpdb` |
| **User** | `mcp_user` |
| **Password** | `mcp_password` |
| **Schema** | `test` (default) |
| **Extensions** | pgvector, pg_trgm, unaccent |

#### 📊 pgAdmin 4
| Property | Value |
|----------|-------|
| **URL** | http://localhost:8090 |
| **Email** | admin@example.com |
| **Password** | admin123 |
| **Mode** | Desktop (no master password) |
| **Pre-configured Server** | MCP Database (auto-connect) |

## 🔧 Configuración de Conexión

### Para aplicaciones
```
Host: localhost
Port: 5434
Database: mcpdb
Username: mcp_user
Password: mcp_password
```

### Para pgAdmin
- El servidor PostgreSQL ya está preconfigurado en pgAdmin como "MCP Database"
- **Credenciales automáticas**: No solicita contraseña al conectarse al servidor
- **Configuración persistente**: Las configuraciones se mantienen entre reinicios

## 📁 Estructura

```
DockerConfig/
├── Dockerfile.mcp              # Dockerfile para MCP Server
├── Dockerfile.client           # Dockerfile para Cliente MCP
├── Dockerfile.agent            # Dockerfile para Gemini Agent
├── docker-compose.yml          # Configuración LOCAL (solo DB)
├── docker-compose.override.yml # Sobrescrituras opcionales
├── .env                        # Variables para docker-compose LOCAL
├── nginx.conf                  # Configuración de Nginx
├── pgadmin-servers.json        # Servidores pre-configurados
├── start.sh                    # Script de inicio
├── stop.sh                     # Script de parada
├── pgadmin/                    # Configuración de pgAdmin
│   └── servers.json
└── README.md                   # Este archivo
```

## 🌐 Networking

### Docker Networks

```mermaid
graph TB
    subgraph PublicNetwork["🌐 Public Network (Host)"]
        HostMachine["💻 Host Machine<br/>localhost"]
    end

    subgraph ProductionNetwork["🔗 lab01_network (Bridge)"]
        direction TB

        ProdServices["Production Services<br/>━━━━━━━━━━━━━━━<br/>• nginx (80/443)<br/>• client-mcp (8080)<br/>• mcp-server (3000)<br/>• gemini-agent (8000)<br/>• postgres (5432)<br/>• redis (6379)<br/>• pgadmin (80)"]

        ProdDNS["Internal DNS<br/>━━━━━━━━━━<br/>nginx → mcp-server<br/>client-mcp → mcp-server<br/>mcp-server → postgres"]
    end

    subgraph LocalNetwork["🔗 docker-config (Bridge)"]
        direction TB

        LocalServices["Local Dev Services<br/>━━━━━━━━━━━━━━━<br/>• postgres (5432)<br/>• pgadmin (80)"]

        LocalDNS["Internal DNS<br/>━━━━━━━━━━<br/>pgadmin → postgres"]
    end

    HostMachine -->|"Port Mapping<br/>5050 → pgadmin:80"| ProdServices
    HostMachine -->|"Port Mapping<br/>5434 → postgres:5432"| ProdServices
    HostMachine -->|"Port Mapping<br/>3000 → mcp-server:3000"| ProdServices
    HostMachine -->|"Port Mapping<br/>80/443 → nginx:80"| ProdServices

    HostMachine -->|"Port Mapping<br/>8090 → pgadmin:80"| LocalServices
    HostMachine -->|"Port Mapping<br/>5434 → postgres:5432"| LocalServices

    ProdServices -.->|"Inter-container<br/>Communication"| ProdDNS
    LocalServices -.->|"Inter-container<br/>Communication"| LocalDNS

    style PublicNetwork fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style ProductionNetwork fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
    style LocalNetwork fill:#fff3e0,stroke:#e65100,stroke-width:3px
    style ProdServices fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style LocalServices fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px
```

### Port Mappings

#### Production Stack Ports

| Service | Container Port | Host Port | Protocol | Access |
|---------|---------------|-----------|----------|--------|
| **Nginx** | 80 | 80 | HTTP | Public |
| **Nginx** | 443 | 443 | HTTPS | Public |
| **MCP Server** | 3000 | 3000 | HTTP | Internal/API |
| **PostgreSQL** | 5432 | 5434 | TCP | Database |
| **pgAdmin** | 80 | 5050 | HTTP | Admin UI |
| **Redis** | 6379 | 6379 | TCP | Cache |
| **Client MCP** | 8080 | - | HTTP | Internal only |
| **Gemini Agent** | 8000 | - | HTTP | Internal only |

#### Local Dev Stack Ports

| Service | Container Port | Host Port | Protocol | Access |
|---------|---------------|-----------|----------|--------|
| **PostgreSQL** | 5432 | 5434 | TCP | Database |
| **pgAdmin** | 80 | 8090 | HTTP | Admin UI |

**Note:** Port 5434 is shared between stacks - ensure only one is running at a time.

---

## 🔀 Configuration Comparison

### Docker Compose Files Comparison

| Aspect | Production Stack | Local Dev Stack |
|--------|-----------------|-----------------|
| **File Path** | `/Lab01-MCP/docker-compose.yml` | `/Lab01-MCP/DockerConfig/docker-compose.yml` |
| **Services Count** | 7 services | 2 services |
| **Environment File** | `/Lab01-MCP/.env` | `/Lab01-MCP/DockerConfig/.env` |
| **Docker Network** | `lab01_network` | `docker-config` |
| **Purpose** | ✅ Full production stack | ⚠️ Database development only |
| **Startup Command** | `docker-compose up -d` | `cd DockerConfig && docker-compose up -d` |
| **Profiles** | dev, cache, production | None |
| **Volume Persistence** | Yes (all services) | Yes (PostgreSQL only) |

## 🔒 Seguridad

⚠️ **Solo para desarrollo local**
- Las contraseñas son simples para facilitar el desarrollo
- No usar en producción
- Cambiar credenciales para entornos reales

## 📋 Comandos Útiles

```bash
# Verificar estado de servicios
docker-compose ps

# Reiniciar PostgreSQL
docker-compose restart postgres

# Acceder a PostgreSQL directamente
docker exec -it mcp-postgres psql -U mcp_user -d mcpdb

# Ver logs específicos
docker-compose logs postgres
docker-compose logs pgadmin

# Limpiar todo (incluyendo volúmenes)
docker-compose down -v
```

## 🔧 Extensiones Incluidas

- **vector**: Búsquedas vectoriales (pgvector)
- **uuid-ossp**: Generación de UUIDs
- **unaccent**: Búsquedas sin acentos
- **pg_trgm**: Búsquedas con similitud

## 🎯 Uso con MCP

Esta configuración está optimizada para trabajar con el servidor MCP en el puerto 5434.

### Configuración en aplicaciones MCP:
```python
DATABASE_URL = "postgresql://mcp_user:mcp_password@localhost:5434/mcpdb"
SCHEMA_NAME = "test"
```

### Esquema por defecto
- **search_path**: `test, public`
- **Esquema principal**: `test` (para tablas de productos y MCP)