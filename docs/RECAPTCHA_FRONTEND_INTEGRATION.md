# Integración de reCAPTCHA v3 en el Frontend

## 🎯 Objetivo

Este documento explica cómo integrar **reCAPTCHA v3** en tu aplicación frontend para trabajar con demo_agent.

---

## 📋 Resumen Rápido

```
┌─────────────────────────────────────────────────────────────────┐
│                        FLUJO DE reCAPTCHA v3                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. USUARIO CARGA PÁGINA                                        │
│     └─> Script reCAPTCHA se carga (invisible)                   │
│                                                                 │
│  2. USUARIO INTERACTÚA (hace clic, escribe, etc.)              │
│     └─> reCAPTCHA analiza comportamiento                        │
│     └─> Genera TOKEN                                            │
│                                                                 │
│  3. USUARIO ENVÍA FORMULARIO                                    │
│     └─> Token se incluye en la solicitud                        │
│     └─> Se envía al BACKEND (demo_agent)                        │
│                                                                 │
│  4. BACKEND VERIFICA TOKEN                                      │
│     └─> Envía token a Google API                                │
│     └─> Recibe puntuación (0.0-1.0)                            │
│     └─> Decide: permitir / requerir CAPTCHA / bloquear          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Las Dos Claves

### Site Key (Clave del Sitio)
```
6LeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```
- **Dónde**: Frontend (código JavaScript)
- **Público**: ✅ Se puede ver en el navegador
- **Uso**: Cargar el script de reCAPTCHA
- **Seguridad**: Sin riesgo si se expone

### Secret Key (Clave Secreta)
```
6LeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```
- **Dónde**: Backend (archivo `.env`)
- **Público**: ❌ NUNCA en el código frontend
- **Uso**: Verificar tokens con Google API
- **Seguridad**: CRÍTICA - protégela bien

---

## 🛠️ Implementación en Frontend

### Opción 1: HTML Vanilla + JavaScript

#### Paso 1: Cargar el Script de reCAPTCHA

En tu archivo HTML, agrega esto en la sección `<head>` o antes del `</body>`:

```html
<!-- Cargar reCAPTCHA v3 -->
<script src="https://www.google.com/recaptcha/api.js?render=6LeXXXXXXXXXXXXXXXXXXXXXX"></script>
```

Reemplaza `6LeXXXXXXXXXXXXXXXXXXXXXX` con tu **SITE_KEY**.

#### Paso 2: Obtener Token en Tu Formulario

```javascript
// Obtener token de reCAPTCHA v3
function obtenerTokenRecaptcha(action = 'submit') {
    return new Promise((resolve) => {
        grecaptcha.ready(function() {
            grecaptcha.execute('6LeXXXXXXXXXXXXXXXXXXXXXX', {
                action: action  // 'submit', 'demo_query', etc.
            }).then(function(token) {
                resolve(token);
            });
        });
    });
}
```

#### Paso 3: Enviar Token al Backend

```javascript
async function enviarConsultaAlDemo() {
    try {
        // 1. Obtener token de reCAPTCHA
        const recaptchaToken = await obtenerTokenRecaptcha('demo_query');

        // 2. Preparar datos
        const datos = {
            user_id: "usuario_123",
            session_id: "sesion_abc",
            input: document.getElementById('query').value,
            language: "es",
            metadata: {
                ip: "127.0.0.1",  // El servidor la obtiene automáticamente
                user_agent: navigator.userAgent,
                fingerprint: "opcional",
                recaptcha_token: recaptchaToken  // ← Token aquí
            }
        };

        // 3. Enviar al backend
        const response = await fetch('http://api.example.com/v1/demo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });

        const resultado = await response.json();

        // 4. Manejar respuesta
        if (resultado.success) {
            console.log('Respuesta:', resultado.response);
        } else if (resultado.error === 'captcha_required') {
            console.warn('reCAPTCHA requiere verificación adicional');
            // Mostrar un CAPTCHA v2 (checkbox) como backup
        } else {
            console.error('Error:', resultado.message);
        }
    } catch (error) {
        console.error('Error al enviar consulta:', error);
    }
}
```

---

### Opción 2: React

#### Instalación de librería

```bash
npm install @react-recaptcha-v3/react
```

#### Componente React

```jsx
import { GoogleReCaptchaProvider, useGoogleReCaptcha } from '@react-recaptcha-v3/react';

function DemoQueryComponent() {
    const { executeRecaptcha } = useGoogleReCaptcha();

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!executeRecaptcha) {
            console.log('reCAPTCHA no está listo');
            return;
        }

        // Obtener token
        const token = await executeRecaptcha('demo_query');

        // Enviar consulta
        const response = await fetch('/v1/demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "usuario_123",
                input: "tu pregunta",
                metadata: {
                    recaptcha_token: token
                }
            })
        });

        const data = await response.json();
        console.log(data);
    };

    return (
        <form onSubmit={handleSubmit}>
            <input type="text" placeholder="Escribe tu pregunta" />
            <button type="submit">Enviar</button>
        </form>
    );
}

