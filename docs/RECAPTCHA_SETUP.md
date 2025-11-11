# Configuración de reCAPTCHA v3 en Demo Agent

## 🎯 Objetivo

Este documento proporciona instrucciones detalladas para obtener y configurar las claves de **reCAPTCHA v3** en el servicio demo_agent.

---

## 📋 Requisitos Previos

- ✅ Una cuenta de Google activa
- ✅ Acceso a Google Cloud Console
- ✅ Tu dominio registrado (o localhost para desarrollo)

---

## 🔑 Paso a Paso: Obtener las Claves reCAPTCHA

### Paso 1: Acceder a la Consola de reCAPTCHA

1. Abre tu navegador y ve a: **https://www.google.com/recaptcha/admin**
2. Si no has iniciado sesión, haz clic en **"Iniciar sesión"**
3. Usa tu cuenta de Google

---

### Paso 2: Crear un Nuevo Sitio

1. Una vez en la consola, verás una lista de sitios existentes (si los hay)
2. Haz clic en el botón **"+" (más)** en la esquina superior izquierda para crear un nuevo sitio
3. O ve a: **https://www.google.com/recaptcha/admin/create**

---

### Paso 3: Completar el Formulario de Creación

Completa los siguientes campos:

#### **Label (Etiqueta)**
```
Nombre: Demo Agent
(o el nombre que uses para tu aplicación)
```

#### **reCAPTCHA type (Tipo de reCAPTCHA)**
**Selecciona: reCAPTCHA v3**

```
□ reCAPTCHA v2
  ├─ "I'm not a robot" Checkbox
  └─ Invisible reCAPTCHA badge

✓ reCAPTCHA v3
  └─ No requiere interacción del usuario
```

#### **Domains (Dominios)**
Agrega los dominios donde despliegas tu aplicación:

**Para desarrollo local:**
```
localhost
127.0.0.1
```

**Para producción:**
```
api.example.com
www.example.com
example.com
```

**Nota**: Puedes agregar múltiples dominios separados por saltos de línea

#### **Términos de Servicio**
✓ Acepta los términos de servicio de Google reCAPTCHA

---

### Paso 4: Crear el Sitio

1. Haz clic en **"Create"** o **"Crear"**
2. Google validará que los dominios sean válidos
3. Serás redirigido a la página de configuración del sitio

---

### Paso 5: Copiar las Claves

En la página de configuración, verás dos claves:

#### **1. Site Key (Clave del Sitio)**
```
6LeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Uso**: Frontend (cliente)
- ✅ Se puede exponer públicamente
- ✅ Se envía en el formulario HTML
- ✅ Se incluye en el código JavaScript del cliente

#### **2. Secret Key (Clave Secreta)**
```
6LeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Uso**: Backend (servidor)
- ❌ NUNCA la expongas públicamente
- ❌ No la incluyas en repositorios públicos
- ❌ Solo en el servidor backend
- ✅ Solo para verificación con Google API

---

## ⚙️ Paso 6: Configurar en demo_agent

### 6.1 Actualizar el archivo `.env.example`

Ya está actualizado con las instrucciones. Verifica que contenga:

```bash
ENABLE_CAPTCHA=true
RECAPTCHA_SECRET_KEY=6LeXXXXXXXXXXXXXXXXXXXXXX_YOUR_SECRET_KEY_HERE
RECAPTCHA_SITE_KEY=6LeXXXXXXXXXXXXXXXXXXXXXX_YOUR_SITE_KEY_HERE
```

### 6.2 Crear/Actualizar el archivo `.env` local

```bash
cd /home/javort/alfredo/MCP-Server/demo_agent
cp .env.example .env
```

Luego edita `.env` con tus claves reales:

```bash
# Security Configuration
ENABLE_CAPTCHA=true
RECAPTCHA_SECRET_KEY=6LeIIIIIIIIIIIIIIIIIIII-XXXXXXXXXXXXXX
RECAPTCHA_SITE_KEY=6LeIIIIIIIIIIIIIIIIIIII-YYYYYYYYYYYYY
```

### 6.3 Configurar en Docker (docker-compose)

Si usas Docker, actualiza el archivo `docker-compose.yml`:

```yaml
services:
  demo_agent:
    environment:
      ENABLE_CAPTCHA: "true"
      RECAPTCHA_SECRET_KEY: "6LeIIIIIIIIIIIIIIIIIIII-XXXXXXXXXXXXXX"
      RECAPTCHA_SITE_KEY: "6LeIIIIIIIIIIIIIIIIIIII-YYYYYYYYYYYYY"
```

---

## 🔒 Seguridad: Mejores Prácticas

### ✅ HAZLO:
- Mantén `RECAPTCHA_SECRET_KEY` solo en el servidor
- Usa variables de entorno en producción
- Almacena las claves en un `.env` **nunca versionado**
- Añade `.env` a tu `.gitignore`

### ❌ NO LO HAGAS:
- ❌ No expongas `RECAPTCHA_SECRET_KEY` en el frontend
- ❌ No la commits en repositorios públicos
- ❌ No la incluyas en logs o mensajes de error
- ❌ No la compartas en Slack/Teams/correos

### 📋 Verificar `.gitignore`

Asegúrate de que tu `.gitignore` excluya:

```bash
# En .gitignore
.env
.env.local
.env.*.local
*.key
secrets.json
```

---

## 🧪 Verificar que Funciona

