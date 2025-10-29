# Google Calendar Credentials

Este directorio contiene las credenciales de Google Calendar necesarias para la integración de reservas.

## 📋 Prerequisitos

Para usar Google Calendar, necesitas:
1. Una cuenta de Google Cloud Platform (GCP)
2. Habilitar la Google Calendar API
3. Crear credenciales de Service Account

## 🔧 Configuración paso a paso

### 1. Crear proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Anota el Project ID

### 2. Habilitar Google Calendar API

1. En el menú lateral, ve a **APIs & Services** > **Library**
2. Busca "Google Calendar API"
3. Click en "Enable" (Habilitar)

### 3. Crear Service Account

1. Ve a **APIs & Services** > **Credentials**
2. Click en "Create Credentials" > "Service Account"
3. Nombre sugerido: `mcp-calendar-service`
4. Descripción: `Service account for MCP booking system`
5. Click "Create and Continue"
6. Rol: **Editor** (o puedes usar roles más específicos como "Calendar Editor")
7. Click "Continue" y luego "Done"

### 4. Generar clave JSON

1. En la lista de Service Accounts, click en el service account que creaste
2. Ve a la pestaña **Keys**
3. Click "Add Key" > "Create new key"
4. Selecciona **JSON** como tipo
5. Click "Create"
6. Se descargará un archivo JSON automáticamente

### 5. Colocar el archivo de credenciales

**IMPORTANTE:** Renombra el archivo descargado a `service-account.json` y colócalo en este directorio:

```bash
# Estructura esperada:
MCP-Server/
└── credentials/
    ├── README.md                        ← Esta guía
    ├── .gitkeep                         ← Mantiene el directorio en git
    ├── service-account.json.example     ← Archivo de ejemplo (NO usar en producción)
    └── service-account.json             ← ⚠️ TU archivo real (DEBES CREARLO)
```

**Nota:** El archivo `service-account.json.example` muestra la estructura esperada pero NO contiene credenciales reales. Debes crear tu propio `service-account.json` siguiendo los pasos anteriores.

### 6. Compartir el calendario con el Service Account

⚠️ **PASO CRÍTICO:** Debes compartir tu Google Calendar con la cuenta de servicio:

1. Abre el archivo `service-account.json` que descargaste
2. Busca el campo `client_email`, tendrá un formato como:
   ```
   mcp-calendar-service@tu-proyecto.iam.gserviceaccount.com
   ```
3. Copia ese email
4. Ve a [Google Calendar](https://calendar.google.com/)
5. En la lista de calendarios (lado izquierdo), busca tu calendario
6. Click en los 3 puntos → "Settings and sharing"
7. En la sección "Share with specific people", click "Add people"
8. Pega el email del service account
9. Selecciona permisos: **Make changes to events** (para crear/modificar eventos)
10. Click "Send"

### 7. Configurar variables de entorno

Edita el archivo `mcp_server/.env`:

```bash
# Google Calendar Configuration
GOOGLE_CALENDAR_CREDENTIALS_PATH=credentials/service-account.json
GOOGLE_CALENDAR_ID=tu-email@gmail.com  # O "primary" para el calendario principal
GOOGLE_CALENDAR_TIMEZONE=America/Costa_Rica  # Tu zona horaria
```

## 🐳 Configuración en Docker

El archivo de credenciales se monta automáticamente en el contenedor Docker como un volumen de solo lectura.

No necesitas hacer nada adicional si el archivo está en la ubicación correcta.

## 🔒 Seguridad

⚠️ **NUNCA** subas el archivo `service-account.json` a git.

Este directorio está incluido en `.gitignore` para prevenir commits accidentales.

### Archivo de ejemplo (service-account.json)

```json
{
  "type": "service_account",
  "project_id": "tu-proyecto-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "mcp-calendar-service@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

## ✅ Verificar configuración

Para verificar que las credenciales están configuradas correctamente:

```bash
# En local (sin Docker)
make validate

# Con Docker (después de iniciar los servicios)
make docker-logs SERVICE=mcp-server
# Busca el mensaje: "✅ Google Calendar client initialized"
```

## 🆘 Troubleshooting

### Error: "Credentials file not found"

- Verifica que el archivo esté en `credentials/service-account.json`
- Verifica que el archivo no esté corrupto (debe ser JSON válido)
- Si usas Docker, reinicia el servicio: `make docker-restart SERVICE=mcp-server`

### Error: "Invalid credentials" o "Authentication failed"

- Verifica que el archivo JSON es el correcto
- Asegúrate de que la Google Calendar API está habilitada
- Verifica que el service account tiene permisos en el calendario

### Error: "Calendar not found" o "Access denied"

- **Verifica que compartiste el calendario con el service account** (paso 6)
- El email del service account debe tener permisos de edición
- Verifica que el `GOOGLE_CALENDAR_ID` en `.env` es correcto

### Error: "Quota exceeded"

- Google Calendar API tiene límites de uso
- Verifica el [dashboard de cuotas](https://console.cloud.google.com/apis/dashboard)
- Considera solicitar aumento de cuota si es necesario

## 📚 Referencias

- [Google Calendar API Documentation](https://developers.google.com/calendar)
- [Service Accounts Overview](https://cloud.google.com/iam/docs/service-accounts)
- [Calendar API Python Quickstart](https://developers.google.com/calendar/api/quickstart/python)

## 🔗 Archivos relacionados

- `mcp_server/config/settings.py` - Configuración de Google Calendar
- `mcp_server/utils/google_calendar.py` - Cliente de Google Calendar
- `mcp_server/tools/bookings.py` - Herramientas de reservas
- `mcp_server/.env.example` - Variables de entorno de ejemplo
