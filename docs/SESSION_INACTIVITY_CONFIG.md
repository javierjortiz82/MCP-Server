# Session Inactivity Configuration

## ⚙️ Configuración Actual

```bash
SESSION_TTL_MINUTES=60
SESSION_IDLE_TIMEOUT_MINUTES=1        # ← 1 MINUTO DE INACTIVIDAD
SESSION_ABSOLUTE_TIMEOUT_MINUTES=480
```

## 🎯 Comportamiento

### **Regla Simple:**
**"Si el usuario no hace nada durante 1 minuto, su sesión expira y debe re-autenticar con OTP"**

---

## 📊 Flujo de Inactividad

### **Timeline:**

```
T=00:00 ─ Usuario autentica con OTP
         ├─ Session creada
         └─ last_activity_at = 00:00
         └─ ⏰ Expira en: 01:00

T=00:15 ─ Usuario hace request #1
         └─ Sesión actualizada
         └─ last_activity_at = 00:15
         └─ ⏰ Expira en: 01:15

T=00:45 ─ Usuario hace request #2
         └─ Sesión actualizada
         └─ last_activity_at = 00:45
         └─ ⏰ Expira en: 01:45

T=01:00 ─ Usuario está viendo la pantalla pero sin hacer nada
         └─ SIN NUEVO REQUEST
         └─ last_activity_at sigue siendo = 00:45

T=01:45 ─ ⏰ TIMEOUT ALCANZADO
         └─ (01:45 - 00:45 = 1 minuto exacto)
         └─ SESIÓN EXPIRA ❌

T=01:46 ─ Usuario intenta hacer request #3
         └─ SessionExpiryMiddleware valida
         └─ Detecta: idle_timeout
         └─ 🔴 Retorna 401 Unauthorized
         └─ Mensaje: "Session expired (idle_timeout)"
         └─ Elimina sesión de BD

T=01:47 ─ Usuario re-autentica
         ├─ POST /v1/auth/resend-otp
         ├─ Recibe nuevo OTP
         ├─ POST /v1/auth/verify-otp
         └─ ✅ Nueva sesión creada (nueva última actividad)
```

---

## 🔑 Puntos Clave

### **1. La inactividad se cuenta desde el ÚLTIMO REQUEST**

```
Último request: 00:45
Espera sin requests: 01:00 - 00:45 = 15 minutos
PERO timer solo se activa después de 1 minuto sin requests
```

### **2. Cada request "reinicia el reloj"**

```
00:00 - Autentica (timeout en 01:00)
00:30 - Request 1 (timeout AHORA en 01:30) ← Reinicia
00:50 - Request 2 (timeout AHORA en 01:50) ← Reinicia
01:30 - Request 3 (timeout AHORA en 02:30) ← Reinicia
```

**Resultado: Mientras el usuario esté activo, nunca expira**

### **3. Solo requiere re-auth si está INACTIVO**

```
✅ Usuario activo cada 30 segundos → Nunca expira
❌ Usuario inactivo 2+ minutos → EXPIRA y requiere OTP
```

---

## 🧪 Testing

### **Ejecutar Test Automático:**

```bash
python scripts/test_session_inactive.py
```

**Salida esperada:**
```
========================================================================
SESSION INACTIVITY TIMEOUT TEST (1 MINUTE)
========================================================================

📌 STEP 1: Creating test session...
✅ Session created:
   Session ID: sess_test_abc12345
   User ID: javierjortiz82
   Created: 2025-11-18T10:00:00Z
   Last Activity: 2025-11-18T10:00:00Z

📌 STEP 2: Verifying session is valid...
✅ Session expired? False
   Status: ✅ VALID

📌 STEP 3: Simulating 2 minutes of inactivity...
⏱️  Inactivity timeout configured: 1 minute(s)
⏱️  Simulating: 2 minutes without activity

✅ Activity timestamp updated:
   Current time: 2025-11-18T10:02:00Z
   Last activity: 2025-11-18T10:00:00Z
   Elapsed time: 120 seconds (2.00 minutes)

📌 STEP 4: Checking if session has expired...
✅ Session expired? True
   Status: ❌ EXPIRED
   Reason: idle_timeout

📌 STEP 5: Invalidating expired session...
✅ Session invalidated (deleted from database)

📌 STEP 6: API Response on next request...
Response: 401 Unauthorized
{
  "success": false,
  "error": "SessionExpired",
  "message": "Session expired (idle_timeout). Please log in again.",
  "reason": "idle_timeout",
  "action": "login",
  "hint": "Your session has expired. Please log in again with OTP verification."
}

========================================================================
✅ TEST PASSED: Session inactivity timeout working correctly
========================================================================
```

---

## 📱 Experiencia del Usuario

### **Scenario 1: Usuario Activo (No ve 401)**

```
10:00 - Abre la app, ingresa email
10:00:30 - Completa OTP, recibe sesión
10:00:45 - Hace pregunta #1 ✅
10:01:15 - Hace pregunta #2 ✅
10:01:50 - Hace pregunta #3 ✅
...
🎉 Usuario sigue trabajando sin interrupciones
```

### **Scenario 2: Usuario Inactivo (Ve 401 y re-autentica)**