### 1. Verificar Configuración en el Servidor

```bash
cd /home/javort/alfredo/MCP-Server/demo_agent
python -c "from config.settings import config; print(f'CAPTCHA Enabled: {config.ENABLE_CAPTCHA}'); print(f'Secret Key: {bool(config.RECAPTCHA_SECRET_KEY)}'); print(f'Site Key: {bool(config.RECAPTCHA_SITE_KEY)}')"
```

Debería mostrar:
```
CAPTCHA Enabled: True
Secret Key: True
Site Key: True
```

### 2. Prueba de Verificación de Token

Endpoint: `POST /v1/demo`

Con un token reCAPTCHA válido:

```bash
curl -X POST http://localhost:8082/v1/demo \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "session_id": "sess_test",
    "input": "¿Hola?",
    "language": "es",
    "metadata": {
      "ip": "127.0.0.1",
      "user_agent": "test-agent",
      "fingerprint": "test-fingerprint"
    }
  }'
```

Si CAPTCHA está configurado y habilitado:
- ✅ Se verificará el token reCAPTCHA
- ✅ Se calculará la puntuación de riesgo
- ✅ Se permitirá o bloqueará según la puntuación

### 3. Verificar Estado de reCAPTCHA

El servicio proporciona un método para verificar el estado:

```python
from demo_agent.security.captcha_handler import CaptchaHandler
handler = CaptchaHandler()
status = handler.get_recaptcha_status()
print(status)
```

Output esperado:
```python
{
    "enabled": True,
    "configured": True,
    "version": "v3",
    "score_threshold": 0.5,
    "status": "ready"
}
```

---

## 📊 Entendiendo las Puntuaciones de reCAPTCHA

reCAPTCHA v3 devuelve una puntuación de **0.0 a 1.0**:

| Score | Significado | Acción |
|-------|-------------|--------|
| **0.0 - 0.3** | Probablemente un bot | 🚫 Bloquear |
| **0.3 - 0.7** | Actividad sospechosa | ⚠️ Requerir CAPTCHA |
| **0.7 - 1.0** | Probablemente humano | ✅ Permitir |

**En demo_agent:**
- Si `abuse_score > FINGERPRINT_SCORE_THRESHOLD` (0.7)
- Se requiere verificación reCAPTCHA
- Si falla → Error `captcha_required`

---

## 🔍 Monitoreo y Análisis

### En la Consola de reCAPTCHA:

1. Ve a **Analytics** en tu sitio
2. Verás gráficos de:
   - Solicitudes diarias
   - Distribución de puntuaciones
   - Patrones de actividad

### En los Logs de demo_agent:

```bash
# Ver logs de verificación reCAPTCHA
tail -f logs/demo_agent.log | grep -i captcha
```

Ejemplos de logs:
```
2025-11-03 12:30:45 - CAPTCHA required for user_123: abuse_score=0.85
2025-11-03 12:31:22 - Verifying reCAPTCHA token from 192.168.1.100
2025-11-03 12:31:23 - CAPTCHA verification failed: invalid-input-response
```

---

## 🐛 Solución de Problemas

### Problema 1: "RECAPTCHA_SECRET_KEY not configured"

**Síntoma**:
```json
{
  "success": false,
  "error_codes": ["missing-input-secret"]
}
```

**Solución**:
1. Verifica que `.env` tiene `RECAPTCHA_SECRET_KEY`
2. Confirma que la clave no está vacía
3. Reinicia el servicio: `docker-compose restart demo_agent`

---

### Problema 2: "Invalid site key"

**Síntoma**:
```json
{
  "success": false,
  "error_codes": ["invalid-input-response"]
}
```

**Solución**:
1. Verifica que el `RECAPTCHA_SITE_KEY` es correcto
2. Asegúrate de que el dominio está registrado en Google
3. Espera 5-10 minutos después de crear el sitio

---

### Problema 3: CAPTCHA se requiere para todos

**Síntoma**: Todos los usuarios obtienen error `captcha_required`

**Causa**: `FINGERPRINT_SCORE_THRESHOLD` muy bajo (default 0.7)

**Solución**:
```bash
# En .env, aumenta el umbral:
FINGERPRINT_SCORE_THRESHOLD=0.85
```

---

### Problema 4: CAPTCHA nunca se requiere

**Síntoma**: Nadie obtiene error `captcha_required`

**Causa**: `ENABLE_CAPTCHA` está en `false`

**Solución**:
```bash
# En .env:
ENABLE_CAPTCHA=true
```

---

## 📚 Referencias

- [Google reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin)
- [reCAPTCHA v3 Documentation](https://developers.google.com/recaptcha/docs/v3)
- [reCAPTCHA Best Practices](https://developers.google.com/recaptcha/docs/best-practices)

---

## ✅ Checklist de Configuración

- [ ] Cuenta de Google creada
- [ ] Acceso a Google reCAPTCHA Admin Console
- [ ] Nuevo sitio reCAPTCHA v3 creado
- [ ] Dominios agregados (localhost y/o producción)
- [ ] Site Key copiada
- [ ] Secret Key copiada
- [ ] `.env` actualizado con claves reales
- [ ] `ENABLE_CAPTCHA=true`
- [ ] `.env` agregado a `.gitignore`
- [ ] Servicio reiniciado
- [ ] Prueba de verificación completada
- [ ] Status `ready` confirmado

---

**Última actualización**: 2025-11-03
**Versión**: 1.0.0