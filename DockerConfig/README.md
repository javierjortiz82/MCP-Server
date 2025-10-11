# DockerConfig - Configuración de Docker

Este directorio contiene archivos de configuración de Docker para el proyecto Lab01-MCP.

## ⚠️ IMPORTANTE: Dos Configuraciones Docker

Este directorio contiene:
1. **Docker Compose Local** (`docker-compose.yml` aquí) - Solo PostgreSQL + pgAdmin para desarrollo
2. **Dockerfiles** para el docker-compose.yml principal del proyecto raíz

## 🚀 Inicio Rápido

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

## 📊 Servicios

### Docker Compose Principal (Proyecto Raíz)
✅ **Archivo:** `/home/javort/Lab01-MCP/docker-compose.yml`
- PostgreSQL + pgvector
- MCP Server
- Client MCP (Odiseo Bot)
- Gemini Agent
- PgAdmin (perfil: dev)
- Redis (perfil: cache)
- Nginx (perfil: production)

### Docker Compose Local (Este Directorio)
⚙️ **Archivo:** `/home/javort/Lab01-MCP/DockerConfig/docker-compose.yml`

#### PostgreSQL
- **Puerto**: 5434
- **Base de datos**: mcpdb
- **Usuario**: mcp_user
- **Contraseña**: mcp_password

#### pgAdmin
- **URL**: http://localhost:8090
- **Email**: admin@example.com
- **Contraseña**: admin123
- **Servidor PostgreSQL**: Preconfigurado
- **Modo**: Desktop (sin master password)

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
├── init/                       # Scripts SQL de inicialización
│   └── 01-create-database.sql
├── pgadmin/                    # Configuración de pgAdmin
│   └── servers.json
└── README.md                   # Este archivo
```

## 🔀 Diferencias entre Docker Compose Files

| Aspecto | Proyecto Raíz | DockerConfig/ |
|---------|---------------|---------------|
| **Archivo** | `/Lab01-MCP/docker-compose.yml` | `/Lab01-MCP/DockerConfig/docker-compose.yml` |
| **Servicios** | 7 servicios | 2 servicios |
| **Variables .env** | `/Lab01-MCP/.env` | `/Lab01-MCP/DockerConfig/.env` |
| **Red** | lab01_network | docker-config |
| **Uso** | ✅ Producción/Desarrollo | ⚠️ Solo base de datos |

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