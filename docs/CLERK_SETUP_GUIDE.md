# Guía de Configuración de Clerk para Odiseo Sales AI

Esta guía detalla paso a paso cómo configurar Clerk como Identity Provider para el proyecto Odiseo Sales AI con autenticación federada (Google, Apple, Microsoft).

---

## 1. Creación de Cuenta y Aplicación en Clerk

### 1.1 Registro en Clerk

1. Navega a [https://clerk.com](https://clerk.com)
2. Haz clic en "Start building for free"
3. Regístrate con tu email corporativo o cuenta de Google
4. Verifica tu email

### 1.2 Crear Nueva Aplicación

1. En el Dashboard de Clerk, haz clic en **"Create application"**
2. Configuración inicial:
   - **Application name**: `Odiseo Sales AI`
   - **Select sign-in methods**:
     - ✅ Email address
     - ✅ Google
     - ✅ Apple
     - ✅ Microsoft
   - **Choose authentication strategy**:
     - Selecciona "Social login (OAuth)" como primario
     - Mantén "Email verification" como fallback
3. Haz clic en **"Create application"**

### 1.3 Obtener API Keys

Una vez creada la aplicación:

1. Ve a **"API Keys"** en el menú lateral
2. Copia las siguientes keys:
   ```
   CLERK_PUBLISHABLE_KEY=pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXX
   CLERK_SECRET_KEY=sk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```
3. **IMPORTANTE**: Guarda el `CLERK_SECRET_KEY` en un lugar seguro. Solo se muestra una vez.

---

## 2. Configuración de OAuth Providers

### 2.1 Google OAuth

#### Paso 1: Crear Proyecto en Google Cloud Console

1. Navega a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto:
   - **Project name**: `Odiseo Sales AI`
   - **Organization**: Tu organización
3. Habilita la API de Google+:
   - Ve a **"APIs & Services" > "Library"**
   - Busca "Google+ API"
   - Haz clic en **"Enable"**

#### Paso 2: Configurar OAuth Consent Screen

1. Ve a **"APIs & Services" > "OAuth consent screen"**
2. Configuración:
   - **User type**: External (para permitir cualquier cuenta Google)
   - **App name**: `Odiseo Sales AI`
   - **User support email**: tu email corporativo
   - **App logo**: (opcional, sube el logo de Odiseo)
   - **Developer contact email**: tu email corporativo
3. **Scopes**: Agrega los siguientes:
   - `userinfo.email`
   - `userinfo.profile`
   - `openid`
4. Guarda y continúa

#### Paso 3: Crear OAuth 2.0 Credentials

1. Ve a **"APIs & Services" > "Credentials"**
2. Haz clic en **"Create Credentials" > "OAuth client ID"**
3. Configuración:
   - **Application type**: Web application
   - **Name**: `Odiseo Sales AI - Clerk`
   - **Authorized JavaScript origins**:
     ```
     https://accounts.clerk.com
     http://localhost:8080 (desarrollo)
     ```
   - **Authorized redirect URIs**:
     ```
     https://accounts.clerk.com/v1/oauth_callback
     http://localhost:8080/auth/callback (desarrollo)
     ```
4. Copia el **Client ID** y **Client Secret**

#### Paso 4: Configurar en Clerk

1. En Clerk Dashboard, ve a **"User & Authentication" > "Social Connections"**
2. Selecciona **"Google"**
3. Habilita el toggle "Enable Google"
4. Pega las credenciales:
   - **Client ID**: (del paso anterior)
   - **Client Secret**: (del paso anterior)
5. Guarda

---

### 2.2 Apple OAuth

#### Paso 1: Configurar en Apple Developer Portal

1. Navega a [Apple Developer Portal](https://developer.apple.com/account/)
2. Ve a **"Certificates, Identifiers & Profiles"**
3. Selecciona **"Identifiers"** en el menú lateral
4. Haz clic en el botón **"+"** para crear un nuevo identifier

#### Paso 2: Crear App ID

1. Selecciona **"App IDs"** y haz clic en **"Continue"**
2. Configuración:
   - **Description**: `Odiseo Sales AI`
   - **Bundle ID**: `com.odiseo.salesai` (explicit)
   - **Capabilities**: Marca **"Sign in with Apple"**
3. Haz clic en **"Continue"** y luego **"Register"**

#### Paso 3: Crear Service ID

1. De vuelta en **"Identifiers"**, haz clic en **"+"**
2. Selecciona **"Services IDs"** y haz clic en **"Continue"**
3. Configuración:
   - **Description**: `Odiseo Sales AI - Web`
   - **Identifier**: `com.odiseo.salesai.web`
   - Marca **"Sign in with Apple"**
4. Haz clic en **"Configure"** junto a "Sign in with Apple"
5. Configuración de dominio:
   - **Primary App ID**: Selecciona el App ID creado anteriormente
   - **Domains and Subdomains**:
     ```
     accounts.clerk.com
     localhost (desarrollo)
     ```
   - **Return URLs**:
     ```
     https://accounts.clerk.com/v1/oauth_callback
     http://localhost:8080/auth/callback (desarrollo)
     ```
6. Guarda y registra

#### Paso 4: Crear Private Key

1. Ve a **"Keys"** en el menú lateral
2. Haz clic en **"+"** para crear una nueva key
3. Configuración:
   - **Key Name**: `Odiseo Sales AI Sign In Key`
   - Marca **"Sign in with Apple"**
   - Haz clic en **"Configure"**
   - Selecciona el App ID principal
4. Haz clic en **"Continue"** y luego **"Register"**
5. **Descarga la key** (archivo .p8)
   - ⚠️ **IMPORTANTE**: Solo puedes descargarla una vez. Guárdala en lugar seguro.
6. Anota el **Key ID** (se muestra arriba del botón Download)

#### Paso 5: Configurar en Clerk

1. En Clerk Dashboard, ve a **"Social Connections"**
2. Selecciona **"Apple"**
3. Habilita el toggle "Enable Apple"
4. Configuración:
   - **Services ID**: `com.odiseo.salesai.web`
   - **Team ID**: (encuéntralo en el esquina superior derecha del Apple Developer Portal)
   - **Key ID**: (del paso 4)
   - **Private Key**: Pega el contenido del archivo .p8 (incluyendo BEGIN/END lines)
5. Guarda

---

### 2.3 Microsoft OAuth

#### Paso 1: Registrar Aplicación en Azure AD

1. Navega a [Azure Portal](https://portal.azure.com/)
2. Ve a **"Azure Active Directory" > "App registrations"**
3. Haz clic en **"New registration"**
4. Configuración:
   - **Name**: `Odiseo Sales AI`
   - **Supported account types**:
     - Selecciona "Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts"
   - **Redirect URI**:
     - **Platform**: Web
     - **URI**: `https://accounts.clerk.com/v1/oauth_callback`
5. Haz clic en **"Register"**

#### Paso 2: Crear Client Secret

1. En la aplicación recién creada, ve a **"Certificates & secrets"**
2. Haz clic en **"New client secret"**
3. Configuración:
   - **Description**: `Clerk Integration`
   - **Expires**: 24 months (o según política de seguridad)
4. Haz clic en **"Add"**
5. **Copia el Value del secret** (solo se muestra una vez)

#### Paso 3: Configurar Permisos API

1. Ve a **"API permissions"**
2. Haz clic en **"Add a permission"**
3. Selecciona **"Microsoft Graph"**
4. Selecciona **"Delegated permissions"**
5. Agrega los siguientes permisos:
   - `openid`
   - `profile`
   - `email`
   - `User.Read`
6. Haz clic en **"Add permissions"**
7. Haz clic en **"Grant admin consent for [Your Organization]"**

#### Paso 4: Obtener Application ID

1. En la página **"Overview"** de tu aplicación
2. Copia el **Application (client) ID**
3. Copia el **Directory (tenant) ID**

#### Paso 5: Configurar en Clerk

1. En Clerk Dashboard, ve a **"Social Connections"**
2. Selecciona **"Microsoft"**
3. Habilita el toggle "Enable Microsoft"
4. Configuración:
   - **Client ID**: (Application ID del paso 4)
   - **Client Secret**: (del paso 2)
   - **Tenant ID**: (del paso 4) - usa `common` para multi-tenant
5. Guarda

---

## 3. Configuración de Webhooks

### 3.1 Crear Endpoint en Clerk

1. En Clerk Dashboard, ve a **"Webhooks"**
2. Haz clic en **"Add Endpoint"**
3. Configuración:
   - **Endpoint URL**:
     - Desarrollo: `http://localhost:8000/v1/webhooks/clerk` (usa ngrok para testing)
     - Producción: `https://api.odiseo.com/v1/webhooks/clerk`
   - **Message Filtering**: Selecciona los siguientes eventos:
     - ✅ `user.created`
     - ✅ `user.updated`
     - ✅ `user.deleted`
     - ✅ `session.created`
4. Haz clic en **"Create"**

### 3.2 Obtener Webhook Secret

1. Una vez creado el endpoint, haz clic en él
2. Ve a la sección **"Signing Secret"**
3. Copia el secret:
   ```
   CLERK_WEBHOOK_SECRET=whsec_XXXXXXXXXXXXXXXXXXXXXXXX
   ```
4. Guárdalo para configurar en el backend

### 3.3 Testing de Webhooks (Desarrollo con ngrok)

Para testing local:

```bash
# Instalar ngrok
npm install -g ngrok

# Exponer puerto 8000
ngrok http 8000

# Copiar la URL HTTPS generada (ej: https://abc123.ngrok.io)
# Actualizar el webhook endpoint en Clerk con: https://abc123.ngrok.io/v1/webhooks/clerk
```

---

## 4. Personalización de Clerk

### 4.1 Branding

1. En Clerk Dashboard, ve a **"Customization" > "Appearance"**
2. **Theme**:
   - Selecciona el tema base (Light/Dark/Auto)
3. **Colors**:
   - **Primary color**: `#your-brand-color` (ej: `#0066CC` para Odiseo)
   - **Background**: Ajusta según tu diseño
4. **Logo**:
   - Sube el logo de Odiseo (formato PNG, máx 500KB)
   - Recomendado: 200x50px
5. **Layout**:
   - Selecciona "Card" o "Full page" según preferencia

### 4.2 Configuración de Idiomas (i18n)

1. Ve a **"Customization" > "Localization"**
2. **Default locale**: Spanish (`es`)
3. **Available locales**:
   - ✅ Spanish (`es`)
   - ✅ English (`en`)
   - (Agrega más según necesidad)
4. Haz clic en **"Customize messages"** para personalizar textos:
   - Botón de login: "Iniciar sesión con Google"
   - Mensajes de error en español
   - Emails de verificación en español

### 4.3 Email Templates

1. Ve a **"Customization" > "Emails"**
2. Personaliza los siguientes templates:

#### Email de Verificación
```html
Hola {{user.firstName}},

Bienvenido a Odiseo Sales AI.

Haz clic en el siguiente enlace para verificar tu email:
{{verification.url}}

Este enlace expira en 24 horas.

Saludos,
Equipo de Odiseo Sales AI
```

#### Email de Bienvenida
```html
¡Hola {{user.firstName}}!

Gracias por registrarte en Odiseo Sales AI.

Tu cuenta está lista para usar. Puedes iniciar sesión en:
https://app.odiseo.com

Si tienes preguntas, no dudes en contactarnos.

Saludos,
Equipo de Odiseo Sales AI
```

### 4.4 Configurar Metadata Custom

1. Ve a **"User & Authentication" > "User metadata"**
2. Agrega campos custom para el signup:
   - **company** (string): Nombre de la empresa
   - **role** (string): Cargo del usuario
   - **phone** (string): Teléfono de contacto
   - **industry** (string): Industria/sector

Estos campos se capturarán durante el registro y se sincronizarán con Postgres vía webhooks.

---

## 5. Variables de Entorno - Resumen

Al finalizar la configuración, deberías tener las siguientes variables:

### Backend (`demo_agent/.env`)
```bash
# Clerk API Keys
CLERK_SECRET_KEY=sk_test_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
CLERK_PUBLISHABLE_KEY=pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXX
CLERK_WEBHOOK_SECRET=whsec_XXXXXXXXXXXXXXXXXXXXXXXX
CLERK_API_URL=https://api.clerk.com/v1

# Google OAuth (Opcional - solo si necesitas llamar directamente a Google API)
GOOGLE_CLIENT_ID=XXXXXX.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-XXXXXXXXXXXXX

# Apple OAuth (Opcional)
APPLE_TEAM_ID=XXXXXXXXXX
APPLE_KEY_ID=XXXXXXXXXX
APPLE_SERVICE_ID=com.odiseo.salesai.web

# Microsoft OAuth (Opcional)
MICROSOFT_CLIENT_ID=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
MICROSOFT_CLIENT_SECRET=XXXXXXXXXXXXXXXXXXXXXXXXXXXX
MICROSOFT_TENANT_ID=common
```

### Frontend (`odiseo-sales-ai/.env`)
```bash
# Clerk
VITE_CLERK_PUBLISHABLE_KEY=pk_test_XXXXXXXXXXXXXXXXXXXXXXXXXX

# API
VITE_API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL_PROD=https://api.odiseo.com
```

---

## 6. Checklist de Configuración Completa

Antes de proceder a la implementación del código, verifica:

- [ ] Cuenta de Clerk creada y aplicación configurada
- [ ] Google OAuth configurado (Client ID y Secret obtenidos)
- [ ] Apple OAuth configurado (Service ID, Team ID, Key ID, Private Key obtenidos)
- [ ] Microsoft OAuth configurado (Application ID, Client Secret, Tenant ID obtenidos)
- [ ] Los 3 OAuth providers habilitados en Clerk
- [ ] Webhook endpoint creado y Signing Secret obtenido
- [ ] Branding personalizado (logo, colores)
- [ ] Localización configurada (español como default)
- [ ] Email templates personalizados
- [ ] Metadata custom fields configurados
- [ ] Todas las variables de entorno documentadas
- [ ] ngrok instalado para testing local de webhooks (desarrollo)

---

## 7. Siguiente Paso

Una vez completada esta configuración, procede con la **Fase 2: Migraciones de Base de Datos**.

Todas las API keys y secrets deben almacenarse en archivos `.env` que **NO** se deben commitear a Git (agregar a `.gitignore`).

---

**Documentado por**: Claude Code
**Fecha**: 2025-11-03
**Proyecto**: Odiseo Sales AI - Clerk Authentication Integration
