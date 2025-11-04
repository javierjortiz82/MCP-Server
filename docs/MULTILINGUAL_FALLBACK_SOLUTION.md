# Solución: Fallback Messages Multiidioma

**Problema**: El código de fallback está hardcodeado en español
```python
return (
    "Para ayudarte mejor, necesito conocer los servicios...\n\n"
    "Estoy obteniendo la lista de servicios que ofrecemos..."
)
```

**Por qué es un problema**:
- ❌ Hardcoded en español
- ❌ Rompe con patrón multiidioma del proyecto
- ❌ No respeta `self.language` del agente
- ❌ No usa sistema de traducción existente

---

## ✅ SOLUCIÓN CORRECTA (3 opciones)

### OPCIÓN 1: Usar PromptManager para Fallback Messages (RECOMENDADA)

**Patrón existente en el proyecto**: El `PromptManager` ya maneja multiidioma via Jinja2 templates.

**Implementación**:

```python
# En booking_agent.py

async def _create_fallback_response(self, iteration: int) -> str:
    """Create multilingual fallback response respecting current language.

    Uses PromptManager to load language-specific fallback messages
    from Jinja2 templates, ensuring consistency with system prompts.
    """
    try:
        # Load fallback message template based on current language
        prompt_manager = PromptManager()

        fallback_msg = prompt_manager.render_template(
            "fallback_messages.jinja2",
            language=self.language,
            iteration=iteration,
            agent_type="booking"
        )

        self.logger.info(
            f"✅ Loaded fallback message (lang={self.language}, iteration={iteration})"
        )
        return fallback_msg

    except Exception as e:
        # Graceful fallback if template loading fails
        self.logger.warning(
            f"Failed to load fallback template: {e}. Using generic message."
        )
        return self._get_generic_fallback(iteration)

def _get_generic_fallback(self, iteration: int) -> str:
    """Generic fallback messages with basic language support."""
    messages = {
        "es": {
            1: "Para ayudarte mejor, necesito más información.\n\nIntentemos de nuevo.",
            2: "Parece que hay un problema técnico. Intenta reformular tu pregunta.",
        },
        "en": {
            1: "To help you better, I need more information.\n\nLet's try again.",
            2: "There seems to be a technical issue. Please rephrase your question.",
        },
    }

    lang_msgs = messages.get(self.language, messages["es"])
    return lang_msgs.get(iteration, lang_msgs[1])
```

**Crear template**: `prompts/templates/base/fallback_messages.jinja2`

```jinja2
{# Multilingual Fallback Messages for All Agents #}
{% if language == "es" %}

{% if iteration == 1 and agent_type == "booking" %}
Para ayudarte mejor, necesito conocer los servicios disponibles.

Estoy obteniendo la lista de servicios que ofrecemos...
{% elif iteration >= 2 %}
Parece que hay un problema técnico. Por favor, intenta reformular tu pregunta con más detalles.
{% else %}
No pude procesar tu solicitud completamente. Intenta de nuevo con más información.
{% endif %}

{% elif language == "en" %}

{% if iteration == 1 and agent_type == "booking" %}
To help you better, I need to know what services are available.

I'm getting the list of services we offer...
{% elif iteration >= 2 %}
There seems to be a technical issue. Please try rephrasing your question with more details.
{% else %}
I couldn't fully process your request. Please try again with more information.
{% endif %}

{% endif %}
```

---

### OPCIÓN 2: Diccionario de Mensajes (ALTERNATIVA SIMPLE)

**Para cuando PromptManager no sea viable**:

```python
class BookingAgent(BaseAgent):

    # Mensajes fallback multiidioma - constantes de clase
    FALLBACK_MESSAGES = {
        "es": {
            "first_attempt_booking": (
                "Para ayudarte mejor, necesito conocer los servicios disponibles.\n\n"
                "Estoy obteniendo la lista de servicios que ofrecemos..."
            ),
            "second_attempt": (
                "Parece que hay un problema técnico. "
                "Por favor, intenta reformular tu pregunta con más detalles."
            ),
            "generic": (
                "No pude procesar tu solicitud completamente. "
                "Intenta de nuevo con más información."
            ),
        },
        "en": {
            "first_attempt_booking": (
                "To help you better, I need to know what services are available.\n\n"
                "I'm getting the list of services we offer..."
            ),
            "second_attempt": (
                "There seems to be a technical issue. "
                "Please try rephrasing your question with more details."
            ),
            "generic": (
                "I couldn't fully process your request. "
                "Please try again with more information."
            ),
        },
    }

    def _create_fallback_response(self, iteration: int) -> str:
        """Create fallback response respecting language setting."""
        lang_messages = self.FALLBACK_MESSAGES.get(
            self.language,
            self.FALLBACK_MESSAGES["es"]  # Fallback a español si idioma no existe
        )

        if iteration == 1:
            return lang_messages.get("first_attempt_booking", lang_messages["generic"])
        elif iteration >= 2:
            return lang_messages.get("second_attempt", lang_messages["generic"])
        else:
            return lang_messages["generic"]
```

---

### OPCIÓN 3: gettext Module (ENTERPRISE LEVEL)

**Para proyectos con muchos idiomas y mantenimiento profesional**:

```python
import gettext

class BookingAgent(BaseAgent):

    def __init__(self, ...):
        super().__init__(...)

        # Cargar traductor según idioma del agente
        lang_dir = Path(__file__).parent / "locales"
        try:
            translation = gettext.translation(
                'booking_agent',
                localedir=lang_dir,
                languages=[self.language]
            )
            self._ = translation.gettext
        except FileNotFoundError:
            # Fallback si traducción no existe
            self._ = lambda x: x

    def _create_fallback_response(self, iteration: int) -> str:
        """Create multilingual fallback using gettext."""
        if iteration == 1:
            return self._(
                "To help you better, I need to know what services are available.\n\n"
                "I'm getting the list of services we offer..."
            )
        elif iteration >= 2:
            return self._(
                "There seems to be a technical issue. "
                "Please try rephrasing your question with more details."
            )
        else:
            return self._("I couldn't fully process your request.")
```

