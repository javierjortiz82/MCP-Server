# Migración a Pydantic v2 - Documentación

## 📅 Fecha: 2025-10-09

### 🎯 Objetivo
Migrar el sistema de configuración de `mcp_server` de dataclasses a Pydantic v2 BaseSettings para mejorar la validación, type safety y manejo de variables de entorno.

---

## ✅ Cambios Implementados

### 1. **Nueva Estructura de Configuración**

#### Archivos Creados:
```
mcp_server/
├── config/
│   ├── __init__.py
│   └── settings.py (Pydantic v2 BaseSettings)
```

#### Archivos Eliminados:
```
mcp_server/utils/config.py → config.py.bak (backup)
```

---

### 2. **Migración de Código**

#### Cambios en Imports:
```python
# ANTES
from utils.config import settings

# DESPUÉS
from config import settings
```

#### Cambios en Nombres de Variables:
| Antes (snake_case) | Después (UPPER_CASE) |
|-------------------|---------------------|
| `settings.database_url` | `settings.DATABASE_URL` |
| `settings.schema_name` | `settings.SCHEMA_NAME` |
| `settings.google_api_key` | `settings.GOOGLE_API_KEY` |
| `settings.embedding_model` | `settings.EMBEDDING_MODEL` |
| `settings.log_level` | `settings.LOG_LEVEL` |
| `settings.log_max_size_mb` | `settings.LOG_MAX_SIZE_MB` |
| `settings.log_backup_count` | `settings.LOG_BACKUP_COUNT` |
| `settings.log_dir` | `settings.LOG_DIR` |

---

### 3. **Archivos Modificados**

#### Core Utils:
- ✅ `utils/logger.py` - Sistema de logging
- ✅ `utils/db.py` - Database connection
- ✅ `utils/embeddings.py` - Embeddings client

#### Tools:
- ✅ `tools/fetch.py`
- ✅ `tools/search.py`
- ✅ `tools/fuzzy_search.py`

#### Handlers:
- ✅ `mcp_handlers/resource_handlers.py`

#### Server:
- ✅ `server.py`

---

### 4. **Nueva Configuración Pydantic v2**

```python
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuration settings for MCP Server."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")
    SCHEMA_NAME: str = Field(default="test", description="PostgreSQL schema name")

    # Google GenAI
    GOOGLE_API_KEY: str = Field(..., description="Google API key for Gemini AI")
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-001")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_MAX_SIZE_MB: int = Field(default=10, gt=0)
    LOG_BACKUP_COUNT: int = Field(default=5, gt=0)
    LOG_DIR: str = Field(default="logs")

    # Validators
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()

    # Computed Properties
    @property
    def log_dir_path(self) -> Path:
        """Get absolute path to logs directory."""
        return Path(__file__).parent.parent / self.LOG_DIR

    @property
    def log_max_bytes(self) -> int:
        """Get max log file size in bytes."""
        return self.LOG_MAX_SIZE_MB * 1024 * 1024

settings = Settings()
```

---

### 5. **Dependencias Actualizadas**

#### pyproject.toml:
```toml
dependencies = [
    "mcp>=1.2.0",
    "psycopg2-binary>=2.9.10",
    "google-genai>=1.38.0",
    "pgvector>=0.4.1",
    "python-dotenv>=1.0.0",
    "uvicorn>=0.30.0",
    "pydantic>=2.11.0",           # NUEVO
    "pydantic-settings>=2.11.0",  # NUEVO
]
```

---

## 🧪 Verificación

### Tests Realizados:

1. **Carga de Settings:**
```bash
python -c "from config import settings; print(settings.DATABASE_URL)"
✅ Settings cargados correctamente
```

2. **Validación de Tipos:**
```bash
python -c "from config.settings import Settings; s = Settings()"
✅ Validación Pydantic funcionando
```

3. **Computed Properties:**
```bash
python -c "from config import settings; print(settings.log_dir_path)"
✅ /home/javort/Lab01-MCP/mcp_server/logs
```

4. **Imports del Sistema:**
```bash
python -c "from utils.db import init_db; from utils.logger import setup_logging"
✅ Todos los imports funcionan
```

---

## 🎁 Beneficios de Pydantic v2

### 1. **Type Safety**
- Validación automática en tiempo de carga
- Detección temprana de errores de configuración
- Type hints completos

### 2. **Validación Avanzada**
```python
# Field validators personalizados
@field_validator("DATABASE_URL")
@classmethod
def validate_database_url(cls, v: str) -> str:
    if not v.startswith("postgresql://"):
        raise ValueError("Must be PostgreSQL URL")
    return v
```

### 3. **Computed Properties**
```python
@property
def log_dir_path(self) -> Path:
    """Absolute path, not relative."""
    return Path(__file__).parent.parent / self.LOG_DIR
```

### 4. **Mejor Manejo de .env**
- Path relativo al archivo settings.py
- Case insensitive
- Extra fields ignorados
- Encoding UTF-8

### 5. **Documentación Inline**
```python
DATABASE_URL: str = Field(
    ...,  # Required
    description="PostgreSQL connection URL",
    examples=["postgresql://user:pass@localhost:5432/db"],
)
```

---

## 🚨 Breaking Changes

### Para Desarrolladores:

1. **Imports:**
   - `from utils.config` → `from config`

2. **Variable Names:**
   - Todos los accesos deben usar UPPER_CASE
   - `settings.database_url` → `settings.DATABASE_URL`

3. **Type Safety:**
   - Errores de configuración se detectan al import, no en runtime
   - Valores inválidos lanzan `ValidationError`

---

## 📝 Guía de Migración para Nuevos Módulos

Si necesitas crear un nuevo módulo que use configuración:

```python
# 1. Import settings
from config import settings

# 2. Usar variables con UPPER_CASE
database_url = settings.DATABASE_URL
schema = settings.SCHEMA_NAME

# 3. Usar computed properties cuando sea posible
log_path = settings.log_dir_path  # Path absoluto
max_bytes = settings.log_max_bytes  # Calculado
```

---

## 🔧 Troubleshooting

### Error: "cannot import name 'settings' from 'utils.config'"
**Solución:** Actualizar import a `from config import settings`

### Error: "AttributeError: 'Settings' object has no attribute 'database_url'"
**Solución:** Usar UPPER_CASE → `settings.DATABASE_URL`

### Error: "ValidationError: DATABASE_URL field required"
**Solución:** Añadir `DATABASE_URL` al archivo `.env`

### Error: ".env file not found"
**Solución:** Crear `.env` en `mcp_server/` copiando desde `.env.example`

---

## 📚 Referencias

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Field Validators](https://docs.pydantic.dev/latest/concepts/validators/)

---

**Autor:** Claude (Anthropic)  
**Fecha:** 2025-10-09  
**Versión:** 1.0.0
