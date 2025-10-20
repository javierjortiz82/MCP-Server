# Análisis: Problema de Contexto de Idioma - English Input vs Spanish Output

**Fecha:** 2025-10-20
**Problema:** Usuario escribe en inglés pero el sistema responde en español
**Severidad:** 🔴 CRÍTICO (afecta UX multi-idioma)

---

## 🔍 Análisis del Caso Reportado

### Input del Usuario:
```
👤 You: i want reserved
```
✅ Input en INGLÉS

### Output del Sistema:
```
🤖 Bot: Perfecto. Aquí tienes los servicios que puedes reservar:
1️⃣ **Consulta General** → 30 min, $50
2️⃣ **Demostración de Producto** → 45 min, Gratis
...
```
❌ Output en ESPAÑOL (cambió de contexto)

### Logs que Revelan el Problema:

```
[INFO] prompt_manager:912 - 🌐 TEMPLATE_SELECTION: user_lang=es → base/router_classification.jinja2
[INFO] booking_agent:399 - 🌐 GENERATE_RESPONSE: Agent language is 'es', setting kwargs['user_lang']=es
[INFO] booking_agent:289 - 🌐 GET_SYSTEM_PROMPT: Requesting template for language: es
```

**Conclusión:** El sistema está usando "es" (español) como idioma incluso con input en inglés.

---

## 🎯 Raíz del Problema

### 1. **BaseAgent - Idioma por Defecto Hardcodeado**

**Archivo:** `src/gemini_agent/base_agent.py:115`

```python
def __init__(
    self,
    api_key: str | None = None,
    model_name: str | None = None,
    language: str = "es",  # ⚠️ HARDCODED DEFAULT = SPANISH
    **generation_params: Any,
) -> None:
```

**Problema:**
- ✅ Valor por defecto: `"es"` (Español)
- ❌ NO hay detección automática del idioma del usuario
- ❌ NO hay parámetro para cambiar el idioma en tiempo de ejecución
- ❌ Se usa este idioma para TODOS los prompts y respuestas

**Impacto:**
- Todos los agentes heredan este idioma por defecto
- BookingAgent recibe `language="es"` aunque el usuario hable inglés

---

### 2. **BookingAgent - Setea Idioma sin Detectarlo**

**Archivo:** `src/multi_agent/booking_agent.py:398`

```python
async def generate_response(self, query: str, **kwargs: Any) -> str:
    # ...
    kwargs["user_lang"] = self.language  # ⚠️ Usa self.language (por defecto "es")
    self.logger.info(
        f"🌐 GENERATE_RESPONSE: Agent language is '{self.language}', "
        f"setting kwargs['user_lang']={self.language}"
    )
    system_prompt = self.get_system_prompt(**kwargs)
```

**Problema:**
- ✅ Usa `self.language` para generar prompts
- ❌ `self.language` es "es" por defecto
- ❌ NO hay lógica de detección del idioma del usuario

---

### 3. **PromptManager - Acepta Idioma pero No Lo Detecta**

**Archivo:** `src/multi_agent/prompt_manager.py:77`

```python
def get_booking_prompt(
    self,
    customer_email: str | None = None,
    user_id: str | None = None,
    user_lang: str = "es",  # ⚠️ VALOR POR DEFECTO = SPANISH
    ...
) -> str:
```

**Problema:**
- ✅ Acepta `user_lang` como parámetro
- ❌ Valor por defecto es "es"
- ❌ No valida que el idioma coincida con el input del usuario
- ❌ El comentario dice "Gemini handles multilingual" pero en realidad NO (usa lang por defecto)

---

### 4. **MCP Server - Responde en Español Siempre**

**Logs:**
```
[INFO] booking_agent:693 - 🔧 Executing: get_services({})
# MCP devuelve:
# Consulta General, Demostración de Producto, etc. (todo en español)
```

