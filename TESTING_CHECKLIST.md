# Testing Checklist - Telegram Bot + Gemini Language Detection

**Objetivo:** Verificar que el bot Telegram responde correctamente en el idioma del usuario y sin empty responses.

**Fecha:** 2025-11-11  
**Estado:** ⏳ Pendiente de Testing (Bot necesita reinicio)

---

## Pre-Requisitos

- [ ] Bot Telegram reiniciado con últimos cambios
- [ ] Verificar logs muestran: `✅ LanguageDetectorService initialized`
- [ ] Variables de entorno configuradas (`TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`)

---

## Test Suite 1: Detección de Idioma (Casos que Fallaban)

### Test 1.1: "proximo martes" (Español)
```
Input:     "proximo martes"
Expected:  Detección: "es", Ruta: Booking Agent
Success:   [ ]
Notes:     ________________________________
```

### Test 1.2: "quiero una laptop" (Español)
```
Input:     "quiero una laptop"
Expected:  Detección: "es", Ruta: Sales Agent (NO General)
Success:   [ ]
Notes:     ________________________________
```

### Test 1.3: "next tuesday" (English)
```
Input:     "next tuesday"
Expected:  Detección: "en", Ruta: Booking Agent
Success:   [ ]
Notes:     ________________________________
```

### Test 1.4: "I want a laptop" (English)
```
Input:     "I want a laptop"
Expected:  Detección: "en", Ruta: Sales Agent
Success:   [ ]
Notes:     ________________________________
```

---

## Test Suite 2: Conversación Multi-Turn (Session Language)

### Test 2.1: Conversación en Español
```
Message 1: "hola"
Expected:  Detección con Gemini → "es"
Success:   [ ]

Message 2: "proximo martes"
Expected:  Usa session_language → "es" (sin API call)
Success:   [ ]

Message 3: "a las 3pm"
Expected:  Usa session_language → "es" (sin API call)
Success:   [ ]

Notes:     ________________________________
```

### Test 2.2: Conversación en Inglés
```
Message 1: "hello"
Expected:  Detección con Gemini → "en"
Success:   [ ]

Message 2: "next tuesday"
Expected:  Usa session_language → "en" (sin API call)
Success:   [ ]

Message 3: "at 3pm"
Expected:  Usa session_language → "en" (sin API call)
Success:   [ ]

Notes:     ________________________________
```

---

## Test Suite 3: Edge Cases

### Test 3.1: Entrada Ambigua con Session
```
Message 1: "hola"
Expected:  Detección → "es"
Success:   [ ]

Message 2: "18"
Expected:  Usa session_language → "es" (fallback)
Success:   [ ]

Notes:     ________________________________
```

### Test 3.2: Entrada Muy Corta
```
Input:     "ok"
Expected:  Fallback a session o "es"
Success:   [ ]
Notes:     ________________________________
```

### Test 3.3: Mezcla de Idiomas (Code-switching)
```
Input:     "quiero un MacBook Pro"
Expected:  Detección → "es"
Success:   [ ]
Notes:     ________________________________
```

---

## Test Suite 4: Performance y Rate Limiting

### Test 4.1: Múltiples Mensajes Rápidos
```
Enviar 10 mensajes seguidos en mismo chat:
1. "hola"
2. "productos"
3. "laptops"
4. "gaming"
5. "presupuesto"
6. "envio"
7. "garantia"
8. "stock"
9. "colores"
10. "gracias"

Expected:  
- Solo mensaje 1 llama Gemini API
- Mensajes 2-10 usan session_language
- Sin empty responses
- Sin rate limiting errors

Success:   [ ]
Notes:     ________________________________
```

### Test 4.2: Cache Hit Rate
```
Enviar mismo mensaje 2 veces en diferentes chats:

Chat A: "proximo martes"
Chat B: "proximo martes"

Expected:  
- Chat A: API call (cache miss)
- Chat B: Cache hit (sin API call)

Success:   [ ]
Notes:     ________________________________
```

---

## Test Suite 5: Error Handling

### Test 5.1: Gemini API Falla
```
Simular fallo de API (ej: desconectar internet brevemente)

Input:     "test message"
Expected:  Fallback a "es", sin crash, respuesta en español

Success:   [ ]
Notes:     ________________________________
```

### Test 5.2: Input Vacío
```
Input:     ""
Expected:  Manejo graceful, default a "es"

Success:   [ ]
Notes:     ________________________________
```

---

## Logs Esperados (Success Criteria)

### ✅ Logs Exitosos
```
✅ LanguageDetectorService initialized with model: gemini-2.5-flash
✅ AgentRouter initialized (Gemini-based language detection)
🌐 Language detected: es for 'proximo martes'
Using session language: es
🎯 Intent classification: booking (es)
📊 Cache hit for 'proximo martes...' → es
```

### ❌ Logs de Error (NO deberían aparecer)
```
❌ Language detection failed
Empty response from Gemini
'NoneType' object is not subscriptable
RuntimeError: Empty response from Gemini API
```

---

## Verificación de Métricas

### API Calls
- [ ] Primer mensaje de cada sesión: 1 API call
- [ ] Mensajes subsecuentes: 0 API calls
- [ ] Reducción total: ~99%

### Latency
- [ ] Primer mensaje (cold): 200-300ms
- [ ] Mensajes cached: <1ms
- [ ] Session-based: <1ms

### Accuracy
- [ ] "proximo martes" → "es" ✅
- [ ] "next tuesday" → "en" ✅
- [ ] Consistency en conversación ✅

---

## Comandos de Troubleshooting

### Ver Logs en Tiempo Real
```bash
# En terminal donde corre el bot
# Logs deberían mostrar cada mensaje procesado
```

### Verificar Proceso del Bot
```bash
ps aux | grep main_telegram.py
```

### Verificar Variables de Entorno
```bash
echo $TELEGRAM_BOT_TOKEN
echo $GOOGLE_API_KEY
```

### Cache Stats (si necesitas debug)
```python
# Agregar temporalmente en agent_router.py
stats = self.language_detector.get_cache_stats()
logger.info(f"Cache stats: {stats}")
```

---

## Criterios de Éxito

**PASS:** Todos los tests de Suite 1-5 pasan ✅

**CONDITIONAL PASS:** 90% de tests pasan, fallas menores documentadas

**FAIL:** Cualquiera de estos ocurre:
- [ ] "proximo martes" detectado como "en"
- [ ] Empty responses de Gemini
- [ ] Bot crash o no responde
- [ ] Rate limiting errors
- [ ] NoneType errors en logs

---

## Resultados

**Fecha de Testing:** _______________  
**Tester:** _______________  

**Tests Pasados:** _____ / _____  
**Success Rate:** _____% 

**Issues Encontrados:**
1. ________________________________
2. ________________________________
3. ________________________________

**Notas Adicionales:**
________________________________
________________________________
________________________________

---

## Próximos Pasos Si PASS

1. [ ] Marcar como Production Ready
2. [ ] Documentar en README
3. [ ] Considerar migración de archivos restantes (base_agent, booking_agent, sales_agent)
4. [ ] Monitorear en producción por 48 horas

## Próximos Pasos Si FAIL

1. [ ] Documentar fallas en detalle
2. [ ] Revisar logs completos
3. [ ] Contactar para debugging adicional
4. [ ] Considerar rollback si crítico

---

**Documento creado:** 2025-11-11  
**Última actualización:** 2025-11-11  
**Referencia:** `docs/TELEGRAM_STATUS.md`
