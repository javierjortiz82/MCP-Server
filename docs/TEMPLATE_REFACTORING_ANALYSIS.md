# Análisis de Refactorización: Mensajes Hardcodeados a Plantillas Jinja2

**Fecha**: 2025-11-19
**Autor**: Claude Code
**Estado**: Propuesta de Mejora

---

## 📋 Resumen Ejecutivo

### Problema Identificado
El archivo `agent/src/multi_agent/booking_agent.py` contiene **18 bloques de mensajes hardcodeados** con lógica bilingüe (español/inglés) directamente en el código Python.

### Impacto
- ❌ **Mantenibilidad**: Cambios de texto requieren modificar código Python
- ❌ **Escalabilidad**: Difícil agregar nuevos idiomas
- ❌ **Separación de Responsabilidades**: Lógica de negocio mezclada con contenido
- ❌ **Testing**: Difícil probar mensajes sin ejecutar todo el flujo
- ❌ **Reutilización**: Mensajes no reutilizables entre agentes

### Solución Propuesta
Migrar mensajes a sistema de plantillas Jinja2 existente, siguiendo el patrón ya establecido en `prompts/templates/base/booking_agent/`.

---

## 🔍 Inventario de Mensajes Hardcodeados

### 1. Mensajes de Autenticación (archivo: booking_agent.py)

| Línea | Contexto | Idiomas | Categoría |
|-------|----------|---------|-----------|
| 599-609 | Solicitud inicial de email | ES/EN | Auth - Email Request |
| 620-633 | Email inválido | ES/EN | Auth - Validation Error |
| 635-648 | Envío de OTP | ES/EN | Auth - OTP Request |
| 650-663 | OTP inválido | ES/EN | Auth - OTP Validation Error |
| 667-682 | Error al verificar OTP | ES/EN | Auth - OTP Verification Error |
| 685-695 | OTP incorrecto (intentos restantes) | ES/EN | Auth - OTP Retry |
| 780-789 | Solicitud de nombre (usuario nuevo) | ES/EN | Auth - Name Request |
| 792-847 | **Mensaje de bienvenida con menú** | ES/EN | Auth - Welcome + Menu |

### 2. Mensajes de Bienvenida Post-Registro (archivo: booking_agent.py)

| Línea | Contexto | Idiomas | Categoría |
|-------|----------|---------|-----------|
| 1223-1246 | Bienvenida con menú (nombre capturado) | ES/EN | Welcome - New User |

### 3. Mensajes de Sesión Expirada (archivo: booking_agent.py)

| Línea | Contexto | Idiomas | Categoría |
|-------|----------|---------|-----------|
| 862-872 | Sesión expirada | ES/EN | Session - Expired |
| 900-908 | No autenticado en flujo de auth | ES/EN | Session - Not Authenticated |
| 917-925 | Sesión activa pero sin autenticar | ES/EN | Session - Invalid State |
| 932-940 | Re-autenticación por cambio de usuario | ES/EN | Session - User Mismatch |

### 4. Mensajes de Estado de Autenticación (archivo: booking_agent.py)

| Línea | Contexto | Idiomas | Categoría |
|-------|----------|---------|-----------|
| 944-948 | Verificando autenticación | ES/EN | Status - Checking |
| 968-977 | Usuario diferente detectado | ES/EN | Status - User Changed |
| 982-988 | Error desconocido | ES/EN | Status - Unknown Error |

---

## 🏗️ Arquitectura Actual de Plantillas

### Estructura Existente
```
prompts/templates/base/booking_agent/
├── booking_agent.jinja2              # Plantilla principal
├── base.jinja2                       # Base template
└── modules/
    ├── authentication_flow.jinja2    # ✅ YA EXISTE - Flujo de auth
    ├── welcome_menu.jinja2           # ✅ YA EXISTE - Menú de bienvenida
    ├── user_registration_flow.jinja2 # ✅ YA EXISTE - Registro de usuario
    ├── ux_conversational.jinja2      # Pautas UX
    ├── scope_guardrails.jinja2       # Límites de alcance
    └── [otros 20+ módulos]           # Funcionalidad booking
```

### Sistema PromptManager
El `PromptManager` ya existe y soporta:
- ✅ Carga de templates Jinja2
- ✅ Detección automática de idioma (Gemini)
- ✅ A/B testing
- ✅ Versioning de prompts
- ✅ Caché de templates

---

## ❌ Problemas Específicos con Enfoque Actual

### Problema 1: Código Python Controla Mensajes Directos al Usuario