**Problema:**
- ✅ MCP server es configurado para español
- ❌ No respeta el contexto de idioma del usuario
- ❌ Las respuestas de MCP tools influyen en el contexto del agente
- ❌ El sistema cambia de inglés → español al recibir respuesta de MCP

---

## 📊 Flujo Actual (INCORRECTO)

```
1. Usuario escribe: "i want reserved" (INGLÉS)
   ↓
2. BaseAgent.__init__(language="es") → self.language = "es"
   ↓
3. agent_router classifica query (INGLÉS)
   ↓
4. booking_agent.generate_response() ejecuta:
   a. kwargs["user_lang"] = self.language  # "es"
   b. system_prompt = get_system_prompt(user_lang="es")
   c. MCP tools llaman a get_services()
   d. MCP devuelve servicios en ESPAÑOL
   ↓
5. Respuesta final: ESPAÑOL
   ❌ Cambio de idioma de inglés → español
```

---

## 🔧 Soluciones Propuestas

### OPCIÓN 1: Detección Automática de Idioma (RECOMENDADO) ⭐

**Implementar detección en tiempo real del idioma del usuario:**

```python
# src/gemini_agent/utils/language_detector.py (NUEVO)

from langdetect import detect, detect_langs
from typing import Literal

def detect_user_language(text: str) -> Literal["en", "es"]:
    """
    Detect user language from input text.

    Returns:
        "en" for English
        "es" for Spanish
        "es" as default if detection fails
    """
    try:
        lang_code = detect(text)
        return "en" if lang_code.startswith("en") else "es"
    except Exception as e:
        logger.warning(f"Language detection failed: {e}. Using default: es")
        return "es"

# Uso en booking_agent.py:

async def generate_response(self, query: str, **kwargs: Any) -> str:
    # Detectar idioma del usuario si no está especificado
    if "language" not in kwargs:
        detected_language = detect_user_language(query)
        self.logger.info(f"🌐 Detected user language: {detected_language}")
        kwargs["language"] = detected_language

    # ... resto del código
```

**Ventajas:**
- ✅ Automático y sin intervención manual
- ✅ Respeta el idioma del usuario
- ✅ Mantiene contexto consistente
- ✅ Mejora UX significativamente

**Desventajas:**
- ❌ Requiere librería adicional (`langdetect`)
- ❌ Puede fallar con textos muy cortos
- ❌ Pequeño overhead computacional

---

### OPCIÓN 2: Parámetro Explícito (RÁPIDO)

**El cliente/orquestador especifica el idioma:**

```python
# En el cliente o orchestrator:

response = await booking_agent.generate_response(
    query="i want reserved",
    language="en"  # ← Especificar explícitamente
)
```

**Ventajas:**
- ✅ Muy simple de implementar
- ✅ Sin dependencias adicionales
- ✅ Control total del cliente

**Desventajas:**
- ❌ Requiere que el cliente sepa el idioma
- ❌ Manual y propenso a errores
- ❌ No es automático

---

### OPCIÓN 3: Cambiar Default a "en" (NO RECOMENDADO)

```python
# base_agent.py
language: str = "en",  # Cambiar de "es" a "en"
```

**Ventajas:**
- ✅ Un cambio de una línea
- ✅ Simple

**Desventajas:**
- ❌ Rompe todos los usuarios en español
- ❌ No resuelve el problema real
- ❌ Solo mueve el problema al revés

---

### OPCIÓN 4: MCP Tools Multiidioma (FUTURO)

**Hacer que MCP server respete el idioma:**

```python
# mcp_handlers/booking_handlers.py

def get_services(language: str = "es") -> dict:
    """
    Get services in specified language.

    Args:
        language: "en" for English, "es" for Spanish

    Returns:
        Services list in requested language
    """
    if language == "en":
        return {
            "services": [
                {"name": "General Consultation", "duration": 30, "price": 50},
                ...
            ]
        }
    else:
        return {
            "services": [
                {"name": "Consulta General", "duration": 30, "price": 50},
                ...
            ]
        }
```

