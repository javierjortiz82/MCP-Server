# Frontend Migration Guide: IP Extraction Security Update

## 📌 Overview

El backend ahora extrae la dirección IP del cliente de forma **segura y automática** desde los headers HTTP. El frontend **NO debe enviar** el campo `metadata.ip` ya que esto es una vulnerabilidad de seguridad.

## 🔴 Cambio Requerido (BREAKING CHANGE)

### ❌ ANTES (Versión Anterior - INSEGURO)

```typescript
// ❌ NO HACER ESTO - Vulnerable a IP spoofing
const response = await fetch(`${API_URL}/v1/demo`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${clerkToken}`,
  },
  body: JSON.stringify({
    input: userMessage,
    language: 'es',
    metadata: {
      ip: '192.168.1.1',  // ❌ ELIMINAR - Puede ser falsificado por el usuario
      user_agent: navigator.userAgent,
      fingerprint: await generateFingerprint(),
    }
  })
});
```

### ✅ AHORA (Nueva Versión - SEGURO)

```typescript
// ✅ CORRECTO - Backend extrae IP automáticamente
const response = await fetch(`${API_URL}/v1/demo`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${clerkToken}`,
  },
  body: JSON.stringify({
    input: userMessage,
    language: 'es',
    metadata: {
      // IP se omite completamente - backend lo extrae de los headers HTTP
      user_agent: navigator.userAgent,
      fingerprint: await generateFingerprint(),
    }
  })
});
```

## 🔧 Archivos a Modificar

### Archivo: `/src/services/demoAgent.ts`

**Actualizar el método `sendMessage()`**:

```typescript
async sendMessage(
  message: string,
  language: string,
  clerkToken?: string
): Promise<DemoResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (clerkToken) {
    headers['Authorization'] = `Bearer ${clerkToken}`;
  }

  const response = await fetch(`${API_BASE_URL}/v1/demo`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      session_id: this.sessionId,
      input: message,
      language,
      metadata: {
        // ✅ IP field REMOVED - backend extracts automatically
        user_agent: navigator.userAgent,
        fingerprint: await this.generateFingerprint(),
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new DemoAgentError(error, response.status);
  }

  return response.json();
}
```

**Eliminar método `getClientIP()` (si existe)**:

```typescript
// ❌ ELIMINAR COMPLETAMENTE - Ya no es necesario
private async getClientIP(): Promise<string> {
  // ... código anterior ...
}
```

## 📋 Checklist de Migración

- [ ] Eliminar el campo `metadata.ip` de todas las requests a `/v1/demo`
- [ ] Eliminar función `getClientIP()` del servicio
- [ ] Eliminar imports relacionados con extracción de IP
- [ ] Actualizar tests del frontend
- [ ] Verificar que el endpoint `/v1/demo` funciona correctamente
- [ ] Verificar que el rate limiting sigue funcionando

## 🧪 Testing

### Test 1: Verificar Request sin IP

```typescript
// El request debe funcionar SIN el campo metadata.ip
const response = await demoAgent.sendMessage(
  "¿Cuánto cuesta un laptop?",
  "es",
  clerkToken
);

expect(response.success).toBe(true);
expect(response.response).toBeDefined();
```

### Test 2: Verificar Rate Limiting

```typescript
// El rate limiting debe seguir funcionando sin metadata.ip
// Enviar múltiples requests y verificar que se limitan correctamente
```

## ⚠️ Notas de Seguridad

### ¿Por qué este cambio?

1. **Prevención de IP Spoofing**: Los usuarios malintencionados podían falsificar su IP para:
   - Evadir rate limiting
   - Ocultar su ubicación real
   - Realizar ataques de múltiples IPs falsas

2. **Trusted Proxy Validation**: El backend ahora:
   - Solo confía en headers de proxies validados (Cloudflare, nginx, etc.)
   - Valida la cadena de proxies
   - Usa la IP real del cliente extraída de headers seguros

3. **Cumplimiento de Estándares**:
   - Sigue las mejores prácticas de OWASP
   - Compatible con infraestructuras modernas (CDN, load balancers)
   - Previene vulnerabilidades de seguridad comunes

### ¿Qué pasa si el frontend sigue enviando `metadata.ip`?

El backend **IGNORA** completamente el campo `metadata.ip`. No hay error, pero el valor es descartado y se usa la IP extraída de los headers HTTP validados.

## 🌐 Compatibilidad de Infraestructura

El backend ahora soporta automáticamente:

| Infraestructura | Header Usado | Configuración Backend |
|-----------------|--------------|----------------------|
| Cloudflare | `CF-Connecting-IP` | `USE_CLOUDFLARE=true` |
| nginx | `X-Real-IP` | `TRUSTED_PROXIES=<nginx_ip>` |
| AWS ALB | `X-Forwarded-For` | `TRUSTED_PROXIES=<vpc_cidr>` |
| Railway.app | `X-Envoy-External-Address` | `TRUSTED_PROXIES=*` |
| Conexión directa | `request.client.host` | `ENABLE_PROXY_HEADERS=false` |

## 📞 Soporte

Si tienes problemas después de la migración:

1. **Verificar logs del backend**: Buscar mensajes de "non-trusted proxy"
2. **Revisar configuración**: `.env` debe tener `ENABLE_PROXY_HEADERS=true`
3. **Contactar al equipo de backend**: Si rate limiting no funciona

## 📚 Referencias

- Documentación completa: `/docs/NOTAS_CLAUDE.md` (2025-11-07)
- Backend API: `/demo_agent/services/client_ip_service.py`
- Configuración: `/demo_agent/.env.example` (líneas 117-165)

---

**Versión**: 2.0.0
**Fecha**: 2025-11-07
**Status**: ✅ Requerido para producción
