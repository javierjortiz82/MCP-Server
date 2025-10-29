# 📅 Google Calendar API - Guía Completa de Configuración

Este directorio contiene las credenciales de Google Calendar necesarias para la integración del sistema de reservas MCP.

## 📋 Prerequisitos

Antes de comenzar, asegúrate de tener:

- ✅ Una cuenta de Google (Gmail o Google Workspace)
- ✅ Acceso a [Google Cloud Console](https://console.cloud.google.com/)
- ✅ Permisos de administrador en tu calendario de Google
- ✅ 15-20 minutos para completar la configuración

> **Nota**: Este proceso es GRATIS para uso básico. Google Calendar API incluye cuota gratuita generosa.

---

## 🚀 Configuración Completa (Paso a Paso)

### Paso 1️⃣: Crear Proyecto en Google Cloud Console

1. **Ir a Google Cloud Console**
   - Visita: [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Inicia sesión con tu cuenta de Google

2. **Crear Nuevo Proyecto**
   - Click en el selector de proyectos (parte superior izquierda)
   - Click en **"New Project"** (Nuevo Proyecto)
   - Nombre sugerido: `MCP-Booking-System`
   - Organización: Dejar en blanco (o seleccionar si tienes)
   - Click en **"Create"** (Crear)

3. **Esperar Confirmación**
   - Aparecerá una notificación cuando el proyecto esté listo
   - Selecciona el proyecto recién creado en el selector
   - **Anota tu Project ID** (lo necesitarás después)

> **Tip**: El Project ID es único y no se puede cambiar. Asegúrate de anotarlo.

---

### Paso 2️⃣: Habilitar Google Calendar API

1. **Acceder a la Biblioteca de APIs**
   - En el menú lateral (☰), navega a:
     ```
     APIs & Services → Library
     ```
   - O usa el menú: **More products** → **Google Workspace** → **Product Library**

2. **Buscar Google Calendar API**
   - En la barra de búsqueda, escribe: `Google Calendar API`
   - Click en el resultado **"Google Calendar API"**

3. **Habilitar la API**
   - Click en el botón azul **"Enable"** (Habilitar)
   - Espera 10-30 segundos mientras se activa
   - Verás un dashboard con gráficas (significa que está habilitada)

> **Verificación**: En el menú lateral, ve a **APIs & Services** → **Enabled APIs & Services** y deberías ver "Google Calendar API" en la lista.

---

### Paso 3️⃣: Crear Service Account

Una **Service Account** es como un "usuario robot" que tu aplicación usa para acceder a Google Calendar sin intervención humana.

1. **Ir a Credenciales**
   - En el menú lateral: **APIs & Services** → **Credentials**
   - Click en **"+ CREATE CREDENTIALS"** (parte superior)
   - Selecciona **"Service Account"**

2. **Configurar Service Account Details**
   - **Service account name**: `mcp-calendar-service`
   - **Service account ID**: Se generará automáticamente (ej: `mcp-calendar-service`)
   - **Description**: `Service account for MCP booking system - automated calendar management`
   - Click **"CREATE AND CONTINUE"**

3. **Asignar Rol (Opcional pero Recomendado)**
   - **Select a role**: Puedes dejarlo vacío o seleccionar:
     - `Basic` → `Editor` (permisos amplios)
     - O dejarlo sin rol (recomendado para seguridad)
   - Click **"CONTINUE"**

4. **Grant users access (Opcional)**
   - Puedes dejarlo vacío
   - Click **"DONE"**

5. **Confirmar Creación**
   - Verás tu nueva service account en la lista
   - **Copia el email** que aparece (formato: `mcp-calendar-service@tu-proyecto.iam.gserviceaccount.com`)
   - Lo necesitarás para compartir el calendario

> **Importante**: La service account NO tiene acceso automático a tu calendar. Debes compartirlo explícitamente (ver Paso 5).

---

### Paso 4️⃣: Generar y Descargar Clave JSON

Esta es la clave privada que tu aplicación usará para autenticarse.

1. **Acceder a Keys**
   - En la lista de **Service Accounts**, click en el service account que acabas de crear
   - Ve a la pestaña **"KEYS"** (parte superior)

2. **Crear Nueva Clave**
   - Click en **"ADD KEY"** → **"Create new key"**
   - Selecciona el tipo de clave: **JSON** (recomendado)
   - Click **"CREATE"**

3. **Guardar el Archivo Descargado**
   - Se descargará automáticamente un archivo JSON
   - El nombre será algo como: `tu-proyecto-abc123def456.json`
   - **⚠️ IMPORTANTE**: Este archivo contiene tu clave privada. Guárdalo en un lugar seguro.

4. **Renombrar y Mover el Archivo**
   ```bash
   # Renombra el archivo descargado a service-account.json
   mv ~/Downloads/tu-proyecto-abc123def456.json ./credentials/service-account.json

   # Verifica que esté en la ubicación correcta
   ls -l credentials/service-account.json
   ```

> **⚠️ ADVERTENCIA DE SEGURIDAD**:
> - Este archivo te da acceso completo al proyecto de Google Cloud
> - NUNCA lo compartas públicamente ni lo subas a Git
> - Por defecto, las claves de service account **nunca expiran** (puedes cambiar esto)
> - Puedes tener hasta 10 claves por service account
> - Si pierdes el archivo, NO puedes volver a descargarlo (debes crear una nueva clave)

---

### Paso 5️⃣: Compartir tu Google Calendar con el Service Account

Este es **EL PASO MÁS CRÍTICO**. Sin esto, tu aplicación no podrá acceder al calendario.

#### ¿Por qué es necesario?

La service account es como un usuario separado de Google. Necesita que le des acceso explícito a tu calendario, igual que compartirías tu calendario con un colega.

#### Pasos Detallados:

1. **Encontrar el Email de la Service Account**
   - Opción A: Abre el archivo `service-account.json` y busca el campo `client_email`
   - Opción B: En Google Cloud Console, ve a **IAM & Admin** → **Service Accounts**

   El email tendrá este formato:
   ```
   mcp-calendar-service@tu-proyecto-123.iam.gserviceaccount.com
   ```

   **Copia este email completo**

2. **Ir a Google Calendar**
   - Abre [Google Calendar](https://calendar.google.com/) en tu navegador
   - Inicia sesión con tu cuenta personal (la que usa el calendario)

3. **Seleccionar el Calendario a Compartir**
   - En el panel izquierdo, localiza **"My calendars"**
   - Busca el calendario que quieres usar (normalmente tu calendario principal)
   - Pasa el mouse sobre el nombre del calendario
   - Click en los **tres puntos verticales (⋮)**
   - Selecciona **"Settings and sharing"**

4. **Agregar la Service Account**
   - Desplázate hasta la sección **"Share with specific people or groups"**
   - Click en el botón **"+ Add people and groups"**
   - **Pega el email de la service account** que copiaste en el paso 1
   - **Muy importante**: Selecciona el nivel de permisos

5. **Seleccionar Permisos Correctos**

   Dependiendo de lo que necesites:

   - **"Make changes to events"** ← ✅ **RECOMENDADO** (crear, editar, eliminar eventos)
   - **"See all event details"** ← Solo lectura (útil para consultas)
   - **"See only free/busy"** ← Mínimo acceso (no recomendado)

   Para el sistema MCP de reservas, selecciona: **"Make changes to events"**

6. **Guardar y Confirmar**
   - Click en **"Send"**
   - NO es necesario notificar al service account (es un robot, no lee emails 😄)
   - Aparecerá en la lista de personas con acceso

#### ✅ Verificación:

Deberías ver algo como esto en tu lista de personas con acceso:

```
mcp-calendar-service@tu-proyecto-123.iam.gserviceaccount.com
Permission: Make changes to events
```

> **Error Común**: Si olvidas este paso, verás errores como "Calendar not found" o "Access denied" cuando la aplicación intente usar el calendario.

---

### Paso 6️⃣: Configurar Variables de Entorno

Ahora configura tu aplicación para usar las credenciales.

#### Para Desarrollo Local:

Edita el archivo `mcp_server/.env`:

```bash
# ============================================
# Google Calendar API Configuration
# ============================================

# Habilitar integración con Google Calendar
GOOGLE_CALENDAR_ENABLED=true

# Ruta al archivo de credenciales de service account
# Para local: ruta relativa desde la raíz del proyecto
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials/service-account.json

# ID del calendario a usar
# Opción 1: Tu email de Gmail
GOOGLE_CALENDAR_ID=tu-email@gmail.com
# Opción 2: Usar "primary" para el calendario principal del service account
# GOOGLE_CALENDAR_ID=primary

# Zona horaria para los eventos (formato IANA)
# Ver lista completa: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
GOOGLE_CALENDAR_TIMEZONE=America/Costa_Rica
```

#### Zonas Horarias Comunes:

```bash
# América Latina
America/Costa_Rica      # Costa Rica (UTC-6)
America/Mexico_City     # México (UTC-6)
America/Bogota          # Colombia (UTC-5)
America/Lima            # Perú (UTC-5)
America/Argentina/Buenos_Aires  # Argentina (UTC-3)
America/Santiago        # Chile (UTC-3/UTC-4)

# España
Europe/Madrid           # España (UTC+1/UTC+2)

# Estados Unidos
America/New_York        # Este (UTC-5/UTC-4)
America/Chicago         # Centro (UTC-6/UTC-5)
America/Los_Angeles     # Oeste (UTC-8/UTC-7)
```

---

## 🐳 Configuración en Docker

El sistema está **pre-configurado para Docker**. El archivo de credenciales se monta automáticamente como un volumen de solo lectura.

### Qué hace Docker automáticamente:

```yaml
# En DockerConfig/docker-compose.yml
volumes:
  - ../credentials:/app/credentials:ro  # Monta el directorio de credenciales

environment:
  # Override para Docker - usa ruta absoluta del contenedor
  GOOGLE_CALENDAR_CREDENTIALS_PATH: /app/credentials/service-account.json
```

### Lo que necesitas hacer:

✅ **Solo asegúrate de que el archivo esté aquí:**
```bash
MCP-Server/credentials/service-account.json
```

❌ **NO necesitas**:
- Copiar el archivo al contenedor manualmente
- Modificar el Dockerfile
- Cambiar permisos del archivo

El sistema detecta automáticamente si está en Docker o desarrollo local y ajusta las rutas.

---

## 📄 Estructura del Archivo service-account.json

### Campos del Archivo:

Un archivo de service account válido contiene estos campos:

```json
{
  "type": "service_account",
  "project_id": "tu-proyecto-id-123",
  "private_key_id": "abc123def456...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC...\n-----END PRIVATE KEY-----\n",
  "client_email": "mcp-calendar-service@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "1234567890",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}
```

### Explicación de Campos:

| Campo | Propósito | Ejemplo |
|-------|-----------|---------|
| `type` | Identifica el tipo de credencial | `"service_account"` |
| `project_id` | ID único de tu proyecto GCP | `"mcp-booking-123"` |
| `private_key_id` | ID de la clave privada | Hash único |
| `private_key` | **Clave RSA privada** (1600+ chars) | Inicia con `-----BEGIN PRIVATE KEY-----` |
| `client_email` | Email del service account | `mcp-calendar-service@...iam.gserviceaccount.com` |
| `client_id` | ID numérico del cliente | `"1234567890"` |
| `auth_uri` | Endpoint de autorización OAuth | URL de Google |
| `token_uri` | Endpoint para obtener tokens | URL de Google |
| `client_x509_cert_url` | URL del certificado X.509 | URL de Google |
| `universe_domain` | Dominio del universo (nuevo) | `"googleapis.com"` |

### ⚠️ Validación del Archivo:

Un archivo **válido** debe tener:

✅ `private_key` de ~1600 caracteres (no 76 como en el placeholder)
✅ Formato JSON válido (sin comas extras ni errores de sintaxis)
✅ Todos los campos requeridos presentes
✅ Archivo con permisos de lectura (no necesita ser ejecutable)

Un archivo **inválido** (placeholder) tendrá:

❌ `private_key` con texto "TU_CLAVE_PRIVADA_AQUI"
❌ `project_id` con valor "tu-proyecto-id"
❌ Causará error: `binascii.Error: Incorrect padding`

---

## 🔒 Seguridad y Buenas Prácticas

### 🚨 Reglas de Seguridad CRÍTICAS:

1. **NUNCA subas el archivo a Git**
   - ✅ El archivo `service-account.json` está en `.gitignore`
   - ✅ Solo el directorio y placeholder están en Git
   - ⚠️ Revisa siempre antes de hacer `git add .`

2. **NUNCA compartas el archivo públicamente**
   - ❌ No lo pegues en Slack, Discord, o foros
   - ❌ No lo subas a Google Drive público
   - ❌ No lo incluyas en screenshots
   - ✅ Compártelo solo por canales seguros (1Password, LastPass, etc.)

3. **Rotación de Claves**
   ```bash
   # Crear una nueva clave cada 90 días
   # En Google Cloud Console → Service Accounts → Keys → Add Key
   # Luego ELIMINA la clave antigua
   ```

4. **Principio de Mínimo Privilegio**
   - Solo comparte el calendario necesario (no todos tus calendarios)
   - Usa permisos de "Make changes to events" solo si es necesario
   - Considera "See all event details" para apps de solo lectura

5. **Monitoreo**
   - Revisa los **Service Account Keys** periódicamente
   - Elimina claves que no uses
   - Google Cloud Console muestra la última vez que se usó cada clave

### Protección del Archivo:

```bash
# Verifica que el archivo esté en .gitignore
grep "service-account.json" .gitignore

# Cambia permisos para que solo tú puedas leerlo (Linux/Mac)
chmod 600 credentials/service-account.json

# Verifica que NO esté staged en Git
git status

# Si accidentalmente lo agregaste:
git rm --cached credentials/service-account.json
```

---

## ✅ Verificación de Configuración

Sigue estos pasos para confirmar que todo está configurado correctamente:

### Verificación Paso a Paso:

#### 1. Verificar que el archivo existe y es válido:

```bash
# Verificar que el archivo existe
ls -l credentials/service-account.json

# Verificar que es JSON válido
python3 -c "import json; json.load(open('credentials/service-account.json')); print('✓ JSON válido')"

# Verificar tamaño del archivo (debe ser ~2KB, no solo unos bytes)
wc -c credentials/service-account.json
# Debería mostrar algo como: 2339 credentials/service-account.json
```

#### 2. Verificar campos críticos:

```bash
# Verificar que tiene el private_key correcto (no placeholder)
python3 << 'EOF'
import json
with open('credentials/service-account.json') as f:
    data = json.load(f)
    key = data.get('private_key', '')
    if len(key) < 1000:
        print('❌ ERROR: private_key parece ser un placeholder')
        print(f'   Longitud actual: {len(key)} caracteres')
        print('   Esperado: ~1600 caracteres')
    else:
        print(f'✓ private_key válido ({len(key)} caracteres)')
    print(f'✓ client_email: {data.get("client_email")}')
    print(f'✓ project_id: {data.get("project_id")}')
EOF
```

#### 3. Verificar variables de entorno:

```bash
# Ver configuración actual
grep GOOGLE_CALENDAR mcp_server/.env
```

Deberías ver:
```
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials/service-account.json
GOOGLE_CALENDAR_ID=tu-email@gmail.com
GOOGLE_CALENDAR_TIMEZONE=America/Costa_Rica
```

#### 4. Probar la aplicación:

**En desarrollo local:**
```bash
make validate
# Busca: "✅ Google Calendar client initialized"
```

**Con Docker:**
```bash
# Iniciar servicios
make docker-start

# Ver logs del servidor MCP
make docker-logs SERVICE=mcp-server

# Buscar mensaje de éxito:
# "✅ Google Calendar client initialized"
# "Google Calendar API enabled for calendar: tu-email@gmail.com"
```

### Señales de Configuración Exitosa:

✅ **Logs que indican éxito:**
```
[INFO] google_calendar:220 - Initializing Google Calendar client for calendar: tu-email@gmail.com
[INFO] google_calendar:253 - ✅ Google Calendar service initialized successfully
```

❌ **Logs que indican problema:**
```
[ERROR] google_calendar:255 - Credentials file not found: /app/credentials/service-account.json
[ERROR] google_calendar:259 - Authentication failed: Incorrect padding
```

---

## 🆘 Troubleshooting (Solución de Problemas)

### 🔴 Error: "Credentials file not found"

**Mensaje de error:**
```
FileNotFoundError: Credenciales de cuenta de servicio no encontradas: /credentials/service-account.json
```

**Causas posibles:**

1. **El archivo no existe en la ubicación correcta**
   ```bash
   # Verifica la ubicación
   ls -l credentials/service-account.json

   # Si no existe, asegúrate de haberlo descargado y movido aquí
   mv ~/Downloads/tu-proyecto-*.json credentials/service-account.json
   ```

2. **Path incorrecto en variables de entorno**
   ```bash
   # Revisa mcp_server/.env
   grep GOOGLE_CALENDAR_CREDENTIALS_PATH mcp_server/.env

   # Debe ser:
   # GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials/service-account.json
   ```

3. **En Docker: volumen no montado correctamente**
   ```bash
   # Reinicia el contenedor
   make docker-stop SERVICE=mcp-server
   make docker-start SERVICE=mcp-server

   # Verifica que el archivo esté montado
   docker exec mcp-server ls -l /app/credentials/
   ```

---

### 🔴 Error: "Incorrect padding" o "Authentication failed"

**Mensaje de error:**
```
binascii.Error: Incorrect padding
ERROR: Authentication failed: Incorrect padding
```

**Causa:** El archivo `service-account.json` es un **placeholder** y no contiene credenciales reales.

**Solución:**

1. **Verifica el contenido del archivo:**
   ```bash
   grep "TU_CLAVE_PRIVADA_AQUI" credentials/service-account.json
   ```

   Si encuentra algo, significa que es el placeholder.

2. **Descarga las credenciales REALES de Google Cloud Console:**
   - Ve a [Google Cloud Console](https://console.cloud.google.com/)
   - **IAM & Admin** → **Service Accounts**
   - Selecciona tu service account
   - **Keys** → **Add Key** → **Create new key** → **JSON**
   - Guarda el archivo descargado como `credentials/service-account.json`

3. **Verifica que el nuevo archivo es válido:**
   ```bash
   # El archivo debe tener ~2KB
   wc -c credentials/service-account.json
   # Debería mostrar: ~2300-2400 bytes

   # No debe tener ~680 bytes (tamaño del placeholder)
   ```

---

### 🔴 Error: "Calendar not found" o "Access denied"

**Mensaje de error:**
```
ERROR: Failed to access calendar: 404 Not Found
ERROR: Calendar API returned: Access denied
```

**Causa:** No has compartido el calendario con la service account.

**Solución:**

1. **Obtén el email de la service account:**
   ```bash
   python3 -c "import json; print(json.load(open('credentials/service-account.json'))['client_email'])"
   ```

2. **Ve a Google Calendar y comparte el calendario:**
   - Abre [Google Calendar](https://calendar.google.com/)
   - Click en el calendario → **Settings and sharing**
   - **Share with specific people** → **Add people**
   - Pega el email de la service account
   - Permisos: **"Make changes to events"**
   - Click **Send**

3. **Verifica el CALENDAR_ID en `.env`:**
   ```bash
   grep GOOGLE_CALENDAR_ID mcp_server/.env

   # Debe coincidir con tu email o el calendario compartido
   # GOOGLE_CALENDAR_ID=tu-email@gmail.com
   ```

---

### 🔴 Error: "Quota exceeded"

**Mensaje de error:**
```
ERROR: Rate limit exceeded
ERROR: Quota exceeded for quota metric 'Queries' and limit 'Queries per day'
```

**Causa:** Has excedido los límites de la API de Google Calendar.

**Límites gratuitos:**
- 1,000,000 consultas por día
- 100 consultas por 100 segundos por usuario

**Solución:**

1. **Revisa tu uso actual:**
   - Ve a [Google Cloud Console - API Dashboard](https://console.cloud.google.com/apis/dashboard)
   - Busca **Google Calendar API**
   - Revisa las métricas de uso

2. **Implementa rate limiting en tu código** (ya implementado en este proyecto):
   ```python
   # El código ya incluye manejo de rate limits
   # Ver: mcp_server/utils/google_calendar.py
   ```

3. **Si necesitas más cuota:**
   - [Solicitar aumento de cuota](https://console.cloud.google.com/apis/api/calendar-json.googleapis.com/quotas)
   - Normalmente se aprueba automáticamente para límites razonables

---

### 🔴 Error: "Invalid grant" o "Token has expired"

**Mensaje de error:**
```
ERROR: invalid_grant: Token has been expired or revoked
```

**Causas posibles:**

1. **Las credenciales fueron eliminadas o rotadas:**
   - Ve a Google Cloud Console → **Service Accounts** → **Keys**
   - Verifica que la clave aún existe
   - Si no existe, crea una nueva

2. **El reloj del sistema está desincronizado:**
   ```bash
   # Verifica la hora del sistema
   date

   # Sincroniza (Linux)
   sudo ntpdate -s time.nist.gov
   ```

3. **La service account fue deshabilitada:**
   - Ve a Google Cloud Console → **IAM & Admin** → **Service Accounts**
   - Verifica que la service account está **Enabled**

---

### 🔴 Error: "API not enabled"

**Mensaje de error:**
```
ERROR: Google Calendar API has not been used in project before or it is disabled
```

**Solución:**

1. **Habilita la API:**
   - Ve a [Google Cloud Console](https://console.cloud.google.com/)
   - **APIs & Services** → **Library**
   - Busca **"Google Calendar API"**
   - Click **"Enable"**

2. **Espera 1-2 minutos** para que se propague el cambio

3. **Reinicia tu aplicación**

---

### 📋 Checklist de Diagnóstico Completo:

Si tienes problemas, revisa estos puntos en orden:

- [ ] **1. Archivo existe:** `ls -l credentials/service-account.json`
- [ ] **2. Archivo válido:** `python3 -c "import json; json.load(open('credentials/service-account.json'))"`
- [ ] **3. No es placeholder:** El `private_key` tiene ~1600 caracteres
- [ ] **4. API habilitada:** Google Calendar API está habilitada en GCP
- [ ] **5. Variables configuradas:** `grep GOOGLE_CALENDAR mcp_server/.env`
- [ ] **6. Calendario compartido:** Service account email tiene acceso al calendario
- [ ] **7. Permisos correctos:** Service account tiene "Make changes to events"
- [ ] **8. CALENDAR_ID correcto:** Coincide con el calendario compartido

---

## 📚 Referencias y Documentación Oficial

### Documentación de Google:

- 📖 [Google Calendar API - Documentación Oficial](https://developers.google.com/calendar) *(Actualizado Octubre 2025)*
- 🔐 [Service Accounts - Guía Completa](https://cloud.google.com/iam/docs/service-accounts)
- 🔑 [OAuth 2.0 para Aplicaciones Server-to-Server](https://developers.google.com/identity/protocols/oauth2/service-account)
- 🐍 [Python Quickstart - Google Calendar API](https://developers.google.com/calendar/api/quickstart/python)
- 🔧 [Crear y Eliminar Service Account Keys](https://cloud.google.com/iam/docs/keys-create-delete) *(Actualizado 2025)*
- 📊 [API Quotas y Límites](https://developers.google.com/calendar/api/guides/quota)
- 🌍 [Lista de Time Zones IANA](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

### Consolas y Dashboards:

- 🖥️ [Google Cloud Console](https://console.cloud.google.com/)
- 📅 [Google Calendar](https://calendar.google.com/)
- 📈 [API Dashboard - Ver Uso y Cuotas](https://console.cloud.google.com/apis/dashboard)

### Tutoriales y Recursos:

- 💡 [Integración con Service Accounts (Medium)](https://medium.com/iceapple-tech-talks/integration-with-google-calendar-api-using-service-account-1471e6e102c8)
- 🚀 [Guía de 30 Minutos - Service Accounts](https://www.salesforceben.com/google-api-and-service-accounts-get-up-and-running-in-30-minutes/)
- 📝 [Crear Service Account - Guía Visual](https://docs.edna.io/kb/get-service-json/)

---

## 🔗 Archivos Relacionados del Proyecto

### Archivos de Configuración:

| Archivo | Descripción |
|---------|-------------|
| `credentials/service-account.json` | ⚠️ **Credenciales reales** (debe crearse manualmente) |
| `credentials/README.md` | 📖 Esta guía |
| `mcp_server/.env` | ⚙️ Variables de entorno del servidor MCP |
| `mcp_server/.env.example` | 📄 Plantilla de variables de entorno |
| `DockerConfig/docker-compose.yml` | 🐳 Configuración Docker (monta credenciales) |

### Código Fuente Relevante:

| Archivo | Descripción | Líneas Clave |
|---------|-------------|--------------|
| `mcp_server/config/settings.py` | Configuración de Google Calendar | :113, :416-434 |
| `mcp_server/utils/google_calendar.py` | Cliente de Google Calendar | :195-280 |
| `mcp_server/tools/bookings.py` | Herramientas de reservas | :151-154 |

---

## 🎯 Resumen: Inicio Rápido

### Para Usuarios Impacientes:

```bash
# 1. Ve a Google Cloud Console y crea un proyecto
open https://console.cloud.google.com/

# 2. Habilita Google Calendar API
# APIs & Services → Library → Google Calendar API → Enable

# 3. Crea Service Account
# APIs & Services → Credentials → Create Credentials → Service Account
# Nombre: mcp-calendar-service

# 4. Descarga clave JSON
# Service Accounts → tu service account → Keys → Add Key → JSON

# 5. Guarda el archivo
mv ~/Downloads/tu-proyecto-*.json credentials/service-account.json

# 6. Obtén el email de la service account
python3 -c "import json; print(json.load(open('credentials/service-account.json'))['client_email'])"

# 7. Comparte tu calendario con ese email en Google Calendar
# Permisos: "Make changes to events"

# 8. Configura variables de entorno
nano mcp_server/.env
# GOOGLE_CALENDAR_ENABLED=true
# GOOGLE_CALENDAR_ID=tu-email@gmail.com
# GOOGLE_CALENDAR_TIMEZONE=America/Costa_Rica

# 9. Verifica
make validate
# O con Docker:
make docker-start && make docker-logs SERVICE=mcp-server
```

---

## 💡 Consejos Finales

### ✅ Mejores Prácticas:

1. **Usa nombres descriptivos** para tus service accounts (`mcp-calendar-service`, no `sa-1234`)
2. **Documenta qué calendario usas** (en comentarios del `.env`)
3. **Rota las claves cada 90 días** (mejor práctica de seguridad)
4. **Prueba localmente primero** antes de desplegar en Docker/producción
5. **Monitorea el uso de API** regularmente en el dashboard de Google Cloud

### ⚠️ Errores Comunes a Evitar:

1. ❌ Olvidar compartir el calendario con la service account
2. ❌ Usar el placeholder en lugar de credenciales reales
3. ❌ No habilitar Google Calendar API en el proyecto GCP
4. ❌ Usar `GOOGLE_CALENDAR_ID=primary` con calendarios personales
5. ❌ Subir el archivo `service-account.json` a Git

### 🎓 Para Aprender Más:

- Lee la [documentación oficial](https://developers.google.com/calendar/api/guides/overview)
- Experimenta con [Google Calendar API Explorer](https://developers.google.com/calendar/api/v3/reference)
- Revisa los ejemplos de código en `mcp_server/utils/google_calendar.py`

---

## 📞 Soporte

Si tienes problemas después de seguir esta guía:

1. ✅ Revisa el **Checklist de Diagnóstico Completo** (arriba)
2. ✅ Lee la sección de **Troubleshooting** completa
3. ✅ Verifica los logs de la aplicación: `make docker-logs SERVICE=mcp-server`
4. ✅ Consulta la [documentación oficial de Google](https://developers.google.com/calendar)

---

**Última actualización:** 2025-10-29
**Versión del documento:** 2.0 (Enhanced)
**Validado con:** Google Cloud Console (Octubre 2025)
