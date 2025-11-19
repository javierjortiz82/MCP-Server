# Session Re-authentication Flow

## Configuración Actual

```
SESSION_TTL_MINUTES=60              # Duración máxima de sesión: 60 minutos
SESSION_IDLE_TIMEOUT_MINUTES=1      # ⚡ TIMEOUT POR INACTIVIDAD: 1 MINUTO
SESSION_ABSOLUTE_TIMEOUT_MINUTES=480  # Máximo absoluto: 8 horas
```

## Flujo Completo: Usuario inactivo → Re-autenticación con OTP

### **FASE 1: Usuario Autentica y Crea Sesión**

```
┌──────────────────────────────────────────────────────┐
│ 1. Usuario accede a la aplicación                    │
│    Email: javierjortiz82@gmail.com                   │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 2. Sistema envía OTP (6 dígitos)                     │
│    ⏱️ Válido por: 10 minutos (OTP_EXPIRATION)        │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 3. Usuario ingresa OTP                               │
│    POST /v1/auth/verify-otp                          │
│    Body: {"email": "...", "otp_code": "123456"}     │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 4. ✅ OTP Verificado - Sesión Creada                 │
│    Response: {                                       │
│      "session_id": "sess_abc123xyz",                 │
│      "user_id": 1,                                   │
│      "is_authenticated": true,                       │
│      "message": "Authentication successful"          │
│    }                                                 │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 5. 🎯 SESIÓN ACTIVA                                 │
│    created_at:      2025-11-18 10:00:00 UTC        │
│    last_activity_at: 2025-11-18 10:00:00 UTC       │
│    Status: ✅ VÁLIDA                                │
└──────────────────────────────────────────────────────┘
```

---

### **FASE 2: Usuario Hace Requests - Sesión se Renueva**

```
T=10:00 - Usuario autentica
         ├─ created_at: 10:00
         └─ last_activity_at: 10:00
         └─ ⏱️ Timeout en: 10:01

T=10:00:15 - POST /v1/demo (Request 1)
         ├─ SessionExpiryMiddleware valida sesión
         │  └─ ¿Expirada? NO (solo 15 segundos)
         ├─ Procesa request
         ├─ Actualiza last_activity_at: 10:00:15
         └─ ⏱️ Nuevo timeout en: 10:01:15

T=10:00:45 - POST /v1/demo (Request 2)
         ├─ SessionExpiryMiddleware valida sesión
         │  └─ ¿Expirada? NO (solo 45 segundos)
         ├─ Procesa request
         ├─ Actualiza last_activity_at: 10:00:45
         └─ ⏱️ Nuevo timeout en: 10:01:45

[USUARIO ACTIVO - SESIÓN SIEMPRE VÁLIDA]
```

---

### **FASE 3: Usuario Inactivo - Sesión Expira**

```
T=10:00:45 - Último request procesado
             └─ last_activity_at: 10:00:45

T=10:01:00 - Usuario inactivo (15 segundos sin hacer nada)
             └─ Idle timeout aún no alcanzado

T=10:01:45 - ⏰ IDLE TIMEOUT ALCANZADO
             ├─ (10:01:45 - 10:00:45 = 1 minuto)
             ├─ last_activity_at:    10:00:45
             ├─ Ahora:              10:01:45
             ├─ Diferencia:         1 minuto = EXPIRADA ❌
             └─ SessionService.is_session_expired() = TRUE

T=10:02:00 - Usuario intenta hacer request
             └─ POST /v1/demo

             ┌────────────────────────────────────────┐
             │ SessionExpiryMiddleware                │
             │                                        │
             │ 1. Obtiene sesión de BD                │
             │ 2. Llama is_session_expired()          │
             │ 3. Comprueba idle timeout:             │
             │    (now - last_activity_at) > 1 min    │
             │    (10:02:00 - 10:00:45) = 1:15 min    │
             │    1:15 > 1:00 ✅ TRUE                 │
             │ 4. Obtiene razón: "idle_timeout"       │
             │ 5. Invalida sesión (DELETE en BD)      │
             │ 6. Retorna 401 Unauthorized            │
             └────────────────────────────────────────┘
                          ↓
             ┌────────────────────────────────────────┐
             │ 🔴 RESPUESTA 401 UNAUTHORIZED          │
             │                                        │
             │ HTTP/1.1 401 Unauthorized              │
             │ Content-Type: application/json         │
             │                                        │
             │ {                                      │
             │   "success": false,                    │
             │   "error": "SessionExpired",           │
             │   "message": "Session expired          │
             │    (idle_timeout). Please log in       │
             │    again.",                            │
             │   "reason": "idle_timeout",            │
             │   "action": "login",                   │
             │   "hint": "Your session has            │
             │    expired. Please log in again        │
             │    with OTP verification."             │
             │ }                                      │
             └────────────────────────────────────────┘
```

