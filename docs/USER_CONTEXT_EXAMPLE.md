# 🧠 User Context en Análisis de Sentimientos

## 📊 Descripción

El bot de Telegram ahora envía **contexto del usuario** al servicio de análisis de sentimientos para obtener evaluaciones más precisas y contextuales.

---

## 🔄 Cómo Funciona

### Tracking de Sesión

Cada sesión de usuario ahora rastrea:
- **`previous_sentiment`**: Sentimiento del mensaje anterior ("positive", "negative", "neutral")
- **`message_count`**: Número total de mensajes en la conversación

### Flujo de Análisis

```
Usuario envía mensaje 1
    ↓
user_context = {
    "previous_sentiment": "neutral",  # Primera vez
    "conversation_count": 0
}
    ↓
Sentiment Analysis → "positive"
    ↓
Session actualizada:
- previous_sentiment = "positive"
- message_count = 1

---

Usuario envía mensaje 2
    ↓
user_context = {
    "previous_sentiment": "positive",  # Del mensaje anterior
    "conversation_count": 1
}
    ↓
Sentiment Analysis → "negative"
    ↓
Session actualizada:
- previous_sentiment = "negative"
- message_count = 2
```

---

## 📝 Ejemplo Real

### Conversación Completa

**Mensaje 1:**
```
Usuario: "Hola, quiero comprar una laptop"
```

**Request al Sentiment Service:**
```json
{
  "text": "Hola, quiero comprar una laptop",
  "user_id": "telegram_123456789",
  "user_context": {
    "previous_sentiment": "neutral",
    "conversation_count": 0
  }
}
```

**Response:**
```json
{
  "polarity": ["neutral", 0.75],
  "emotion": ["curious", 0.68],
  "urgency_level": "low",
  "recommendation": "Continue normal conversation"
}
```

**Sesión actualizada:**
- `previous_sentiment` → "neutral"
- `message_count` → 1

---

**Mensaje 2:**
```
Usuario: "Necesito una urgentemente para trabajo"
```

**Request al Sentiment Service:**
```json
{
  "text": "Necesito una urgentemente para trabajo",
  "user_id": "telegram_123456789",
  "user_context": {
    "previous_sentiment": "neutral",
    "conversation_count": 1
  }
}
```

**Response:**
```json
{
  "polarity": ["neutral", 0.70],
  "emotion": ["urgent", 0.82],
  "urgency_level": "medium",
  "recommendation": "Prioritize response"
}
```

**Sesión actualizada:**
- `previous_sentiment` → "neutral"
- `message_count` → 2

---

**Mensaje 3:**
```
Usuario: "Ya llevo 3 días esperando y nadie me responde!"
```

**Request al Sentiment Service:**
```json
{
  "text": "Ya llevo 3 días esperando y nadie me responde!",
  "user_id": "telegram_123456789",
  "user_context": {
    "previous_sentiment": "neutral",
    "conversation_count": 2
  }
}
```

**Response:**
```json
{
  "polarity": ["negative", 0.92],
  "emotion": ["frustrated", 0.89],
  "urgency_level": "high",
  "recommendation": "Escalate to human support immediately"
}
```

**Acción del Bot:**
- ⚠️ Escalamiento activado (urgency_level = "high")
- Alerta enviada al grupo de soporte
- Sesión actualizada:
  - `previous_sentiment` → "negative"
  - `message_count` → 3

---

## 💡 Beneficios del Contexto

### Sin Contexto (Versión Anterior)

Cada mensaje se analiza independientemente:
```
Msg 1: "Hola" → neutral
Msg 2: "Necesito ayuda" → neutral
Msg 3: "Ya llevo días esperando!" → negative
```
❌ **No detecta escalada gradual de frustración**

### Con Contexto (Versión Actual)

El servicio ve el historial:
```
Msg 1: "Hola"
       → neutral (prev: neutral, count: 0)

Msg 2: "Necesito ayuda"
       → neutral (prev: neutral, count: 1)
       ⚠️ Servicio nota repetición de neutralidad + count aumentando

Msg 3: "Ya llevo días esperando!"
       → negative (prev: neutral, count: 2)
       🚨 Servicio detecta: cambio brusco + conversación larga + frustración
       → urgency_level: HIGH
```
✅ **Detecta patrones y escalada de frustración**

---

## 🔍 Logs Generados

### Logs del Bot

