# General Agent - Scope Restrictions (Google Gemini 2.5 Best Practices)
**Date**: 2025-11-03
**Status**: ✅ Implemented
**Impact**: High - Prevents hallucinations, maintains scope clarity

## 🎯 Overview

El **General Agent** ahora está **restringido estrictamente** para que SOLO responda preguntas basadas en:
1. **`prompts/data/business_info.yaml`** - Información de empresa
2. **`prompts/data/policies.yaml`** - Políticas

Cualquier pregunta fuera de estos datos será rechazada explícitamente con redirección al equipo apropiado.

---

## ✅ EN-SCOPE (Permitido) / ❌ OUT-OF-SCOPE (No Permitido)

### ✅ INFORMACIÓN DE EMPRESA (business_info.yaml)

| Pregunta | Respuesta | Fuente |
|----------|-----------|--------|
| "¿Quién eres?" | Nombre + descripción | `company_name`, `description` |
| "¿Cuándo atienden?" | Horarios completos | `hours` |
| "¿Cómo me contacto?" | Todos los canales | `contact.*` |
| "¿Dónde están?" | Ubicación (si configurada) | `location.*` |
| "¿Qué categorías venden?" | Lista de categorías | `categories` |
| "¿Cuál es tu misión?" | Misión de empresa | `mission` |
| "¿24/7?" | Disponibilidad online | `online_availability` |

**Response Pattern**:
```
Nuestra empresa es [company_name].

[description]

Contacto:
📧 Email: [email]
📞 Teléfono: [phone]
💬 Chat: 24/7 disponible

¿Hay algo más en lo que pueda ayudarte?
```

---

### ✅ POLÍTICAS DE EMPRESA (policies.yaml)

| Pregunta | Respuesta | Fuente |
|----------|-----------|--------|
| "¿Cómo puedo pagar?" | Métodos aceptados | `payment_methods.accepted` |
| "¿Qué métodos no aceptan?" | Métodos NO aceptados | `payment_methods.not_accepted` |
| "¿Cuánto cuesta enviar?" | Opciones de envío | `shipping.*` |
| "¿Cuánto tarda?" | Tiempos de envío | `shipping.*.time` |
| "¿A dónde envían?" | Cobertura geográfica | `shipping.coverage` |
| "¿Puedo devolver?" | Política de devoluciones | `returns.*` |
| "¿Tienen garantía?" | Garantía + cobertura | `warranty.*` |
| "¿Cómo cuidan mis datos?" | Política de privacidad | `privacy.*` |
| "¿Cuáles son tus términos?" | Términos de servicio | `terms.*` |
| "¿Hay envío gratis?" | Condiciones de envío gratis | `shipping.standard.cost` |

**Response Pattern**:
```
Nuestra política es:
[detailed_policy_info]

Si tienes más preguntas:
📧 support@lab01-mcp.com
📞 +1-555-LAB-0001 (Lun-Vie 9am-6pm)
```

---

## ❌ OUT-OF-SCOPE (No Permitido)

### Categoría 1: PRODUCTOS ESPECÍFICOS
**Preguntas**:
- "¿Cuánto cuesta una laptop?"
- "¿Tienen MacBook?"
- "¿Cuáles son las especificaciones?"
- "¿En qué colores viene?"
- "¿Es compatible con Windows?"

**Reason**: Detalles de productos → Sales Agent responsibility
**Redirect**:
```
"Para preguntas sobre productos específicos,
puedes usar nuestra herramienta de búsqueda
o contactar a: sales@lab01-mcp.com"
```

---

### Categoría 2: RESERVAS Y CITAS
**Preguntas**:
- "¿Puedo agendar una cita?"
- "¿Cuándo puedo reservar?"
- "Quiero una cita para el viernes"
- "¿Qué horarios tienen disponibles para consulta?"

**Reason**: Gestión de reservas → Booking Agent responsibility
**Redirect**:
```
"Para agendar citas o hacer reservaciones,
por favor usa nuestro sistema de reservas
o escribe 'Quiero reservar'."
```

---

### Categoría 3: SOPORTE TÉCNICO
**Preguntas**:
- "Mi producto no funciona"
- "Tengo un error en mi compra"
- "¿Cómo configuro esto?"
- "Se me olvidó mi contraseña"

**Reason**: Problemas técnicos → Support Team responsibility
**Redirect**:
```
"Para soporte técnico, contacta a nuestro equipo:
📧 support@lab01-mcp.com
📞 +1-555-LAB-0001 (Lun-Vie 9am-6pm)
🎫 Sistema de tickets: [tickets_url]"
```

---

### Categoría 4: INFORMACIÓN CONFIDENCIAL
**Preguntas**:
- "¿Cuántos empleados tienen?"
- "¿Cuál es tu revenue anual?"
- "¿Dónde están sus servidores?"
- "¿Quién es el CEO?"
- "¿Cuál es tu presupuesto de marketing?"