---

### **FASE 4: Re-autenticación con OTP**

```
┌──────────────────────────────────────────────────────┐
│ Usuario recibe 401 SessionExpired                    │
│ ⚠️ Frontend redirige a pantalla de login             │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ Usuario vuelve a escribir email:                     │
│ javierjortiz82@gmail.com                             │
│                                                      │
│ POST /v1/auth/resend-otp                             │
│ Body: {"email": "javierjortiz82@gmail.com"}         │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ ✉️ Sistema envía NUEVO OTP                           │
│                                                      │
│ Email recibido con código: 654321                   │
│ ⏱️ Válido por: 10 minutos                           │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ Usuario verifica OTP:                                │
│                                                      │
│ POST /v1/auth/verify-otp                             │
│ Body: {                                              │
│   "email": "javierjortiz82@gmail.com",              │
│   "otp_code": "654321"                              │
│ }                                                    │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ ✅ NUEVA SESIÓN CREADA                               │
│                                                      │
│ Response: {                                          │
│   "session_id": "sess_xyz789abc",  (NUEVA)           │
│   "user_id": 1,                                      │
│   "is_authenticated": true,                          │
│   "message": "Authentication successful"             │
│ }                                                    │
│                                                      │
│ Sesión anterior (sess_abc123xyz) fue ELIMINADA     │
│ Nueva sesión (sess_xyz789abc) ACTIVA                │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 🎉 Usuario autenticado nuevamente                    │
│ Puede usar la aplicación otra vez                    │
└──────────────────────────────────────────────────────┘
```

---

## Diagrama de Timeline

```
TIEMPO    EVENTO                  ESTADO SESIÓN              ACCIÓN
═════════════════════════════════════════════════════════════════════
10:00     Login OTP verificado    ✅ CREADA                 Crear sesión
          created_at: 10:00       last_activity: 10:00
          ⏰ Timeout en: 10:01

10:00:15  POST /v1/demo          ✅ ACTIVA                 Actualizar
          Request 1              last_activity: 10:00:15   última actividad
          ⏰ Timeout en: 10:01:15

10:00:45  POST /v1/demo          ✅ ACTIVA                 Actualizar
          Request 2              last_activity: 10:00:45   última actividad
          ⏰ Timeout en: 10:01:45

10:01:50  Usuario inactivo       ✅ VÁLIDA AÚN             (esperando)
          (sin hacer requests)   Falta: 10 segundos
          ⏰ Timeout en: 10:01:45

10:02:00  POST /v1/demo          ❌ EXPIRADA               Retorna 401
          Request 3              idle_timeout              Elimina sesión
          Ahora: 10:02:00        (1 min 15 seg)
          última: 10:00:45       ➜ > 1 minuto

          [SessionExpiryMiddleware]
          - Detecta expiración
          - Invalida sesión (DELETE)
          - Retorna 401 Unauthorized

10:02:05  POST /v1/auth/resend   📧 Envía OTP              Enviar email
          -otp                   Código: 654321
          Email request          ⏱️ Válido 10 min

10:02:30  POST /v1/auth/verify   ✅ NUEVA SESIÓN           Crear nueva
          -otp                   created_at: 10:02:30      sesión
          OTP: 654321            last_activity: 10:02:30
                                 ⏰ Timeout en: 10:03:30

10:03:00  POST /v1/demo          ✅ ACTIVA                 Actualizar
          Request 4              last_activity: 10:03:00   última actividad
          ⏰ Timeout en: 10:04:00
```

---

## Respuestas del Sistema

### ✅ **Sesión Válida - 200 OK**

```json
{
  "success": true,
  "response": "Los laptops varían entre $500 y $3000...",
  "tokens_used": 150,
  "tokens_remaining": 4850,
  "session_id": "sess_abc123xyz",
  "created_at": "2025-11-18T10:00:00Z"
}
```

### ❌ **Sesión Expirada - 401 Unauthorized**

```json
{
  "success": false,
  "error": "SessionExpired",
  "message": "Session expired (idle_timeout). Please log in again.",
  "reason": "idle_timeout",
  "action": "login",
  "hint": "Your session has expired. Please log in again with OTP verification."
}
```

### ✅ **OTP Verificado - Nueva Sesión Creada**

```json
{
  "success": true,
  "session_id": "sess_xyz789abc",
  "user_id": 1,
  "email": "javierjortiz82@gmail.com",
  "is_authenticated": true,
  "message": "Authentication successful",
  "created_at": "2025-11-18T10:02:30Z"
}
```

---

## Posibles Escenarios

### **Escenario 1: Usuario Muy Inactivo**
```
10:00 - Autentica
10:01 - Inactivo 1 minuto
10:02 - Intenta request → ❌ 401 Session Expired
10:03 - Ingresa OTP nuevamente → ✅ Nueva sesión
```