```
[INFO] [chat_id=123456789] Processing text message...
[INFO] [chat_id=123456789] Sentiment: neutral (0.75) | Emotion: curious (0.68) |
       Urgency: low | Context: prev=neutral, msg_count=0

[INFO] [chat_id=123456789] Processing text message...
[INFO] [chat_id=123456789] Sentiment: neutral (0.70) | Emotion: urgent (0.82) |
       Urgency: medium | Context: prev=neutral, msg_count=1

[INFO] [chat_id=123456789] Processing text message...
[INFO] [chat_id=123456789] Sentiment: negative (0.92) | Emotion: frustrated (0.89) |
       Urgency: high | Context: prev=neutral, msg_count=2
[WARNING] [chat_id=123456789] ⚠️ URGENT ESCALATION TRIGGERED | Urgency: high |
          Recommendation: Escalate to human support immediately
[INFO] [chat_id=123456789] Escalation alert sent to support group
```

---

## 🧪 Casos de Uso

### Caso 1: Cliente Impaciente

**Patrón:**
- Mensajes rápidos consecutivos
- Sentimiento neutral → neutral → negative
- `conversation_count` aumenta rápidamente

**Detección:**
- El servicio detecta múltiples mensajes en corto tiempo
- Cambia `urgency_level` a "medium" o "high"
- Bot puede responder más rápido o escalar

### Caso 2: Cliente Satisfecho que se Frustra

**Patrón:**
- positive → positive → negative
- `previous_sentiment` cambia de "positive" a "negative"

**Detección:**
- El servicio detecta cambio brusco de sentimiento
- Indica posible problema en el proceso
- Aumenta urgencia para retener cliente satisfecho

### Caso 3: Conversación Larga sin Resolución

**Patrón:**
- neutral → neutral → neutral... (10+ mensajes)
- `conversation_count` > 10

**Detección:**
- El servicio detecta conversación estancada
- Sugiere escalamiento o cambio de estrategia
- Evita frustración por falta de progreso

---

## 🔧 Implementación Técnica

### Session Class (chat_core/session_manager.py)

```python
@dataclass
class Session:
    session_id: str
    message_count: int = 0
    previous_sentiment: str = "neutral"

    def get_user_context(self) -> dict:
        return {
            "previous_sentiment": self.previous_sentiment,
            "conversation_count": self.message_count
        }

    def update_sentiment(self, sentiment: str) -> None:
        self.previous_sentiment = sentiment

    def increment_message_count(self) -> int:
        self.message_count += 1
        return self.message_count
```

### TelegramAdapter (_process_user_input)

```python
# Obtener contexto de la sesión
session = self.chat_core.session_manager.get_or_create_session(session_id, ...)
user_context = session.get_user_context()

# Enviar al servicio con contexto
sentiment_response = await sentiment.analyze(
    text=text,
    user_id=str(chat_id),
    user_context=user_context  # ← Nuevo parámetro
)

# Actualizar sesión después del análisis
session.update_sentiment(sentiment_response.polarity_label)
session.increment_message_count()
```

---

## 📊 Diferencia con Implementación Anterior

### Antes (analyze_simple)

```python
# Sin contexto
sentiment_response = await sentiment.analyze_simple(
    text=text,
    user_id=str(chat_id)
)

# Request enviado:
{
  "text": "Estoy molesto!",
  "user_id": "123456789"
}
```

### Ahora (analyze con contexto)

```python
# Con contexto completo
sentiment_response = await sentiment.analyze(
    text=text,
    user_id=str(chat_id),
    user_context=user_context  # ← Incluye historial
)

# Request enviado:
{
  "text": "Estoy molesto!",
  "user_id": "123456789",
  "user_context": {
    "previous_sentiment": "neutral",
    "conversation_count": 5
  }
}
```

---

## ✅ Ventajas

1. **Análisis más preciso**: El servicio entiende el contexto histórico
2. **Detección temprana**: Identifica escalada de frustración antes de ser crítica
3. **Mejor escalamiento**: Decisiones basadas en patrones, no solo mensaje actual
4. **Personalización**: Cada usuario tiene su propio contexto independiente

---

## 🚀 Próximos Pasos

El servicio de Sentiment ahora puede usar este contexto para:
- Ajustar umbrales de urgencia dinámicamente
- Detectar patrones de comportamiento
- Mejorar precisión del análisis con machine learning
- Personalizar respuestas según historial

---

**Implementado:** 2025-11-11
**Versión:** 2.1.0