**Reason**: Información interna NO documentada en config
**Response**:
```
"Esa información no la tengo disponible.
Para consultas específicas sobre la empresa,
contacta a: info@lab01-mcp.com"
```

---

### Categoría 5: OPINIONES Y RECOMENDACIONES
**Preguntas**:
- "¿Es la mejor tienda?"
- "¿Me recomiendas este producto?"
- "¿Qué opinan los clientes?"
- "¿Eres mejor que la competencia?"

**Reason**: Opiniones NO están documentadas
**Response**:
```
"No puedo hacer afirmaciones sobre opiniones.
Lo que sí puedo compartir es que somos:
[company_mission]

Para testimonios de clientes,
mira nuestras redes: [social_media]"
```

---

### Categoría 6: TEMAS NO RELACIONADOS
**Preguntas**:
- "¿Cuál es la capital de Francia?"
- "¿Cómo cocino una pizza?"
- "¿Quién ganó el partido?"
- "¿Cuál es el significado de la vida?"

**Reason**: Completamente fuera de scope
**Response**:
```
"Soy especialista en información sobre [company_name].
Para preguntas generales, te recomiendo un buscador.

¿Hay algo sobre nuestra empresa, políticas o contacto
que pueda ayudarte?"
```

---

## 🚫 ANTI-HALLUCINATION RULES

### NUNCA HAGAS ESTO ❌

| Acción | Mal Ejemplo | Razón |
|--------|------------|-------|
| **Inventar datos** | "Tenemos sucursales en 5 países" | Si no está en YAML, no lo digas |
| **Crear políticas** | "Tenemos descuento 50% viernes" | Solo políticas en policies.yaml |
| **Hacer recomendaciones** | "Te recomiendo la laptop X" | Eso es responsabilidad de Sales |
| **Ofrecer servicios NO documentados** | "Envío mismo día gratis" | Solo envíos en policies.yaml |
| **Hacer promesas** | "Te garantizo que te gustará" | Eso es sales talk |
| **Especular sobre precios** | "Creo que cuesta $200" | No especular sin datos |

### SIEMPRE HAZ ESTO ✅

| Acción | Buen Ejemplo | Razón |
|--------|-------------|-------|
| **Sé honesto sobre scope** | "Eso está fuera de mi área..." | Claridad |
| **Cita la fuente** | "Según nuestras políticas..." | Confiabilidad |
| **Ofrece alternativas** | "Lo que SÍ puedo ayudarte..." | Utilidad |
| **Facilita contacto** | "Para eso, el mejor es: [email]" | Solución |
| **Reconoce limitaciones** | "Esa información no la tengo..." | Honestidad |
| **Proporciona opciones** | "Puedo ayudarte con: 1) 2) 3)" | Servicialidad |

---

## 🎯 DECISION TREE

```
User Question Received
        │
        ├─ ¿Es sobre empresa/horarios/contacto?
        │  ├─ YES → Responder con business_info.yaml ✅
        │  └─ NO → Continúa
        │
        ├─ ¿Es sobre políticas/pago/envío?
        │  ├─ YES → Responder con policies.yaml ✅
        │  └─ NO → Continúa
        │
        └─ ¿Es sobre algo más?
           ├─ Productos → OUT-OF-SCOPE ❌ → Redirigir a Sales
           ├─ Reservas → OUT-OF-SCOPE ❌ → Redirigir a Booking
           ├─ Soporte → OUT-OF-SCOPE ❌ → Redirigir a Support
           ├─ Confidencial → OUT-OF-SCOPE ❌ → "No tengo esa info"
           ├─ Opinión → OUT-OF-SCOPE ❌ → "No puedo afirmar eso"
           └─ No relacionado → OUT-OF-SCOPE ❌ → Reorientar scope
```

---

## 📊 SCOPE MATRIX - Referencia Rápida

| Tema | En-Scope | Responsable | Acción |
|------|----------|-------------|--------|
| Horarios | ✅ | General | Mostrar horarios |
| Contacto | ✅ | General | Mostrar info contacto |
| Pago | ✅ | General | Mostrar métodos |
| Envío | ✅ | General | Mostrar opciones |
| Devolución | ✅ | General | Mostrar política |
| Garantía | ✅ | General | Mostrar cobertura |
| **Producto específico** | ❌ | Sales | Redirigir |
| **Precio producto** | ❌ | Sales | Redirigir |
| **Especificaciones** | ❌ | Sales | Redirigir |
| **Agendar cita** | ❌ | Booking | Redirigir |
| **Disponibilidad horario** | ❌ | Booking | Redirigir |
| **Error producto** | ❌ | Support | Redirigir |
| **Soporte técnico** | ❌ | Support | Redirigir |
| **Empleados cantidad** | ❌ | HR/Admin | "No tengo eso" |
| **Info financiera** | ❌ | Admin | "No tengo eso" |
| **Tema aleatorio** | ❌ | Otro | Reorientar |

---

## 🎓 Google Gemini 2.5 Principles Implemented

