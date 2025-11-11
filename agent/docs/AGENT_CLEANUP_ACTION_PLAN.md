# Plan de Acción: Limpieza y Reorganización de /agent

**Fecha:** 2025-10-20  
**Prioridad:** Crítica para Q4  
**Responsable:** Dev Team  

---

## Resumen Ejecutivo

El análisis de estructura de `/agent` identifica **5 problemas críticos** que afectan la organización, mantenibilidad y claridad del código. Este documento proporciona un plan de acción paso a paso.

### Impacto:
- **Desorden:** Test files dispersos en 3 ubicaciones diferentes
- **Violación SoC:** Test files mezclados con código fuente
- **Código muerto:** ~466 líneas de deprecated code sin deprecación formal
- **Organización:** Dificulta pytest discovery y CI/CD
- **Mantenibilidad:** Confunde nuevos desarrolladores

---

## Problema 1: Tests Dispersos en Root Directory (CRÍTICO)

### Descripción
9 archivos de tests están en la raíz de `/agent/` cuando deberían estar en `tests/`:

```
agent/
├── test_ab_testing.py ..................... 319 líneas
├── test_agent_factory.py ................. 267 líneas  
├── test_booking_modular_prompts.py ....... 211 líneas
├── test_general_modular_prompts.py ....... 224 líneas
├── test_modular_sales_prompt.py .......... 181 líneas
├── test_metrics.py ....................... 297 líneas
├── test_odiseo_bot_v2.py ................. 567 líneas
├── test_odiseo_bot_v2_integration.py .... 501 líneas
├── test_odiseo_prompt_integration.py .... 391 líneas
└── tests/
    ├── test_base_agent.py ................ 380 líneas
    ├── test_agent.py
    ├── test_config.py
    └── test_server.py
```

### Impacto
- Pytest descubrimiento inadecuado
- Confunde develadores (¿dónde están los tests?)
- Contamina directorio raíz con 3,800 líneas de test code
- CI/CD pipelines pueden no detectar todos los tests

### Solución

**Paso 1: Crear backup (opcional pero recomendado)**
```bash
cd /home/javort/Lab01-MCP/agent
mkdir -p .backup/test_files_backup_$(date +%Y%m%d_%H%M%S)
cp test_*.py .backup/test_files_backup_*/
```

