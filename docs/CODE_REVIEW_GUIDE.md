# Professional Code Review Guide - Lab01-MCP

## Overview
Este proyecto sigue estándares profesionales de code review basados en las mejores prácticas de Python 2025.

## Command: `make review`

Ejecuta una revisión completa de código con 6 verificaciones:

```bash
make review          # Ejecutar review completo
make review-fix      # Auto-fix problemas detectados
make review-report   # Generar reporte detallado
```

---

## 1. LINTING CON RUFF (850+ rules)
**Herramienta:** `ruff check`
**Standard:** PEP 8, PEP 20, Python style guide

### Reglas aplicadas:
- ✅ **E/W**: Errores y warnings de pycodestyle
- ✅ **F**: Pyflakes (undefined names, unused imports, redefinition)
- ✅ **N**: pep8-naming (function_case, CONSTANT_CASE)
- ✅ **UP**: pyupgrade (modernizar código a Python 3.10+)
- ✅ **C4**: Comprehensions optimization
- ✅ **SIM**: Simplificación de código
- ✅ **T20**: Sin print() en production
- ✅ **ARG**: Argumentos no utilizados
- ✅ **TRY**: Exception handling patterns

### Ejemplos detectados:
```python
# ❌ Rechazado
result = foo()
result = foo()  # Variable asignada pero no usada

# ✅ Aceptado
result = foo()
process(result)
```

---

## 2. IMPORT SORTING CON ISORT
**Herramienta:** `isort`
**Standard:** Organized imports (stdlib, third-party, local)

### Estructura requerida:
```python
# Imports de stdlib
import os
import sys
from pathlib import Path
from typing import Optional

# Imports de third-party
import psycopg2
from pydantic import BaseModel

# Imports locales
from client_mcp.models import User
from agent.handlers import process
```

### Propiedades:
- ✅ Agrupa imports en 3 secciones
- ✅ Alfabética dentro de cada sección
- ✅ Multi-line cuando es necesario
- ✅ Trailing commas

---

## 3. TYPE CHECKING CON MYPY (Strict Mode)
**Herramienta:** `mypy --strict`
**Standard:** PEP 484, PEP 604, Modern Type Hints

### Type Hints Modernos (Python 3.10+):

#### ❌ Antiguo (Deprecado)
```python
from typing import Union, List, Dict, Optional

def process(items: List[str], config: Optional[Dict[str, int]]) -> Union[str, int]:
    pass
```

#### ✅ Nuevo (Recomendado)
```python
def process(items: list[str], config: dict[str, int] | None) -> str | int:
    pass
```

### Reglas aplicadas:
- ✅ **disallow_untyped_defs**: Todas las funciones deben tener type hints
- ✅ **disallow_incomplete_defs**: Type hints completos
- ✅ **disallow_untyped_calls**: No llamar funciones sin tipos
- ✅ **no_implicit_optional**: Explícito para None
- ✅ **strict_equality**: Comparaciones type-safe

### Ejemplos válidos:
```python
# ✅ Correcto
def calculate_total(price: float, tax: float) -> float:
    return price * (1 + tax)

user_id: int | str = get_user_id()  # PEP 604 union

class Product(BaseModel):
    name: str
    price: float
    tags: list[str] = []  # PEP 585 generic
```

---

## 4. DEAD CODE DETECTION CON VULTURE
**Herramienta:** `vulture`
**Confidence:** 80% (detección automática)

### Detecta:
- ✅ Funciones no utilizadas
- ✅ Clases no instanciadas
- ✅ Variables asignadas pero no leídas
- ✅ Imports no utilizados
- ✅ Código inalcanzable

### Ejemplo:
```python
# ❌ Detectado como dead code
def unused_function():  # nunca se llama
    return 42

def process():
    x = 10  # asignada pero no usada
    return 20
```

---

## 5. SECURITY ANALYSIS CON BANDIT
**Herramienta:** `bandit -ll` (high+medium severity)
**Standard:** OWASP Top 10

### Detecta:
- ✅ Hardcoded passwords/secrets
- ✅ SQL injection risks
- ✅ Insecure random
- ✅ Insecure temporary files
- ✅ Assert en producción
- ✅ Pickle usage (deserialization)

### Ejemplo:
```python
# ❌ Rechazado
password = "admin123"  # Hardcoded

# ✅ Aceptado
password = os.getenv("DATABASE_PASSWORD")
```

---

## 6. CODE FORMATTING CON RUFF FORMAT
**Herramienta:** `ruff format`
**Standard:** Line length 100, Black-compatible

### Rules aplicadas:
- ✅ F-strings obligatorios (cuando no hay overhead)
- ✅ Sin hardcode de valores
- ✅ Líneas máximo 100 caracteres
- ✅ Quotes consistentes (preferir ")
- ✅ Trailing commas en multi-line

### F-Strings vs format():
```python
# ✅ F-strings (eficientes)
name = "John"
result = f"Hello {name}"

# ⚠️ format() solo si es dinámico
template = "Hello {}"
result = template.format(name)

# ❌ Concatenación (evitar)
result = "Hello " + name
```

---

## No Hardcode Rule

### ❌ Rechazado:
```python
DB_HOST = "localhost"
DB_PORT = 5432
API_KEY = "sk-1234567890"
```

### ✅ Aceptado:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"  # con valor por defecto
    db_port: int = 5432
    api_key: str  # del environment

settings = Settings()
```

---

## Best Practices Summary

| Práctica | Tool | Command |
|----------|------|---------|
| PEP 8 Compliance | ruff | `make lint` |
| Import Organization | isort | `make review` |
| Type Hints | mypy | `make check` |
| Dead Code | vulture | `make review` |
| Security | bandit | `make review` |
| Formatting | ruff | `make format` |

---

## Auto-Fix Available

```bash
make review-fix  # Corrige automáticamente:
                 # - Import ordering (isort)
                 # - Code formatting (ruff format)
                 # - Common issues (ruff --fix)
```

---

## Integration with CI/CD

```yaml
# .github/workflows/code-quality.yml
name: Code Quality
on: [push, pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: make install
      - run: make review
```

---

## Configuration Files

- **pyproject.toml**: Ruff, Mypy, Isort, Pytest configuration
- **Makefile**: Commands para ejecutar reviews
- **.ruff.toml** (opcional): Configuración específica de Ruff

---

## Further Reading

- [PEP 604 - Union Types as X | Y](https://peps.python.org/pep-0604/)
- [PEP 585 - Generic Collections](https://peps.python.org/pep-0585/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
