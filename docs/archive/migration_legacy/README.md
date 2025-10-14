# Archivo: Documentación de Migración Legacy (OdiseoBot → OdiseoBotV2)

**Fecha de Archivo:** 2025-10-13
**Razón:** Variable `USE_ODISEO_V2` obsoleta y eliminada del código

---

## 📚 Contenido de este Archivo

Esta carpeta contiene documentación histórica de la migración de **OdiseoBot (Legacy)** a **OdiseoBotV2 (BaseAgent)** realizada durante octubre 2025.

### Documentos Archivados

| Archivo | Descripción | Fecha Original |
|---------|-------------|----------------|
| `MIGRATION_ODISEOBOT_V2.md` | Guía de migración completa | 2025-10-11 |
| `LEGACY_ELIMINATION_ANALYSIS.md` | Análisis de eliminación de legacy | 2025-10-11 |
| `LEGACY_ELIMINATION_PLAN.md` | Plan de eliminación de legacy | 2025-10-11 |
| `WEEK_5_DEPRECATION_MONITORING.md` | Monitoreo de deprecación | 2025-10-12 |
| `ODISEOBOT_V2_PRODUCTION_CHECKLIST.md` | Checklist de producción | 2025-10-11 |
| `ROLLBACK_STRATEGY.md` | Estrategia de rollback | 2025-10-11 |
| `VALIDATION_REPORT.md` | Reporte de validación | 2025-10-11 |
| `SESSION_SUMMARY_2025_10_12.md` | Resumen de sesión | 2025-10-12 |

---

## ⚠️ Información Importante

### Variable Obsoleta: `USE_ODISEO_V2`

Esta documentación hace referencia extensa a la variable de entorno `USE_ODISEO_V2`, la cual **ya no existe en el código actual**.

**Cronología:**
- **2025-10-10**: Solo existía OdiseoBot (Legacy) monolítico
- **2025-10-11**: Se introdujo `USE_ODISEO_V2` para migración gradual
  - `USE_ODISEO_V2=false` → OdiseoBot (Legacy)
  - `USE_ODISEO_V2=true` → OdiseoBotV2 (BaseAgent)
- **2025-10-12**: Se eliminó Legacy y `USE_ODISEO_V2`, se introdujo sistema multi-agent
- **2025-10-13**: Esta documentación se archivó por obsolescencia

---

## 🔄 Configuración Actual del Sistema

### Variable Activa: `ENABLE_AGENT_ROUTING`

El sistema actual usa `ENABLE_AGENT_ROUTING` para controlar el modo de operación:

```bash
# Ubicación
client_mcp/config/settings.py:300

# Valores
ENABLE_AGENT_ROUTING=false  # Single-agent mode (SalesAgent only)
ENABLE_AGENT_ROUTING=true   # Multi-agent mode (Router + 3 specialized agents)
```

### Arquitectura Actual (2025-10-13)

```
AgentOrchestrator
    │
    ├─> ENABLE_AGENT_ROUTING=false
    │   └─> SalesAgent (productos solamente)
    │
    └─> ENABLE_AGENT_ROUTING=true
        ├─> AgentRouter (clasificación de intención)
        ├─> SalesAgent (productos)
        ├─> BookingAgent (reservas)
        └─> GeneralAgent (información general)
```

**Documentación actualizada**: Consultar `/docs/` y `/agent/docs/` (excluir esta carpeta archive)

---

## 📖 Propósito de este Archivo

Esta documentación se preserva **únicamente para referencia histórica**:

1. **Entender decisiones técnicas pasadas**
2. **Troubleshooting de issues relacionados con migración**
3. **Aprendizaje de patrones de migración gradual**
4. **Auditoría de cambios arquitectónicos**

---

## ⚡ Para Desarrolladores Nuevos

**Si encontraste esta carpeta buscando información sobre cómo configurar el sistema:**

1. ❌ **NO uses esta documentación** - está desactualizada
2. ✅ **Lee la documentación actual** en `/docs/` y `/agent/docs/`
3. ✅ **Variable correcta**: `ENABLE_AGENT_ROUTING` (no USE_ODISEO_V2)
4. ✅ **Guía de configuración**: `/docs/MEMORY_ACTIVATION_GUIDE.md` y `README.md`

---

## 📎 Enlaces Útiles

- **Plan de eliminación**: `../USE_ODISEO_V2_ELIMINATION_PLAN.md`
- **Settings actual**: `../../client_mcp/config/settings.py`
- **Orchestrator actual**: `../../client_mcp/core/agent_orchestrator.py`
- **Documentación activa**: `../../docs/` y `../../agent/docs/`

---

**Archivado por**: Claude Code
**Fecha**: 2025-10-13
**Razón**: Obsolescencia de variable USE_ODISEO_V2