**Ventajas:**
- ✅ Solución completa y consistente
- ✅ MCP tools respetan idioma

**Desventajas:**
- ❌ Mayor complejidad
- ❌ Requiere cambios en MCP server
- ❌ Mantenimiento de traduccciones

---

## ✅ Recomendación Final

**COMBINAR OPCIÓN 1 + OPCIÓN 2:**

1. **Implementar detección automática** (Opción 1) como comportamiento por defecto
2. **Permitir override manual** (Opción 2) si el cliente quiere especificar idioma
3. **Mejorar MCP** (Opción 4) gradualmente en el futuro

### Implementación Propuesta:

```python
# en booking_agent.py

async def generate_response(self, query: str, **kwargs: Any) -> str:
    # Prioridad 1: Usar idioma explícito si se proporciona
    if "language" in kwargs:
        target_language = kwargs["language"]
        self.logger.info(f"🌐 Using explicit language: {target_language}")
    # Prioridad 2: Detectar idioma del query
    else:
        target_language = detect_user_language(query)
        self.logger.info(f"🌐 Auto-detected user language: {target_language}")

    # Actualizar self.language para mantener consistencia
    self.language = target_language
    kwargs["user_lang"] = target_language

    # ... resto del código
```

---

## 🎯 Impacto Esperado

### ANTES (Con Bug):
```
Usuario: "i want reserved" (INGLÉS)
↓
Sistema: "Perfecto. Aquí tienes los servicios..." (ESPAÑOL) ❌
Contexto perdido
```

### DESPUÉS (Con Fix):
```
Usuario: "i want reserved" (INGLÉS)
↓
Detección: language = "en"
↓
Sistema: "Perfect. Here are the services..." (INGLÉS) ✅
Contexto mantenido
```

---

## 📋 Checklist de Implementación

**FASE 1: Detección Automática (URGENTE)**
- [ ] Crear `src/gemini_agent/utils/language_detector.py`
- [ ] Implementar `detect_user_language()` con `langdetect`
- [ ] Agregar `langdetect` a requirements.txt
- [ ] Integrar en `booking_agent.generate_response()`
- [ ] Integrar en `sales_agent.generate_response()`
- [ ] Integrar en `general_agent.generate_response()`
- [ ] Testear con queries en inglés y español

**FASE 2: MCP Server Multiidioma (IMPORTANTE)**
- [ ] Actualizar MCP handlers para aceptar parámetro `language`
- [ ] Traducir respuestas de servicios
- [ ] Traducir respuestas de disponibilidad
- [ ] Traducir confirmaciones

**FASE 3: Logging y Monitoring (BUENA PRÁCTICA)**
- [ ] Agregar logging de detección de idioma
- [ ] Crear métricas de cambio de idioma
- [ ] Monitorear "language context loss" events

---

## 📝 Notas Técnicas

### Librería Recomendada: `langdetect`

```bash
pip install langdetect>=1.0.11
```

**Ventajas:**
- ✅ Preciso para inglés/español
- ✅ Funciona con textos cortos (>3 caracteres)
- ✅ Bajo overhead
- ✅ Bien mantenida

**Alternativas:**
- `textblob`: Más simple pero menos preciso
- `fasttext`: Muy preciso pero requiere modelo externo
- `spacy`: Overkill para solo 2 idiomas

---

## 🔗 Referencias Relacionadas

- `docs/CODE_REVIEW_REPORT.md` - Code review identificó problemas de manejo de idioma
- `src/gemini_agent/base_agent.py:115` - Donde se hardcodea el idioma
- `src/multi_agent/booking_agent.py:398` - Donde se usa el idioma

---

**Prioridad:** 🔴 CRÍTICO
**Tiempo Estimado:** 3-4 horas (Fase 1)
**Complejidad:** 🟡 MEDIA
**Status:** PENDIENTE DE IMPLEMENTACIÓN

