# Data Flow - Cómo el General Agent Obtiene la Información
**Date**: 2025-11-03
**Status**: 📋 Analysis & Documentation

## 🎯 Respuesta Corta
El **General Agent** obtiene la información de **archivos YAML de configuración** (`business_info.yaml` y `policies.yaml`) ubicados en `prompts/data/`, que son cargados dinámicamente por el `PromptManager` y pasados al template Jinja2.

---

## 📊 Data Flow - Diagrama Completo

```
┌─────────────────────────────────────────────────────────────┐
│ CONFIGURACIÓN - ARCHIVOS YAML                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  prompts/data/                                              │
│  ├── business_info.yaml  ────→ Empresa, horarios, contacto │
│  ├── policies.yaml       ────→ Pagos, envío, devoluciones  │
│  └── demo_faqs.yaml      ────→ FAQs adicionales            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    (PromptManager._load_data)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PYTHON - PROMPT MANAGER                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  agent/src/multi_agent/prompt_manager.py                    │
│                                                              │
│  def get_general_prompt():                                  │
│      business = self._load_data("business_info.yaml")       │
│      policies = self._load_data("policies.yaml")            │
│      context = {                                            │
│          "business": business,      ┐                       │
│          "policies": policies,      ├─→ Contexto para      │
│          "version": "v1.0"          │   template Jinja2    │
│      }                              ┘                       │
│      return self._render_template(template_name, context)   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
         (Jinja2 template rendering with context)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ TEMPLATE - JINJA2                                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  prompts/templates/general_agent.jinja2                     │
│                                                              │
│  {% for item in business.categories %}                      │
│      - {{ item }}                                           │
│  {% endfor %}                                               │
│                                                              │
│  Métodos de pago aceptados:                                 │
│  {% for method in policies.payment_methods.accepted %}      │
│      ✅ {{ method }}                                        │
│  {% endfor %}                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
          (Rendered system prompt with actual data)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT - GENERAL AGENT                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  agent/src/multi_agent/general_agent.py                     │
│                                                              │
│  GeneralAgent.get_system_prompt():                          │
│      prompt = PromptManager().get_general_prompt()          │
│      return prompt  # Fully rendered system prompt          │
│                                                              │
│  This prompt is used by Gemini API as system instructions   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ GEMINI API                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Usa el system prompt para responder preguntas del usuario   │
│  Ej: "¿Cuál es tu horario?"                                 │
│       → Gemini responde con info de business_info.yaml      │
│                                                              │
│  Ej: "¿Puedo devolver un producto?"                         │
│       → Gemini responde con info de policies.yaml           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Archivos Involucrados - Detalle

### 1️⃣ **business_info.yaml** (Configuración de Empresa)
**Ubicación**: `prompts/data/business_info.yaml`

**Qué contiene**:
```yaml
# Información básica
company_name: "Lab01-MCP"
description: "Tienda especializada en tecnología..."
mission: "Ofrecer productos de calidad..."

# Operaciones
categories:
  - Computación
  - Audio
  - Hogar Inteligente

# Horarios
hours:
  "Lunes a Viernes": "9:00 AM - 6:00 PM"
  "Sábado": "10:00 AM - 2:00 PM"
  "Domingo": "Cerrado"

# Contacto
contact:
  email: "support@lab01-mcp.com"
  phone: "+1-555-LAB-0001"
  chat: "Disponible 24/7"
  social: "@Lab01MCP"
```

**Usado por template en**:
- `general_agent.jinja2` línea 30-46
- Mostrado en respuestas sobre: horarios, ubicación, contacto, información general

---

### 2️⃣ **policies.yaml** (Políticas de Empresa)
**Ubicación**: `prompts/data/policies.yaml`

**Qué contiene**:
```yaml
# Métodos de pago
payment_methods:
  accepted:
    - "Tarjetas de crédito"
    - "PayPal"
    - "Transferencias bancarias"
    - "Pago contra entrega"

# Envíos
shipping:
  standard: "5-7 días hábiles - GRATIS en >$100"
  express: "2-3 días hábiles - $15"
  priority: "1-2 días hábiles - $25"
  coverage: "Todo el país"