// En App.jsx
export default function App() {
    return (
        <GoogleReCaptchaProvider reCaptchaKey="6LeXXXXXXXXXXXXXXXXXXXXXX">
            <DemoQueryComponent />
        </GoogleReCaptchaProvider>
    );
}
```

---

### Opción 3: Vue 3

#### Instalación

```bash
npm install vue3-google-recaptcha
```

#### Componente Vue

```vue
<template>
    <div>
        <form @submit="handleSubmit">
            <input
                v-model="query"
                type="text"
                placeholder="¿Qué deseas saber?"
            />
            <button type="submit" :disabled="loading">
                {{ loading ? 'Enviando...' : 'Enviar' }}
            </button>
        </form>
        <p v-if="respuesta">{{ respuesta }}</p>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useReCaptcha } from 'vue3-google-recaptcha'

const { executeRecaptcha } = useReCaptcha()
const query = ref('')
const loading = ref(false)
const respuesta = ref('')

const handleSubmit = async () => {
    loading.value = true

    try {
        // Obtener token reCAPTCHA
        const token = await executeRecaptcha('demo_query')

        // Enviar al backend
        const response = await fetch('/v1/demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "usuario_123",
                input: query.value,
                metadata: {
                    recaptcha_token: token
                }
            })
        })

        const data = await response.json()

        if (data.success) {
            respuesta.value = data.response
        } else {
            respuesta.value = `Error: ${data.message}`
        }
    } finally {
        loading.value = false
    }
}
</script>
```

---

## 🔗 Flujo Completo: Frontend → Backend

### 1️⃣ Frontend: Cargar reCAPTCHA

```javascript
// En página load
<script src="https://www.google.com/recaptcha/api.js?render=6LeXXXXXXXXXXXXXXXXXXXXXX"></script>
```

### 2️⃣ Frontend: Obtener Token

```javascript
const token = await grecaptcha.execute('6LeXXXXXXXXXXXXXXXXXXXXXX', {
    action: 'demo_query'
});
// token = "0.ABC123XYZ..."
```

### 3️⃣ Frontend: Enviar al Backend

```javascript
fetch('/v1/demo', {
    method: 'POST',
    body: JSON.stringify({
        user_id: "user_123",
        input: "¿Qué es Python?",
        metadata: {
            recaptcha_token: "0.ABC123XYZ..."
        }
    })
})
```

### 4️⃣ Backend: Verificar Token

```python
# En demo_agent/agent.py
verification_result = await demo_agent.captcha_handler.verify_token(
    token=metadata.recaptcha_token,
    remote_ip=request.client.host
)
# verification_result = {
#     "success": True,
#     "score": 0.95,
#     "action": "demo_query"
# }
```

### 5️⃣ Backend: Evaluar Puntuación

```python
if verification_result['score'] < 0.3:
    # Bloquear - es un bot
    return {"error": "suspicious_behavior_detected"}
elif verification_result['score'] < 0.7:
    # Requerir verificación adicional
    return {"error": "captcha_required"}
else:
    # Procesar consulta normalmente
    response = await gemini_api.generate(user_input)
    return {"success": True, "response": response}
```

### 6️⃣ Backend: Responder al Frontend

```json
{
    "success": true,
    "response": "Python es un lenguaje de programación...",
    "tokens_used": 150,
    "warning": {
        "is_warning": false,
        "message": null
    }
}
```

---

## ⚙️ Configuración por Entorno

### Desarrollo Local

```javascript
// En tu archivo de configuración
const RECAPTCHA_SITE_KEY = process.env.REACT_APP_RECAPTCHA_SITE_KEY;
// En .env.local:
// REACT_APP_RECAPTCHA_SITE_KEY=6LeIIIIIIIIIIIIIIIIIIII-localhost-test
```

### Producción

```javascript
const RECAPTCHA_SITE_KEY = process.env.REACT_APP_RECAPTCHA_SITE_KEY;
// En variables de GitHub/GitLab:
// REACT_APP_RECAPTCHA_SITE_KEY=6LeIIIIIIIIIIIIIIIIIIII-production-real
```

---

## 🔐 Seguridad: Lo que NO Hacer

### ❌ NO hagas esto:

```javascript
// ❌ NUNCA expongas la SECRET_KEY en el frontend
const SECRET_KEY = "6LeXXXXXXXXXXXXXXXXXXXXXX";