**Paso 2: Mover todos los test files a tests/**
```bash
mv test_ab_testing.py tests/
mv test_agent_factory.py tests/
mv test_booking_modular_prompts.py tests/
mv test_general_modular_prompts.py tests/
mv test_modular_sales_prompt.py tests/
mv test_metrics.py tests/
mv test_odiseo_bot_v2.py tests/
mv test_odiseo_bot_v2_integration.py tests/
mv test_odiseo_prompt_integration.py tests/
```

**O en una línea:**
```bash
cd /home/javort/Lab01-MCP/agent && mv test_*.py tests/
```

**Paso 3: Verificar que todos se movieron**
```bash
ls -la tests/test_*.py | wc -l  # Debería mostrar 15 (6 existentes + 9 movidos)
ls -la test_*.py 2>/dev/null  # Debería estar vacío
```

**Paso 4: Verificar imports en tests/conftest.py**
Los imports relativos deben seguir funcionando después del move. Ejecutar:
```bash
cd /home/javort/Lab01-MCP/agent
python -m pytest tests/ -v --collect-only
```

### Timeline
- **Tiempo estimado:** 15 minutos
- **Testing required:** 30 minutos (verificar que los tests aún corren)
- **Total:** ~1 hora

---

## Problema 2: Test File Misplaced in Source Directory (CRÍTICO)

### Descripción
Un archivo de test está ubicado dentro del directorio de código fuente:

```
agent/
└── src/
    └── multi_agent/
        ├── booking_agent.py
        ├── sales_agent.py
        └── test_booking_input_parser.py ⚠️ WRONG LOCATION!
```

### Impacto
- **Violación SoC:** Mezcla código de test con código de producción
- **Confusion:** ¿Es esto una demo o un test?
- **Package pollution:** No debería distribuirse con paquete
- **Import issues:** Puede causar problemas de import circular

### Solución

**Paso 1: Mover el archivo**
```bash
mv /home/javort/Lab01-MCP/agent/src/multi_agent/test_booking_input_parser.py \
   /home/javort/Lab01-MCP/agent/tests/
```

**Paso 2: Verificar imports en el archivo movido**
Abrir `tests/test_booking_input_parser.py` y actualizar imports si es necesario:

```python
# ANTES (cuando estaba en src/multi_agent/):
from booking_input_parser import ...

# DESPUÉS (está en tests/):
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from multi_agent.booking_input_parser import ...
```

**Paso 3: Ejecutar el test para verificar**
```bash
cd /home/javort/Lab01-MCP/agent
python -m pytest tests/test_booking_input_parser.py -v
```

### Timeline
- **Tiempo estimado:** 10 minutos
- **Testing required:** 15 minutos
- **Total:** ~25 minutos

---

## Problema 3: Demo Files Not Organized (ALTO)

### Descripción
4 archivos de demo están en la raíz del proyecto:

```
agent/
├── demo_interactive.py .................. 235 líneas
├── demo_ab_testing_e2e.py .............. 383 líneas
├── demo_booking_ab_testing.py .......... 304 líneas
└── demo_general_ab_testing.py .......... 314 líneas
```

### Impacto
- Contamina root directory
- Confunde develadores (¿son tests o ejemplos?)
- Hace difícil distinguir entre código de producción y demostración

### Solución

**Paso 1: Crear directorio demos/**
```bash
mkdir -p /home/javort/Lab01-MCP/agent/demos
```

**Paso 2: Mover archivos demo**
```bash
mv /home/javort/Lab01-MCP/agent/demo_*.py /home/javort/Lab01-MCP/agent/demos/
```

**O en una línea:**
```bash
cd /home/javort/Lab01-MCP/agent && mkdir -p demos && mv demo_*.py demos/
```

**Paso 3: Actualizar references (si existen)**
Si algún script o documentación referencia estos archivos:
```bash
grep -r "demo_" /home/javort/Lab01-MCP/agent --exclude-dir=.git
```

Actualizar cualquier referencia a:
```
python agent/demos/demo_interactive.py
# en lugar de:
python agent/demo_interactive.py
```

**Paso 4: Crear README en demos/**
Crear `/home/javort/Lab01-MCP/agent/demos/README.md`:

```markdown
# Agent Demo Scripts

This directory contains demonstration and example scripts for the agent system.

## Available Demos

- `demo_interactive.py` - Interactive chatbot demo
- `demo_ab_testing_e2e.py` - End-to-end A/B testing demo
- `demo_booking_ab_testing.py` - Booking-specific A/B testing
- `demo_general_ab_testing.py` - General agent A/B testing

## Running Demos

```bash
cd agent
python demos/demo_interactive.py
```

These are not automated tests but interactive demonstrations.
```

### Timeline
- **Tiempo estimado:** 10 minutos
- **Documentación:** 10 minutos
- **Total:** ~20 minutos

---

## Problema 4: Legacy Code Not Marked Deprecated (ALTO)

### Descripción
El archivo `agent.py` (466 líneas) es DEPRECATED pero no está marcado como tal:

```python
# agent.py - CURRENT STATE (no deprecation marker)
class GeminiAgent:
    """Google Gemini AI Agent for natural language processing."""
    # ...
```

### Impacto
- Developers pueden usar código legacy sin saber que está deprecated
- No hay ruta de migración clara a BaseAgent
- Riesgo de que código nuevo dependa de clase legacy

### Solución

**Paso 1: Agregar deprecation decorator**

Editar `src/gemini_agent/agent.py` (línea 21, antes de la clase):

```python
import warnings
from functools import wraps

def deprecated(reason="", removal_date=""):
    """Decorator to mark a class/function as deprecated."""
    def decorator(cls):
        message = f"{cls.__name__} is deprecated"
        if reason:
            message += f": {reason}"
        if removal_date:
            message += f" (will be removed on {removal_date})"
        
        original_init = cls.__init__
        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            return original_init(self, *args, **kwargs)
        
        cls.__init__ = new_init
        cls.__deprecated__ = True
        return cls
    
    return decorator

@deprecated(
    reason="Use BaseAgent instead (provides same functionality with DRY principle)",
    removal_date="2025-12-31"
)
class GeminiAgent:
    """Google Gemini AI Agent for natural language processing.
    
    DEPRECATED: This class is deprecated. Use BaseAgent or specialized agents
    (BookingAgent, GeneralAgent, SalesAgent) instead.
    
    Migration guide:
    
    Before (using GeminiAgent):
        >>> from gemini_agent import GeminiAgent
        >>> agent = GeminiAgent(api_key="key")
        >>> await agent.initialize()
        >>> response = await agent.generate_response("Hello")
    
    After (using BaseAgent):
        >>> from multi_agent import BookingAgent  # or GeneralAgent, SalesAgent
        >>> agent = BookingAgent(api_key="key")
        >>> await agent.initialize()
        >>> response = await agent.generate_response("Hello")
    
    BaseAgent provides:
        - Unified interface for all agent types
        - Eliminated ~280 lines of duplicate code
        - Built-in memory management
        - MCP tools support
        - A/B testing framework
    
    Timeline: This class will be removed on 2025-12-31
    """
```

**Paso 2: Actualizar docstring**

El docstring de la clase ya contiene documentación, pero agregar nota prominente:

```python
class GeminiAgent:
    """Google Gemini AI Agent for natural language processing.
    
    .. deprecated::
        Use :class:`BaseAgent` or its specialized subclasses instead.
        This class is kept for backward compatibility and will be removed
        on 2025-12-31. See migration guide above.
    """
```

**Paso 3: Agregar changelog entry**

Editar `docs/CHANGELOG.md` o crear si no existe:

```markdown
## Deprecations

### v1.2.0
- `GeminiAgent` class is deprecated in favor of `BaseAgent`
  - **Reason:** BaseAgent eliminates code duplication and provides unified interface
  - **Removal date:** 2025-12-31
  - **Migration:** See `src/gemini_agent/agent.py` docstring for migration guide
```

**Paso 4: Update __init__.py to warn on import**

En `src/gemini_agent/__init__.py`:

```python
import warnings

from gemini_agent.agent import GeminiAgent
from gemini_agent.base_agent import BaseAgent
from gemini_agent.config import settings

warnings.warn(
    "GeminiAgent is deprecated, use BaseAgent or specialized agents instead. "
    "See https://github.com/yourrepo/docs/MIGRATION.md",
    category=DeprecationWarning,
    stacklevel=2
)

__version__ = "1.2.0"
__all__ = [
    "BaseAgent",
    "GeminiAgent",  # Kept for backward compatibility
    "settings",
]
```

**Paso 5: Create migration guide**

Crear `docs/MIGRATION_GEMINIGENT_TO_BASEAGENT.md`:

```markdown
# Migration Guide: GeminiAgent → BaseAgent

GeminiAgent has been deprecated in favor of BaseAgent and specialized agents.

## Why the change?

1. **Code Deduplication:** BaseAgent eliminated ~280 lines of duplicate code
2. **Unified Interface:** All agents (Booking, Sales, General) inherit from BaseAgent
3. **Better Features:** Built-in memory management, MCP tools, A/B testing

## Migration Steps

### Before: Using GeminiAgent
```python
from gemini_agent import GeminiAgent

agent = GeminiAgent(api_key="YOUR_KEY")
await agent.initialize()
response = await agent.generate_response("Hello")
```

### After: Using BaseAgent (base class)
```python
from gemini_agent import BaseAgent

class CustomAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "my_agent"
    
    def get_system_prompt(self, **kwargs) -> str:
        return "You are a helpful assistant"

agent = CustomAgent(api_key="YOUR_KEY")
await agent.initialize()
response = await agent.generate_response("Hello")
```

### After: Using Specialized Agents (recommended)
```python
from multi_agent import BookingAgent, SalesAgent, GeneralAgent

# For booking/reservations
booking_agent = BookingAgent()
await booking_agent.initialize()
response = await booking_agent.generate_response("I want to book")

# For sales/products
sales_agent = SalesAgent()
await sales_agent.initialize()
response = await sales_agent.generate_response("I'm looking for...")

# For general info/FAQ
general_agent = GeneralAgent()
await general_agent.initialize()
response = await general_agent.generate_response("How do I...?")
```

## Key Differences

| Feature | GeminiAgent | BaseAgent | Specialized |
|---------|------------|-----------|-------------|
| Code duplication | High | None | None |
| Agent specialization | No | Custom | Built-in |
| Memory management | Limited | Full | Full |
| MCP tools support | Manual | Auto | Auto |
| A/B testing | Manual | Built-in | Built-in |
| Use case | Generic | Custom | Production |

## Timeline

- **Now:** Use deprecated warnings
- **2025-11-30:** Last warning before removal
- **2025-12-31:** GeminiAgent removed from codebase
```

### Timeline
- **Código:** 30 minutos
- **Documentación:** 30 minutos
- **Testing:** 30 minutos (verificar que warnings funcionen)
- **Total:** ~1.5 horas

---

## Problema 5: Large Complex Files (MEDIO)

### Descripción
Dos archivos exceden 700 líneas y contienen lógica compleja:

| Archivo | Líneas | Complejidad |
|---------|--------|-------------|
| `agent_router.py` | 734 | Alta (clasificación de intents, memory integration) |
| `prompt_manager.py` | 900 | Alta (sistema modular de prompts) |

### Impacto
- Difícil de mantener
- Posible dead code no identificado
- Difícil de testear

### Solución

**Paso 1: Auditar agent_router.py**

```bash
cd /home/javort/Lab01-MCP/agent
grep -n "CLASSIFICATION_PROMPT" src/multi_agent/agent_router.py
grep -n "TODO\|FIXME\|XXX\|HACK" src/multi_agent/agent_router.py
```

Revisar si existen:
- [ ] Legacy classification prompt no usado
- [ ] Fallback logic innecesaria
- [ ] Code paths nunca alcanzados

**Paso 2: Documentar en agent_router.py**

Agregar al inicio del archivo después del docstring:

```python
"""
ARCHITECTURE NOTES:
===================

This module uses:
1. PRIMARY: PromptManager-based classification (ACTIVE)
   - Uses get_classification_prompt() for deterministic results
   - Supports A/B testing via PromptManager
   - Used in classify_intent() method

2. FALLBACK: Pattern matching (LEGACY - marked for removal)
   - Uses CLASSIFICATION_PROMPT constant
   - Only used if Gemini API call fails
   - Status: DEPRECATED as of v1.2.0
   - Removal target: v2.0.0 (2025-12-31)

3. MEMORY INTEGRATION: Optional (ACTIVE)
   - Uses memory_manager to load user context
   - Improves classification accuracy for returning users
   - Session-level + user-level memory support
"""
```

**Paso 3: Auditar prompt_manager.py**

```bash
grep -n "def " src/multi_agent/prompt_manager.py | head -20
grep -n "DEPRECATED\|TODO\|FIXME" src/multi_agent/prompt_manager.py
```

Crear documento de "Prompt Inventory":

```python
# Al inicio de prompt_manager.py, agregar:
"""
PROMPT INVENTORY:
================

ACTIVE (producción):
  - get_booking_prompt(): Booking agent system prompt
  - get_general_prompt(): General agent system prompt
  - get_sales_prompt(): Sales agent system prompt
  - get_classification_prompt(): Intent classification
  - get_memory_context_prompt(): Memory enrichment

A/B TESTING (experimental):
  - [variant A] get_booking_prompt(user_id=uid, variant='a')
  - [variant B] get_booking_prompt(user_id=uid, variant='b')
  - Similar for sales and general prompts

DEPRECATED (legacy):
  - None currently marked

TESTING:
  All prompts covered by tests in:
    - tests/test_booking_modular_prompts.py
    - tests/test_general_modular_prompts.py
    - tests/test_modular_sales_prompt.py
"""
```

### Timeline
- **Auditoría:** 1-2 horas
- **Documentación:** 1 hora
- **Refactoring (si es necesario):** 2-4 horas
- **Total:** 4-7 horas

---

## Problema 6: booking_agent_settings.py Underutilization (BAJO)

### Descripción
Archivo de 110 líneas con configuración específica de booking que casi no se usa:

```python
# src/gemini_agent/config/booking_agent_settings.py
from pydantic import Field
from pydantic_settings import BaseSettings

class BookingAgentSettings(BaseSettings):
    BOOKING_MAX_SLOTS: int = Field(default=10)
    BOOKING_TIMEZONE: str = Field(default="America/Bogota")
    # ... more specific settings
```

### Análisis
1. **Uso actual:** Mínimo - solo config específica de booking
2. **Alternativa:** La mayoría de config ya está en `settings.py` genérico
3. **Valor**: Puede ser útil para futuro, pero ahora ocupa espacio

### Recomendación

**Opción A: Mantener (si booking tiene futuro config diferente)**
```bash
# Documentar por qué existe y cómo se usa
echo "Booking-specific configuration. Used by: BookingAgent" > \
  docs/CONFIG_BOOKING_AGENT_SETTINGS.md
```

**Opción B: Fusionar (si config es casi idéntica)**
```python
# Mover contents a settings.py
# Mantener import alias para backward compatibility:
from gemini_agent.config.settings import Settings as BookingAgentSettings
```

**Recomendación:** Opción A (mantener por ahora, revisar en próximo sprint)

---

## Resumen de Acciones

### Semana 1 (CRÍTICO - 2-3 horas)

1. **Mover test_*.py de root a tests/**
   ```bash
   cd /home/javort/Lab01-MCP/agent && mv test_*.py tests/
   ```
   Validar con: `python -m pytest tests/ --collect-only`

2. **Mover test_booking_input_parser.py de src/ a tests/**
   ```bash
   mv src/multi_agent/test_booking_input_parser.py tests/
   ```
   Validar con: `python -m pytest tests/test_booking_input_parser.py -v`

3. **Crear demos/ y mover demo_*.py**
   ```bash
   mkdir demos && mv demo_*.py demos/
   ```

### Semana 2 (ALTO - 2-3 horas)

4. **Marcar agent.py como deprecated**
   - Agregar @deprecated decorator
   - Actualizar docstring con migration guide
   - Crear docs/MIGRATION_GEMINIGENT_TO_BASEAGENT.md

5. **Crear README en demos/**
   - Documentar qué hace cada demo
   - Instrucciones de ejecución

### Semana 3 (MEDIO - 4-7 horas)

6. **Auditar agent_router.py**
   - Documentar qué clasificación se usa (primary vs fallback)
   - Remover dead code si existe
   - Marcar como legacy cualquier fallback

7. **Auditar prompt_manager.py**
   - Crear Prompt Inventory
   - Documentar qué prompts están activos

---

## Validation Checklist

Después de completar todas las acciones:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] No test_*.py files in root: `ls test_*.py 2>/dev/null` (should be empty)
- [ ] No test_*.py files in src/: `find src/ -name "test_*.py"` (should be empty)
- [ ] demos/ directory exists: `ls -d demos/`
- [ ] agent.py has deprecation warning: `grep -q "@deprecated" src/gemini_agent/agent.py`
- [ ] Migration guide exists: `ls docs/MIGRATION_GEMINIGENT_TO_BASEAGENT.md`
- [ ] Directory tree is clean: `tree agent/ -I '__pycache__|.pytest_cache|.mypy_cache|htmlcov'`

---

## Success Metrics

After implementing all actions:

| Metric | Before | After |
|--------|--------|-------|
| Test files in root | 9 | 0 |
| Test files in src/ | 1 | 0 |
| Total files in agent/ root | 20+ | <10 |
| agent.py deprecation status | No | Yes |
| Code organization clarity | Poor | Good |
| New developer onboarding | Confusing | Clear |

---

**Document created:** 2025-10-20  
**Version:** 1.0  
**Status:** Ready for implementation

