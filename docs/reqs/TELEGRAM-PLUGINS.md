# 🧠 Prompt Técnico: Extensión del Bot de Telegram para Procesamiento Multimedia con Endpoints ASR, OCR y Sentiment

Eres un ingeniero senior especializado en **bots de Telegram en Python** (basados en `python-telegram-bot` v20+ con `asyncio`).  
Tu misión es **extender un bot existente que actualmente solo procesa texto**, para que pueda aceptar y manejar entradas multimedia (voz, imágenes, documentos) y convertirlas a texto antes de continuar con el flujo normal de conversación con el agente IA.

---

## 🎯 Objetivo general

El bot **ya tiene un flujo funcional de conversación basado en texto**.  
Tu tarea consiste en que **todas las entradas no textuales (audio, imágenes, documentos)** sean convertidas a texto usando los servicios externos disponibles, y luego sigan **exactamente el mismo flujo actual** de procesamiento de texto.

---

## 🧩 Nuevos tipos de entrada a soportar

1. **Mensajes de texto** → se procesan igual que hoy.  
2. **Mensajes de voz o audio (`voice`)** → convertir a texto con el servicio ASR.  
3. **Fotos (`photo`) o documentos (`document`)** → convertir a texto con el servicio OCR.  
4. **Todo texto obtenido (de cualquier origen)** → analizar sentimientos con el servicio Sentiment antes de responder.

El flujo base de texto **no debe modificarse**, solo integrarse en una función común de procesamiento:  
```python
async def process_user_input(text: str, chat_id: str)
```

---

## ⚙️ Servicios externos disponibles

### 1. 🎤 Voice-ASR Service — *Transcripción de voz a texto*
**URL:** `http://localhost:8002/transcribe`  
**Método:** `POST` (Multipart Form-Data)

**Campos del Form Data:**
| Campo | Tipo | Descripción |
|-------|------|--------------|
| `audio_file` | Binary (.ogg) | Archivo de audio recibido desde Telegram |
| `client_id` | String | Identificador del usuario (chat_id) |
| `language_hint` | String | Idioma sugerido (`"en"`, `"es"`, etc.) |
| `quality_preference` | String | `"fast"`, `"balanced"`, `"accurate"` |
| `X-Request-ID` | Header | UUID único por request |

**Ejemplo de request (Python):**
```python
files = {'audio_file': ('voice_message.ogg', audio_bytes, 'audio/ogg')}
data = {
    'client_id': chat_id,
    'language_hint': 'en',
    'quality_preference': 'balanced'
}
headers = {'X-Request-ID': str(uuid.uuid4())}
response = await http_client.post("http://localhost:8002/transcribe", files=files, data=data, headers=headers)
```

**Ejemplo de respuesta exitosa:**
```json
{
  "success": true,
  "data": {
    "transcription": "Hello, I want to buy a laptop",
    "language": "en",
    "confidence": 0.95
  }
}
```

**Ejemplo de error:**
```json
{
  "success": false,
  "error": "Transcription failed: audio quality too low",
  "error_code": "LOW_QUALITY"
}
```

---

### 2. 📄 OCR-Multilang Service — *Extracción de texto desde documentos o imágenes*
**URL:** `http://localhost:8004/extract`  
**Método:** `POST` (`application/x-www-form-urlencoded`)

**Campos esperados:**
| Campo | Tipo | Descripción |
|-------|------|--------------|
| `file_data` | Base64 string | Contenido del archivo codificado |
| `file_type` | String | `"pdf"`, `"jpg"`, `"png"`, `"docx"` |
| `client_id` | String | `"sales_agent"` o `chat_id` |
| `quality` | String | `"fast"`, `"balanced"`, `"accurate"` |
| `language_hints` | String | `"en,es"` (opcional) |

**Ejemplo de request (Python):**
```python
form_data = {
    "file_data": base64.b64encode(file_bytes).decode("utf-8"),
    "file_type": "pdf",
    "client_id": chat_id,
    "quality": "balanced"
}
response = await http_client.post("http://localhost:8004/extract", data=form_data, headers={"Accept": "application/json"})
```

**Ejemplo de respuesta exitosa:**
```json
{
  "success": true,
  "text": "Product Catalog\nLaptop Gaming XYZ\nPrice: $1,299",
  "confidence": 0.92
}
```

---