// ❌ NO hagas verificación en el cliente
const isHuman = captchaScore > 0.5;  // INCORRECTO

// ❌ NO almacenes datos sensibles
localStorage.setItem('recaptcha_secret', '6LeXXXXXXXXXXXXXXXXXXXXXX');
```

### ✅ HAZLO:

```javascript
// ✅ Solo la SITE_KEY en el frontend
const SITE_KEY = "6LeXXXXXXXXXXXXXXXXXXXXXX";

// ✅ Confía en la verificación del backend
const response = await verify_on_backend(token);

// ✅ La SECRET_KEY solo en el servidor
// En backend/.env:
// RECAPTCHA_SECRET_KEY=6LeXXXXXXXXXXXXXXXXXXXXXX
```

---

## 🧪 Pruebas

### Test Manual

```bash
# 1. Abre Developer Tools (F12)
# 2. En la consola JavaScript, ejecuta:

grecaptcha.ready(function() {
    grecaptcha.execute('TU_SITE_KEY', {action: 'test'})
        .then(token => console.log('Token:', token))
});

# 3. El token aparecerá en la consola
# Ejemplo: "0.AXqqBCnnNkB8nW..."
```

### Test de Integración

```bash
# Verificar que el token se envía correctamente
curl -X POST http://localhost:8082/v1/demo \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "input": "test query",
    "metadata": {
      "recaptcha_token": "0.AXqqBCnnNkB8nW..."
    }
  }'
```

---

## 📊 Monitoreo

### Ver solicitudes reCAPTCHA en Google Console

1. Ve a https://www.google.com/recaptcha/admin
2. Selecciona tu sitio
3. Ve a **Analytics**
4. Verás:
   - Solicitudes por hora
   - Distribución de puntuaciones
   - Patrones sospechosos

### Ver logs en demo_agent

```bash
# Buscar verificaciones reCAPTCHA
tail -f logs/demo_agent.log | grep -i "verify\|captcha"

# Output:
# 2025-11-03 12:30:45 - Verifying reCAPTCHA token from 192.168.1.100
# 2025-11-03 12:30:46 - reCAPTCHA verification: success=true score=0.95
```

---

## 🐛 Solución de Problemas

### Problema: Token no se obtiene

**Síntoma**: `grecaptcha.execute()` devuelve `undefined`

**Solución**:
```javascript
// Asegúrate de que el script se cargó:
grecaptcha.ready(() => {
    // Esto se ejecuta cuando reCAPTCHA está listo
    grecaptcha.execute('TU_SITE_KEY', {action: 'demo_query'})
        .then(token => console.log('Token:', token));
});
```

---

### Problema: "Invalid site key" error

**Síntoma**:
```
reCAPTCHA: The sitekey is invalid or not yet activated.
```

**Solución**:
1. Verifica que usas la **SITE_KEY** correcta (no la SECRET_KEY)
2. Confirma que el dominio está registrado en Google
3. Espera 5-10 minutos después de crear el sitio

---

### Problema: CAPTCHA v3 no se muestra

**Síntoma**: El badge de reCAPTCHA no aparece en la página

**Nota**: reCAPTCHA v3 **no muestra un badge visible** por defecto. Solo aparece en la esquina inferior derecha con pequeño texto "protected by reCAPTCHA".

Si quieres mostrar un checkbox (v2), úsalo como fallback:

```html
<div class="g-recaptcha" data-sitekey="6LeXXXXXXXXXXXXXXXXXXXXXX"></div>
```

---

## 📚 Referencias

- [reCAPTCHA v3 Documentation](https://developers.google.com/recaptcha/docs/v3)
- [Web API](https://developers.google.com/recaptcha/docs/v3#api_request)
- [Testing reCAPTCHA](https://developers.google.com/recaptcha/docs/faq#id-like-to-run-automated-tests-with-recaptcha-can-i-do-this)

---

**Última actualización**: 2025-11-03
**Versión**: 1.0.0