---

## 🎯 COMPARACIÓN DE OPCIONES

| Aspecto | Opción 1 (PromptManager) | Opción 2 (Dict) | Opción 3 (gettext) |
|--------|-------------------------|-----------------|------------------|
| **Align con Proyecto** | ✅ Excelente | ✅ Bueno | ⚠️ Overkill |
| **Multiidioma** | ✅ Completo | ✅ Completo | ✅ Completo |
| **Mantenibilidad** | ✅ Alta | ⚠️ Media | ⚠️ Baja (requiere compilación) |
| **Complejidad** | ⚠️ Media | ✅ Baja | ❌ Alta |
| **Performance** | ⚠️ Template rendering | ✅ O(1) dict lookup | ✅ O(1) |
| **Escalabilidad** | ✅ Excelente | ⚠️ No para 10+ idiomas | ✅ Excelente |

---

## 🔧 CÓDIGO CORREGIDO (Opción 1 - RECOMENDADA)

**Archivo**: `agent/src/multi_agent/booking_agent.py`

**Reemplazar**:
```python
# ❌ ANTES (hardcoded)
if parts is None:
    self.logger.warning(
        f"⚠️ Response parts is None (iteration {iteration}) - Gemini API issue detected"
    )
    # ... código ...
    elif iteration == 1:
        # First attempt - helpful suggestion
        return (
            "Para ayudarte mejor, necesito conocer los servicios...\n\n"
            "Estoy obteniendo la lista de servicios que ofrecemos..."
        )
```

**Con**:
```python
# ✅ DESPUÉS (multiidioma)
if parts is None:
    self.logger.warning(
        f"⚠️ Response parts is None (iteration {iteration}) - Gemini API issue detected"
    )
    # Log diagnostic information
    if response.candidates:
        candidate = response.candidates[0]
        self.logger.debug(
            f"Response diagnostic - candidate.content: {candidate.content}, "
            f"finish_reason: {candidate.finish_reason}"
        )

    # Try to extract text and use as recovery
    try:
        content = response.candidates[0].content if response.candidates else None
        text = self.function_call_handler.extract_text_from_content(content)
        if text and len(text.strip()) > 10:
            # Got meaningful text, use it
            self.logger.debug(f"✅ Extracted text from content: {text[:100]}...")
            return text
    except (AttributeError, IndexError) as e:
        self.logger.warning(f"Failed to extract text from content: {e}")

    # Use multilingual fallback response
    self.logger.info(f"Using fallback response for iteration {iteration}")
    return self._create_fallback_response(iteration)
```

**Actualizar método fallback**:
```python
def _create_fallback_response(self, iteration: int) -> str:
    """Create multilingual fallback response.

    Args:
        iteration: Current iteration number

    Returns:
        Language-appropriate fallback message
    """
    # Mensajes multiidioma
    messages = {
        "es": {
            "first_attempt_booking": (
                "Para ayudarte mejor, necesito conocer los servicios disponibles.\n\n"
                "Estoy obteniendo la lista de servicios que ofrecemos..."
            ),
            "second_attempt": (
                "Parece que hay un problema técnico. "
                "Por favor, intenta reformular tu pregunta con más detalles."
            ),
            "generic": (
                "No pude procesar tu solicitud completamente. "
                "Intenta de nuevo con más información."
            ),
        },
        "en": {
            "first_attempt_booking": (
                "To help you better, I need to know what services are available.\n\n"
                "I'm getting the list of services we offer..."
            ),
            "second_attempt": (
                "There seems to be a technical issue. "
                "Please try rephrasing your question with more details."
            ),
            "generic": (
                "I couldn't fully process your request. "
                "Please try again with more information."
            ),
        },
    }

    # Get messages for current language (fallback to Spanish if not found)
    lang_messages = messages.get(self.language, messages["es"])

    # Select message based on iteration
    if iteration == 1:
        return lang_messages.get("first_attempt_booking", lang_messages["generic"])
    elif iteration >= 2:
        return lang_messages.get("second_attempt", lang_messages["generic"])
    else:
        return lang_messages["generic"]
```

---

## 🧪 Testing Multiidioma

```python
# Test Spanish
agent_es = BookingAgent(..., language="es")
assert "necesito conocer los servicios" in await agent_es.generate_response("quiero reservar")

# Test English
agent_en = BookingAgent(..., language="en")
assert "services are available" in await agent_en.generate_response("I want to book")
```

---

## ✅ CHECKLIST

- [ ] Actualizar `booking_agent.py` con mensajes multiidioma
- [ ] Implementar `_create_fallback_response()` con diccionario
- [ ] Actualizar `sales_agent.py` similarmente
- [ ] Agregar tests para ambos idiomas
- [ ] Documentar en NOTAS_CLAUDE.md el patrón
- [ ] Considerar extender a otros agentes

---

## 📝 CONCLUSIÓN

**Opción recomendada**: **Opción 2 (Diccionario)** por:
- ✅ Simple de implementar
- ✅ Respeta patrón del proyecto (usar self.language)
- ✅ No requiere cambios en infraestructura
- ✅ Fácil de mantener
- ✅ Performance óptima

El código hardcodeado será reemplazado con un diccionario multiidioma que respete `self.language` como lo hace el resto del sistema.