### **Escenario 2: Usuario Continuamente Activo**
```
10:00 - Autentica
10:00:15 - Request 1 (última actividad: 10:00:15)
10:00:45 - Request 2 (última actividad: 10:00:45)
10:01:15 - Request 3 (última actividad: 10:01:15)
10:02:15 - Request 4 (última actividad: 10:02:15)
...
✅ Sesión nunca expira mientras haya actividad
```

### **Escenario 3: Usuario Activo, Luego Inactivo**
```
10:00 - Autentica (última actividad: 10:00)
10:00:30 - Request 1 (última actividad: 10:00:30)
10:00:50 - Request 2 (última actividad: 10:00:50)
10:01:45 - Sin hacer nada (último request: 10:00:50)
10:01:51 - ⏰ TIMEOUT (10:01:51 - 10:00:50 = 1:01 > 1 minuto)
10:02:00 - Intenta request → ❌ 401 Session Expired
10:02:10 - Ingresa OTP nuevamente → ✅ Nueva sesión
```

---

## Logs Esperados

```
2025-11-18 10:00:00 INFO - User authenticated successfully, session_id=sess_abc123xyz
2025-11-18 10:00:15 INFO - Session validated and activity updated, session_id=sess_abc123xyz
2025-11-18 10:00:45 INFO - Session validated and activity updated, session_id=sess_abc123xyz
2025-11-18 10:02:00 WARNING - Session expired, session_id=sess_abc123xyz, reason=idle_timeout, path=/v1/demo
2025-11-18 10:02:00 INFO - Session invalidated: sess_abc123xyz
2025-11-18 10:02:05 INFO - OTP sent to javierjortiz82@gmail.com
2025-11-18 10:02:30 INFO - User authenticated successfully, session_id=sess_xyz789abc
```

---

## Base de Datos - Cambios de Sesión

### **Antes de Expiración**
```sql
SELECT * FROM test.demo_sessions
WHERE session_id = 'sess_abc123xyz';

session_id          | user_id | last_activity_at        | created_at
────────────────────┼─────────┼─────────────────────────┼──────────────
sess_abc123xyz      | 1       | 2025-11-18 10:00:50 UTC | 2025-11-18 10:00:00 UTC
```

### **Después de Expiración**
```sql
SELECT * FROM test.demo_sessions
WHERE session_id = 'sess_abc123xyz';

-- VACÍO (sesión eliminada)
```

### **Después de Nueva Autenticación**
```sql
SELECT * FROM test.demo_sessions
WHERE session_id = 'sess_xyz789abc';

session_id          | user_id | last_activity_at        | created_at
────────────────────┼─────────┼─────────────────────────┼──────────────
sess_xyz789abc      | 1       | 2025-11-18 10:02:30 UTC | 2025-11-18 10:02:30 UTC
```

---

## Testing Manual

### **Test 1: Verificar Sesión Activa**
```bash
curl -X POST http://localhost:8082/v1/demo \
  -H "X-Session-ID: sess_abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{"input": "¿Cuál es el precio?"}'

# Resultado esperado: 200 OK con respuesta
```

### **Test 2: Simular Inactividad (SQL)**
```sql
UPDATE test.demo_sessions
SET last_activity_at = NOW() - INTERVAL '2 minutes'
WHERE session_id = 'sess_abc123xyz';
```

### **Test 3: Verificar Sesión Expirada**
```bash
curl -X POST http://localhost:8082/v1/demo \
  -H "X-Session-ID: sess_abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{"input": "¿Cuál es el precio?"}'

# Resultado esperado: 401 Unauthorized con mensaje SessionExpired
```

### **Test 4: Re-autenticar**
```bash
curl -X POST http://localhost:8082/v1/auth/resend-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "javierjortiz82@gmail.com"}'

# Usuario recibe OTP, luego:

curl -X POST http://localhost:8082/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "javierjortiz82@gmail.com", "otp_code": "654321"}'

# Resultado esperado: 200 OK con nueva session_id
```

---

## Configuración Actual

```ini
# .env actual
SESSION_TTL_MINUTES=60              # 60 minutos máximo
SESSION_IDLE_TIMEOUT_MINUTES=1      # 1 minuto de inactividad
SESSION_ABSOLUTE_TIMEOUT_MINUTES=480  # 8 horas máximo
```

**Esto significa:**
- ✅ Usuario puede usar la sesión hasta **60 minutos** desde creación
- ⏱️ Si es **inactivo 1 minuto**, sesión expira automáticamente
- 🔐 Debe **re-autenticar con OTP** para continuar
- 📊 Máximo absoluto: 8 horas (incluso con actividad continua)

---

## Referencias

- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html)
- Implementación: `demo_agent/security/session_expiry_middleware.py`
- Servicio: `demo_agent/services/session_service.py`