### 3. 😊 Sentiment-Service — *Análisis de sentimientos y urgencia*
**URL:** `http://localhost:8003/analyze`  
**Método:** `POST` (`application/json`)

**Ejemplo de request:**
```json
{
  "text": "I'm really frustrated with this product!",
  "user_context": {
    "previous_sentiment": "neutral",
    "conversation_count": 5
  },
  "user_id": "123456789"
}
```

**Ejemplo de respuesta exitosa:**
```json
{
  "polarity": ["negative", 0.89],
  "emotion": ["frustrated", 0.85],
  "urgency_level": "high",
  "recommendation": "Escalate to human support immediately"
}
```

**Si el campo `urgency_level` es `"high"` o `"critical"`, el bot debe escalar la conversación a un grupo de Telegram de soporte humano.**

---

## 🔗 Flujo de procesamiento esperado

### 🧩 Entrada de texto
1. Recibir `update.message.text`
2. Procesar con `Sentiment-Service`
3. Continuar flujo actual (`process_user_input()`)

---

### 🎙 Entrada de voz
1. Descargar archivo `.ogg` desde Telegram (`await voice.get_file()`)
2. Enviar a `Voice-ASR:8002/transcribe`
3. Obtener `transcription` y pasar texto a `process_user_input()`
4. Analizar sentimientos con `Sentiment-Service`
5. Continuar flujo normal

---

### 🖼 Entrada de imagen o documento
1. Descargar archivo (PDF, PNG, JPG, DOCX)
2. Codificar en Base64
3. Enviar a `OCR-Multilang:8004/extract`
4. Recibir texto (`text`), pasarlo a `process_user_input()`
5. Analizar sentimientos
6. Continuar flujo normal

---

## 🧠 Estructura de Handlers recomendada

```python
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
application.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
```

---

## 🧩 Ejemplo de implementación modular (resumen esperado)

Cada handler:
- Descarga el contenido desde Telegram.
- Llama al cliente respectivo (`voice_client`, `ocr_client`, `sentiment_client`).
- Valida respuesta y errores.
- Registra logs con `chat_id`, tipo de mensaje, duración, confianza.
- Envía el texto final a `process_user_input(text, chat_id)`.

---

## 🧰 Requisitos técnicos y de calidad

- Programación **asíncrona con `asyncio`**
- **Manejo robusto de errores** y logs con `logging.exception`
- Código **modular**, limpio y legible
- **Tipado y docstrings** recomendados
- Sin dependencias externas complejas
- Preparado para producción y pruebas unitarias

---

## 📊 Ejemplo de Logs esperados

```
[INFO] [chat_id=123456789] Processing voice message...
[DEBUG] ASR Confidence: 0.93 | Duration: 2.4s
[INFO] Transcribed text: "Hello, I want to buy a laptop"
[DEBUG] Sentiment: negative (0.89) | Urgency: high
[ALERT] Escalation triggered for chat_id=123456789
```

---

## 🧩 Resultado esperado del desarrollo

1. Código Python completo con:
   - Handlers (`handle_message`, `handle_voice_message`, `handle_document_message`, `handle_photo_message`)
   - Clientes (`ASRClient`, `OCRClient`, `SentimentClient`)
   - Flujo común `process_user_input(text, chat_id)`
   - Registro en `application`

2. Ejemplo funcional con todos los tipos de mensajes.

3. Manejo de escalamiento por sentimiento negativo.

---

## ✅ Resumen del comportamiento final

| Tipo de entrada | Servicio usado | Flujo posterior |
|------------------|----------------|-----------------|
| Texto | — | Procesamiento normal |
| Voz | Voice-ASR (8002) | Transcripción → texto → flujo normal |
| Documento | OCR-Multilang (8004) | Extracción → texto → flujo normal |
| Imagen | OCR-Multilang (8004) | Extracción → texto → flujo normal |
| Todos | Sentiment-Service (8003) | Análisis de urgencia → posible alerta |

---

## 🚀 Entregable final

Un archivo principal `telegram_bot.py` o equivalente que:
- Registre los handlers correctamente.
- Implemente el flujo completo descrito.
- Tenga funciones bien comentadas y tipadas.
- Ejecute correctamente los tres servicios externos (`ASR`, `OCR`, `Sentiment`) de manera integrada.

---

**Instrucción final:**
Genera el código completo y funcional del bot conforme a todas estas especificaciones, con una arquitectura modular, asincrónica, robusta y lista para producción.