**Ubicación**: `booking_agent.py:_handle_auth_flow()`

**Código Actual**:
```python
if language == "en":
    return (
        "Excellent! Welcome, {user_full_name}!\n\n"
        "You're now authenticated! How can I help you today?\n\n"
        "📅 **Booking Options:**\n"
        "• Create a new appointment\n"
        # ... más opciones hardcodeadas
    )
else:
    return (
        "¡Excelente! ¡Bienvenido(a), {user_full_name}!\n\n"
        "¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?\n\n"
        # ... versión en español hardcodeada
    )
```

**Problema**:
- ❌ El código Python retorna el mensaje DIRECTAMENTE al usuario
- ❌ Bypasea completamente el sistema de prompts de Gemini
- ❌ No permite que Gemini adapte el tono o formato
- ❌ Inconsistente con el resto del flujo que usa Gemini

**Impacto**:
- 🔴 **CRÍTICO**: Esta es una violación arquitectural - El agente debe instruir a Gemini, no reemplazarlo

### Problema 2: Templates Ya Existen Pero No Se Usan

**Template Disponible**: `prompts/templates/base/booking_agent/modules/welcome_menu.jinja2`

**Contenido del Template** (líneas 46-70):
```jinja2
**Spanish:**
```
"¡Bienvenido(a), [full_name]! 👋

¿Qué te gustaría hacer hoy?

📌 Menú Principal:
1️⃣ Hacer una reserva
2️⃣ Ver mis reservas

Por favor, selecciona una opción (1 o 2) o escribe lo que necesitas."
```

**English:**
```
"Welcome, [full_name]! 👋

What would you like to do today?

📌 Main Menu:
1️⃣ Make a reservation
2️⃣ View my reservations

Please select an option (1 or 2) or type what you need."
```
```

**Estado**: ✅ **Template ya existe** pero el código Python lo ignora completamente

### Problema 3: Duplicación de Contenido

**Contenido en Template** (`authentication_flow.jinja2:200-202`):
```jinja2
respond_in_user_language(
    es=f"✅ ¡Sesión iniciada correctamente, {user_check['full_name']}!\n\n...",
    en=f"✅ Session started successfully, {user_check['full_name']}!\n\n..."
)
```

**Contenido en Código Python** (`booking_agent.py:792-847`):
```python
if language == "en":
    welcome_msg = f"Excellent! Welcome, {user_full_name}!\n\n"
else:
    welcome_msg = f"¡Excelente! ¡Bienvenido(a), {user_full_name}!\n\n"
```

**Problema**: El mismo mensaje de bienvenida existe en 2 lugares

---

## ✅ Solución Propuesta

### Enfoque: Hybrid Template System

En lugar de retornar mensajes directamente desde Python, el código debe:

1. **Instruir a Gemini** sobre qué hacer (vía system prompt)
2. **Dejar que Gemini genere** la respuesta usando las instrucciones
3. **Eliminar** todos los `return "mensaje..."` del código Python

### Arquitectura Propuesta

```python
# ❌ ANTES (Hardcoded):
def _handle_auth_flow(self, query: str, language: str = "es") -> str | None:
    if is_valid:
        if language == "en":
            return "Excellent! Welcome, ..."
        else:
            return "¡Excelente! ¡Bienvenido(a), ..."

# ✅ DESPUÉS (Template-based):
def _handle_auth_flow(self, query: str, language: str = "es") -> str | None:
    if is_valid:
        # NO RETORNAR MENSAJE - Dejar que Gemini lo maneje usando el prompt
        # El template authentication_flow.jinja2 ya contiene las instrucciones
        return None  # Indica que Gemini debe continuar con el flujo normal
```

### Cómo Funciona con Templates

**Template** (`authentication_flow.jinja2`):
```jinja2
### STEP 2B: Verify OTP Code

if result["success"]:
    # Show welcome message to user
    respond_in_user_language(
        es=f"✅ ¡Sesión iniciada correctamente, {full_name}!\\n\\n...",
        en=f"✅ Session started successfully, {full_name}!\\n\\n..."
    )

    proceed_to_welcome_menu(user_check)
```

**Código Python**:
```python
# Solo maneja la lógica, NO los mensajes
if verify_result["success"]:
    # Guardar autenticación
    self.save_session_auth(...)

    # Actualizar actividad
    self.update_session_activity(...)

    # NO retornar mensaje - Gemini usará el template
    return None
```