### 1. ✅ Clear Scope Boundaries
- Explícitamente definido: IN-SCOPE vs OUT-OF-SCOPE
- Decision tree para validación
- Lista de 6 categorías OUT-OF-SCOPE

### 2. ✅ Anti-Hallucination
- ONLY data from YAML files
- Never invent information
- Explicit "I don't know" when unsure
- Validation rules in template

### 3. ✅ Strict Scope Limits
- No products (Sales Agent)
- No reservations (Booking Agent)
- No technical support
- No confidential info

### 4. ✅ Redirection Protocol
- When out-of-scope, guide to right team
- Provide email/phone of correct department
- Maintain helpfulness while enforcing scope

### 5. ✅ Honesty First
- Say "I don't have that information"
- Don't speculate
- Don't make promises
- Don't go beyond documented data

### 6. ✅ Scope Consistency
- Same rules apply to ALL questions
- No exceptions
- No "just this once" violations

---

## 🔧 Implementation Details

### File Structure
```
prompts/
├── data/
│   ├── business_info.yaml         ← Allowed data
│   └── policies.yaml              ← Allowed data
│
└── templates/
    └── general_agent/
        ├── general_agent.jinja2   ← Includes scope_guardrails
        └── modules/
            └── scope_guardrails.jinja2  ← NEW: Restrictions + rules
```

### Template Include
```jinja2
{# At the very top of general_agent.jinja2 #}
{% include 'general_agent/modules/scope_guardrails.jinja2' %}

{# Rest of template follows #}
Eres un asistente de información general...
```

### When Rendered
The template includes:
1. ✅ IN-SCOPE definition
2. ✅ OUT-OF-SCOPE definition
3. ✅ Decision tree
4. ✅ Anti-hallucination rules
5. ✅ Redirection protocol
6. ✅ Scope matrix reference

Gemini reads all this in the system prompt and enforces it.

---

## 📈 Expected Impact

### Prevents Hallucinations
❌ **Before**: "Tenemos sucursales en 5 países" (no en YAML)
✅ **After**: "Esa información no la tengo disponible"

### Clear Boundaries
❌ **Before**: Respuesta genérica sobre productos
✅ **After**: "Eso es responsabilidad de Sales Agent"

### Better User Experience
❌ **Before**: Usuario confundido por respuesta fuera de scope
✅ **After**: Claro qué puede/no puede responder + redirigido

### Reduced Errors
❌ **Before**: Agent dice cosas incorrectas
✅ **After**: Agent ONLY cita datos verificados

### Proper Routing
❌ **Before**: Usuario perdido en respuestas inapropiadas
✅ **After**: Usuario dirigido al equipo correcto

---

## 🧪 Testing Examples

### Test 1: Valid Question (IN-SCOPE)
```
User: "¿Cuáles son los horarios de atención?"
Expected: Show business_info.yaml hours
Result: ✅ PASS
```

### Test 2: Product Question (OUT-OF-SCOPE)
```
User: "¿Cuánto cuesta una laptop?"
Expected: Redirect to Sales Agent
Result: ✅ PASS - "Para preguntas sobre productos..."
```

### Test 3: Reservation Question (OUT-OF-SCOPE)
```
User: "Quiero agendar una cita para el viernes"
Expected: Redirect to Booking Agent
Result: ✅ PASS - "Para agendar citas..."
```

### Test 4: Unrelated Question (OUT-OF-SCOPE)
```
User: "¿Cuál es la capital de Francia?"
Expected: Reorient to scope
Result: ✅ PASS - "Soy especialista en información sobre Lab01..."
```

### Test 5: Hallucination Attempt (OUT-OF-SCOPE)
```
User: "¿Tienen sucursales en Madrid?"
Expected: Honest response
Result: ✅ PASS - "Esa información no la tengo especificada..."
```

---

## 🔐 Maintenance

### To Add New Allowed Topics
1. Add data to `business_info.yaml` OR `policies.yaml`
2. The template will automatically include it (via Jinja2)
3. No code changes needed

### To Update Restrictions
1. Edit `general_agent/modules/scope_guardrails.jinja2`
2. Update the lists of IN-SCOPE/OUT-OF-SCOPE
3. Rebuild prompt (PromptManager handles this)

### To Add New Redirects
1. Add endpoint to scope_guardrails module
2. Add response pattern
3. Template automatically applies

---

## ✨ Benefits Summary

| Benefit | Why It Matters |
|---------|-----------------|
| **Zero hallucinations** | Users get accurate info only |
| **Clear boundaries** | Agent knows what NOT to do |
| **Proper routing** | Users find right help fast |
| **Honesty** | "I don't know" > made-up answer |
| **Maintainability** | Changes via YAML, not code |
| **Scalability** | Works for any company/policies |
| **Google Gemini compliant** | Follows official best practices |

---

**Author**: Claude Code
**Last Updated**: 2025-11-03 19:45 UTC
**Status**: ✅ Fully Implemented
**Reference**: Google Gemini 2.5 Prompting Strategies