# Devoluciones
returns:
  period: "30 días desde la compra"
  condition: "Producto sin usar, empaque original"
  refund: "100% en compras defectuosas"

# Garantía
warranty:
  manufacturer: "Según producto (típicamente 1-3 años)"
  extended: "Disponible para compra"
  coverage: "Defectos de fabricación"
```

**Usada por template en**:
- `general_agent.jinja2` línea 100-150
- Mostrado en respuestas sobre: métodos de pago, envíos, devoluciones, garantía

---

### 3️⃣ **PromptManager** (Cargador de Datos)
**Ubicación**: `agent/src/multi_agent/prompt_manager.py`

**Método clave**:
```python
def _load_data(self, data_file: str) -> dict[str, Any]:
    """Carga archivo YAML desde prompts/data/"""
    data_path = self.data_dir / data_file
    with open(data_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data
```

**Método que llama a _load_data**:
```python
def get_general_prompt(...) -> str:
    # Cargar datos de archivos YAML
    business = self._load_data("business_info.yaml")
    policies = self._load_data("policies.yaml")

    # Pasar contexto al template
    context = {
        "business": business,
        "policies": policies,
        "version": version,
    }

    # Renderizar template con datos
    return self._render_template(template_name, context)
```

---

### 4️⃣ **general_agent.jinja2** (Template)
**Ubicación**: `prompts/templates/general_agent.jinja2`

**Cómo usa los datos**:
```jinja2
{# Accede a variables pasadas por PromptManager #}

INFORMACIÓN DE LA EMPRESA:
- Nombre: {{ business.company_name }}
- Descripción: {{ business.description }}
- Categorías: {{ business.categories|join(', ') }}

HORARIOS:
{% for day, hours in business.hours.items() %}
  - {{ day }}: {{ hours }}
{% endfor %}

MÉTODOS DE PAGO:
{% for method in policies.payment_methods.accepted %}
  ✅ {{ method }}
{% endfor %}

ENVÍOS:
- Estándar: {{ policies.shipping.standard.time }}
- Express: {{ policies.shipping.express.time }}
```

---

### 5️⃣ **GeneralAgent** (Usa el Prompt)
**Ubicación**: `agent/src/multi_agent/general_agent.py`

**Cómo obtiene el prompt**:
```python
class GeneralAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        """Obtiene el prompt del PromptManager"""
        if self._prompt_manager is None:
            self._prompt_manager = PromptManager()

        # El PromptManager ya tiene los datos YAML cargados
        return self._prompt_manager.get_general_prompt(
            user_lang=kwargs.get("user_lang", "es")
        )
```

---

## 🔄 Flujo Paso a Paso

### Paso 1: Usuario hace pregunta
```
Usuario: "¿Cuándo atienden?"
```

### Paso 2: GeneralAgent obtiene system prompt
```python
# En GeneralAgent.get_system_prompt()
prompt_manager = PromptManager()
system_prompt = prompt_manager.get_general_prompt()
```

### Paso 3: PromptManager carga datos YAML
```python
# En PromptManager.get_general_prompt()
business = self._load_data("business_info.yaml")  # ← Lee archivo
policies = self._load_data("policies.yaml")       # ← Lee archivo
```

### Paso 4: Renderiza template con datos
```python
# En PromptManager._render_template()
context = {
    "business": business,  # ← Datos del YAML
    "policies": policies,  # ← Datos del YAML
}
rendered_prompt = template.render(**context)
```

### Paso 5: Template genera prompt completo
```jinja2
{# El template ahora tiene variables disponibles #}
HORARIOS:
{% for day, hours in business.hours.items() %}
  - {{ day }}: {{ hours }}  ← Valores reales del YAML
{% endfor %}
```

### Paso 6: Gemini recibe el prompt completo
```
System Prompt (enviado a Gemini):
"Eres un asistente de información general...
HORARIOS:
- Lunes a Viernes: 9:00 AM - 6:00 PM
- Sábado: 10:00 AM - 2:00 PM
- Domingo: Cerrado
..."
```

### Paso 7: Gemini responde basado en el prompt
```
Gemini: "Atendemos de lunes a viernes de 9:00 AM a 6:00 PM,
         sábados de 10:00 AM a 2:00 PM, y cerramos los domingos.
         También estamos disponibles 24/7 a través de este chat."
```

---

## 🔑 Claves para Entender

### ✅ Los Datos NO están Hardcodeados
- ❌ No hay valores quemados en el código Python
- ✅ Todos los datos vienen de archivos YAML
- ✅ Cambiar un valor YAML = cambio inmediato en respuestas

### ✅ Template-Driven
- El template Jinja2 es la única fuente de verdad para la UI
- Los datos (business, policies) son dinámicos
- Los datos se cargan en tiempo de ejecución

### ✅ Escalable
- Agregar nueva política → Solo editar `policies.yaml`
- Cambiar horarios → Solo editar `business_info.yaml`
- No requiere cambios en código Python

---

## 📝 Cómo Actualizar la Información

### Cambiar Horarios
```yaml
# prompts/data/business_info.yaml
hours:
  "Lunes a Viernes": "9:00 AM - 6:00 PM"  ← Cambiar aquí
  "Sábado": "10:00 AM - 2:00 PM"          ← Cambiar aquí
```
→ Automáticamente el General Agent dirá nuevos horarios

### Cambiar Políticas de Envío
```yaml
# prompts/data/policies.yaml
shipping:
  standard:
    time: "5-7 días hábiles"        ← Cambiar aquí
    cost: "GRATIS en compras >$100" ← Cambiar aquí
```
→ Automáticamente el General Agent dirá nuevas políticas

### Cambiar Métodos de Pago
```yaml
# prompts/data/policies.yaml
payment_methods:
  accepted:
    - "Tarjetas de crédito"  ← Agregar/quitar aquí
    - "Criptomonedas"        ← Nueva opción
```
→ Automáticamente disponible en respuestas

---

## 🔐 Mantenibilidad

### Ventajas de esta Arquitectura

| Aspecto | Ventaja |
|--------|---------|
| **Cambios sin código** | Editar YAML, no Python |
| **Reutilizable** | Otros agentes pueden usar mismo datos |
| **Versionable** | Cada cambio YAML puede trackearse |
| **Testeable** | Fácil mockear datos YAML |
| **Escalable** | Agregar agentes sin duplicar datos |
| **DRY** | Una sola fuente de verdad |

---

## 📊 Archivos y Su Propósito

```
prompts/
├── data/                          # ← DATOS (YAML)
│   ├── business_info.yaml         # Empresa, horarios, contacto
│   ├── policies.yaml              # Políticas, pagos, envíos
│   └── demo_faqs.yaml             # FAQs adicionales
│
├── templates/                     # ← TEMPLATES (Jinja2)
│   ├── general_agent.jinja2       # UI para General Agent
│   ├── sales_agent/               # UI para Sales Agent
│   ├── booking_agent/             # UI para Booking Agent
│   └── router_classification.jinja2 # UI para Router
│
└── config/                        # ← CONFIGURACIÓN
    └── prompt_versions.yaml       # Versionamiento
```

---

## 🎯 Resumen

| Componente | Propósito | Ubicación |
|-----------|----------|-----------|
| **YAML Files** | Almacenar datos | `prompts/data/*.yaml` |
| **PromptManager** | Cargar datos YAML | `agent/src/multi_agent/prompt_manager.py` |
| **Templates** | Renderizar UI con datos | `prompts/templates/*.jinja2` |
| **GeneralAgent** | Usar prompt con Gemini | `agent/src/multi_agent/general_agent.py` |
| **Gemini API** | Responder preguntas | Google Cloud |

**FLUJO**: YAML → PromptManager → Template → GeneralAgent → Gemini → Respuesta

---

**Author**: Claude Code
**Last Updated**: 2025-11-03 19:30 UTC
**Status**: 📋 Documentation Complete