**Prompt que recibe Gemini**:
```
## 🔐 AUTHENTICATION FLOW

### STEP 2B: Verify OTP Code

if result["success"]:
    respond_in_user_language(
        es="✅ ¡Sesión iniciada correctamente, Juan Pérez!...",
        en="✅ Session started successfully, Juan Pérez!..."
    )
```

**Gemini genera**:
```
✅ ¡Sesión iniciada correctamente, Juan Pérez!

Tu última conexión fue el 17 de November de 2025 a las 03:27 PM.

¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?

📅 Opciones de Reserva:
• Crear una nueva cita
• Ver mis citas
...
```

---

## 📊 Plan de Migración

### Fase 1: Crear Nuevo Módulo de Mensajes (Recomendado)

**Archivo nuevo**: `prompts/templates/base/booking_agent/modules/auth_messages.jinja2`

**Contenido**:
```jinja2
{#
Authentication Messages Module
==============================
Centralized message templates for authentication flow responses.
Used by Gemini to generate user-facing messages during auth.

Version: 1.0.0
Author: Lab01-MCP Team
#}

## 🔐 AUTHENTICATION MESSAGES

### Welcome Message (After Successful OTP)

**Context**: User has successfully verified OTP and is now authenticated.

**Variables Available**:
- {{ user_full_name }} - User's full name
- {{ previous_login }} - ISO timestamp of last login (optional)
- {{ user_email }} - User's email address

**Spanish Template**:
```
¡Excelente! ¡Bienvenido(a), {{ user_full_name }}!

{% if previous_login %}
Tu última conexión fue el {{ previous_login | format_date('es') }}.
{% endif %}

¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?

📅 **Opciones de Reserva:**
• Crear una nueva cita
• Ver mis citas
• Reprogramar una cita
• Cancelar una cita
• Consultar horarios disponibles

¡Solo dime qué necesitas!
```

**English Template**:
```
Excellent! Welcome, {{ user_full_name }}!

{% if previous_login %}
Your last login was on {{ previous_login | format_date('en') }}.
{% endif %}

You're now authenticated! How can I help you today?

📅 **Booking Options:**
• Create a new appointment
• View my appointments
• Reschedule an appointment
• Cancel an appointment
• Check available time slots

Just tell me what you'd like to do!
```
```

### Fase 2: Modificar Código Python

**Cambio en `booking_agent.py`**:

```python
# ANTES:
if is_valid:
    # ... lógica de autenticación ...

    if language == "en":
        welcome_msg = f"Excellent! Welcome, {user_full_name}!\n\n..."
        return welcome_msg
    else:
        welcome_msg = f"¡Excelente! ¡Bienvenido(a), {user_full_name}!\n\n..."
        return welcome_msg

# DESPUÉS:
if is_valid:
    # ... lógica de autenticación ...

    # Inyectar variables en contexto para que Gemini las use
    self.save_memory_block("temp_previous_login", previous_login)

    # NO retornar mensaje - Gemini lo generará usando el template
    return None  # Continúa con generación normal de Gemini
```

### Fase 3: Actualizar PromptManager (Si Necesario)

Si se necesita pasar variables dinámicas al template:

```python
# prompts/manager.py
def get_booking_prompt(
    self,
    user_lang: str = "es",
    user_full_name: str | None = None,
    previous_login: str | None = None,
    **kwargs
) -> str:
    """Get booking agent prompt with dynamic data."""

    # Renderizar template con variables
    template_data = {
        "user_lang": user_lang,
        "user_full_name": user_full_name,
        "previous_login": previous_login,
        **kwargs
    }

    return self._render_template("base/booking_agent/booking_agent.jinja2", template_data)
```

---

## 📈 Beneficios de la Migración

| Aspecto | Antes (Hardcoded) | Después (Templates) |
|---------|-------------------|---------------------|
| **Mantenibilidad** | Editar código Python | Editar template Jinja2 |
| **Idiomas** | 2 (hardcoded) | N (configurables) |
| **Testing** | Requiere ejecutar flujo completo | Test template render independiente |
| **Consistencia** | Mensajes dispersos en código | Centralizados en templates |
| **Reutilización** | No reutilizable | Compartible entre agentes |
| **Versionado** | Mezclado con lógica | Independiente (A/B testing) |
| **UX Changes** | Cambio de código + deploy | Cambio de template only |

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: Romper Flujo Existente
**Mitigación**: Migración incremental por módulo, con tests en cada paso

### Riesgo 2: Pérdida de Control de Timing
**Mitigación**: Usar flags `return None` para indicar que Gemini debe continuar