```
10:00 - Abre la app, ingresa email
10:00:30 - Completa OTP, recibe sesión
10:00:45 - Hace pregunta #1 ✅
10:02:00 - Se va a tomar café (inactivo)
10:02:10 - Vuelve, intenta hacer pregunta #2
        ❌ 401 SessionExpired
        → Frontend muestra: "Tu sesión expiró"
        → Redirige a login
10:02:15 - Usuario re-ingresa email
10:02:20 - Recibe nuevo OTP
10:02:30 - Ingresa OTP
10:02:35 - Nueva sesión creada ✅
10:02:40 - Hace pregunta #2 ✅
```

---

## 🔐 Ventajas de Seguridad

1. **Protección contra session hijacking** en computadoras compartidas
   - Si alguien toma la sesión, expira en 1 minuto si no usa la app

2. **Prevención de acceso no autorizado**
   - Cada sesión requiere OTP válido

3. **Auditoría mejorada**
   - Cada re-autenticación queda registrada
   - Fácil detectar acceso anómalo

4. **Cumple OWASP estándares**
   - ✅ Idle timeout implementado
   - ✅ Activity tracking per request
   - ✅ Session invalidation automática

---

## 🔧 Cómo Cambiar los Timeouts

### **Si necesitas aumentar a 5 minutos (menos interrupciones):**

```bash
# En .env
SESSION_IDLE_TIMEOUT_MINUTES=5
```

### **Si necesitas reducir a 30 segundos (más seguridad):**

```bash
# En .env
SESSION_IDLE_TIMEOUT_MINUTES=0.5  # 30 segundos
```

### **Después de cambiar:**

1. Reinicia el servidor
2. Los cambios se cargan automáticamente
3. Nuevas sesiones usarán el nuevo timeout

---

## 📊 Configuración Recomendada

### **Por tipo de aplicación:**

| Aplicación | TTL | Idle Timeout | Razón |
|-----------|-----|--------------|--------|
| Banca online | 30 min | 5 min | Muy sensible |
| Email | 60 min | 15 min | Sensible |
| Social network | 480 min | 30 min | Menos sensible |
| **Demo Agent** | **60 min** | **1 min** | Testing + seguridad |

**Nota:** Nuestra configuración de 1 minuto es para **testing**. En producción, típicamente es 15-30 minutos.

---

## 🚀 Monitoreo en Logs

### **Buscar sesiones expiradas:**

```bash
# Ver todas las expiraciónes
tail -f demo_agent/logs/app.log | grep "Session expired"

# Resultado:
# 2025-11-18 10:02:00 WARNING - Session expired, session_id=sess_abc123xyz, reason=idle_timeout, path=/v1/demo
```

### **Buscar re-autenticaciones:**

```bash
tail -f demo_agent/logs/app.log | grep "User authenticated"

# Resultado:
# 2025-11-18 10:02:35 INFO - User authenticated successfully, clerk_user_id=user_xxx, email=javierjortiz82@gmail.com
```

---

## 💾 Base de Datos

### **Ver sesión activa:**

```sql
SELECT session_id, user_id, last_activity_at, created_at
FROM test.demo_sessions
WHERE session_id = 'sess_abc123xyz';
```

### **Ver cuándo expira una sesión:**

```sql
SELECT
  session_id,
  last_activity_at,
  NOW() AT TIME ZONE 'UTC' as now,
  (NOW() AT TIME ZONE 'UTC' - last_activity_at) as inactive_duration,
  CASE
    WHEN (NOW() AT TIME ZONE 'UTC' - last_activity_at) > INTERVAL '1 minute'
    THEN 'EXPIRED ❌'
    ELSE 'VALID ✅'
  END as status
FROM test.demo_sessions
WHERE user_id = 'javierjortiz82';
```

---

## 🎓 Resumen para Usuarios

**Para javierjortiz82@gmail.com:**

```
✅ INGRESAS A LA APP
   ├─ Email: javierjortiz82@gmail.com
   ├─ Recibes OTP por correo
   ├─ Ingresas OTP
   └─ ✅ Acceso otorgado

✅ ESTÁS USANDO LA APP
   ├─ Haces preguntas
   ├─ Ves respuestas
   └─ La sesión se renueva con cada uso

⏱️ TE VAS A TOMAR CAFÉ (1 minuto sin hacer nada)
   └─ La sesión expira automáticamente

❌ VUELVES Y TRIES HACER OTRA PREGUNTA
   ├─ El sistema dice: "Session expired"
   ├─ Te redirige a login
   └─ Necesitas re-ingresar OTP

✅ RE-INGRESAS OTP
   ├─ Recibes nuevo OTP
   ├─ Ingresas OTP
   └─ ✅ Nuevamente tienes acceso
```

---

## 📞 Soporte

Si la sesión expira muy frecuentemente:
- **Aumenta** `SESSION_IDLE_TIMEOUT_MINUTES` en `.env`

Si quieres más seguridad:
- **Disminuye** `SESSION_IDLE_TIMEOUT_MINUTES` en `.env`

Cambios requieren **reinicio del servidor**.

---

**Last Updated:** 2025-11-18
**Configuration Version:** 1.0.0