### Riesgo 3: Inconsistencia de Mensajes
**Mitigación**: Templates contienen ejemplos exactos que Gemini debe seguir

---

## 📝 Recomendaciones Finales

### 1. **Enfoque Híbrido** (Recomendado)
- ✅ Mantener templates para **instrucciones a Gemini**
- ✅ Eliminar **retornos directos** de mensajes desde Python
- ✅ Dejar que **Gemini genere** las respuestas usando templates como guía

### 2. **No Crear Nuevo Sistema**
- ❌ NO crear sistema separado de "message templates"
- ✅ SÍ usar sistema Jinja2 existente para prompts

### 3. **Prioridad de Migración**
1. 🔴 **Alta**: Mensajes de bienvenida post-auth (lines 792-847, 1223-1246)
2. 🟡 **Media**: Mensajes de error de autenticación (lines 599-695)
3. 🟢 **Baja**: Mensajes de estado de sesión (lines 862-988)

### 4. **Casos Que DEBEN Quedarse en Python**
- ✅ Logs (logger.info, logger.warning, etc.)
- ✅ Valores de retorno para lógica de control (True/False, None)
- ✅ Llamadas a MCP tools
- ❌ Mensajes que el usuario final verá

---

## 🔬 Ejemplo Completo de Migración

### Código Actual (Problemático)
```python
# booking_agent.py:792-847
if language == "en":
    welcome_msg = f"Excellent! Welcome, {user_full_name}!\n\n"
    if previous_login:
        formatted_date = ...
        welcome_msg += f"Your last login was on {formatted_date}.\n\n"
    welcome_msg += (
        "You're now authenticated! How can I help you today?\n\n"
        "📅 **Booking Options:**\n"
        "• Create a new appointment\n"
        "• View my appointments\n"
        # ... más opciones
    )
    return welcome_msg  # ❌ PROBLEMA: Retorna mensaje directamente
```

### Template Propuesto
```jinja2
{# prompts/templates/base/booking_agent/modules/auth_messages.jinja2 #}

### Welcome After OTP Verification

When OTP is verified successfully, greet the user warmly:

**If user has previous login history:**
```
{% if language == "es" %}
¡Excelente! ¡Bienvenido(a), {{ full_name }}!

Tu última conexión fue el {{ previous_login | format_es_date }}.

¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?

📅 **Opciones de Reserva:**
• Crear una nueva cita
• Ver mis citas
• Reprogramar una cita
• Cancelar una cita
• Consultar horarios disponibles

¡Solo dime qué necesitas!
{% else %}
Excellent! Welcome, {{ full_name }}!

Your last login was on {{ previous_login | format_en_date }}.

You're now authenticated! How can I help you today?

📅 **Booking Options:**
• Create a new appointment
• View my appointments
• Reschedule an appointment
• Cancel an appointment
• Check available time slots

Just tell me what you'd like to do!
{% endif %}
```
```

### Código Migrado (Correcto)
```python
# booking_agent.py (refactored)
if is_valid:
    # Guardar datos en memoria para que Gemini los use
    self.save_memory_block("auth_user_full_name", user_full_name, priority=10)
    self.save_memory_block("auth_previous_login", previous_login, priority=10)

    # Limpiar flags de autenticación
    self._set_auth_flow_pending(False)

    # NO retornar mensaje - Gemini lo generará usando auth_messages.jinja2
    # El template ya tiene las instrucciones de cómo saludar al usuario
    return None
```

---

## 📚 Referencias

- **PromptManager**: `agent/src/multi_agent/prompt_manager.py`
- **Templates Existentes**: `prompts/templates/base/booking_agent/modules/`
- **Authentication Flow**: `authentication_flow.jinja2`
- **Welcome Menu**: `welcome_menu.jinja2`
- **Código Afectado**: `agent/src/multi_agent/booking_agent.py` (18 bloques)

---

## ✅ Siguiente Acción Recomendada

1. **Validar Propuesta** con el equipo
2. **Crear Template** `auth_messages.jinja2` con todos los mensajes
3. **Refactorizar** `_handle_auth_flow()` para eliminar retornos de mensajes
4. **Testing** en ambiente de desarrollo
5. **Deploy Incremental** por módulo

---

**Conclusión**: La migración a templates es **viable, recomendada y sigue el patrón existente**. El sistema de templates Jinja2 ya está en producción y solo requiere extender su uso para eliminar hardcoding de mensajes.
