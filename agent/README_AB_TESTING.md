# A/B Testing System - Quick Start Guide

Sistema completo de A/B testing para prompts modulares con deterministic bucketing, zero-downtime switching, y instant rollback.

## 📋 Características

- ✅ **Modular Prompts**: Jinja2 templates organizados por módulos
- ✅ **A/B Testing**: Experimentación con diferentes versiones de prompts
- ✅ **Deterministic Bucketing**: Mismo usuario → mismo variant (MD5 hash)
- ✅ **Zero-Downtime Switching**: Cambios instantáneos vía YAML
- ✅ **Instant Rollback**: <1 segundo para revertir cambios
- ✅ **Self-Hosted**: Sin dependencias externas
- ✅ **Cost-Free**: $0/mes (vs LaunchDarkly $$)

## 🚀 Quick Start

### 1. Verificar instalación

```bash
# Desde /home/javort/Lab01-MCP/agent/

# Ejecutar tests (debe mostrar 15/15 passed)
python3 test_modular_sales_prompt.py
python3 test_ab_testing.py
python3 test_odiseo_prompt_integration.py

# Ejecutar demo
python3 demo_ab_testing_e2e.py
```

### 2. Habilitar A/B Testing (Producción)

**Editar: `prompts/config/prompt_versions.yaml`**

```yaml
ab_testing:
  enabled: true  # ← Cambiar de false a true

  experiments:
    - name: sales_pagination_6_products
      enabled: true  # ← Activar experimento
      traffic_split: 0.1  # ← 10% tráfico a variant B (gradual rollout)
```

**Guardar el archivo** → Cambios aplicados instantáneamente (sin restart)

### 3. Usar en código

```python
from core.odiseo_bot import OdiseoBot

# Crear bot con user_id (para A/B testing deterministic)
bot = OdiseoBot(
    debug_mode=False,
    user_id=customer.email  # ← Email del cliente (o cualquier ID único)
)
await bot.initialize()

# Enviar mensaje (A/B testing automático)
response = await bot.send_message("Busco una laptop gaming")

# El sistema automáticamente:
# 1. Hash del user_id → determina variant A o B
# 2. Carga el prompt correspondiente (4 o 6 productos)
# 3. Genera respuesta personalizada
```

### 4. Monitorear logs

```bash
# Los logs mostrarán decisiones de A/B testing:
[INFO] A/B test 'sales_pagination_6_products': user=maria@example.com, variant=B, version=v1.1, pagination=6
[SUCCESS] ✅ Using modular prompt system (25087 chars, user_id=maria@ex...)
```

## 📊 Rollout Gradual Recomendado

```yaml
# Semana 1: 10% tráfico a variant B
traffic_split: 0.1

# Semana 2: Incrementar a 30% (si métricas OK)
traffic_split: 0.3

# Semana 3: Full A/B test (50/50)
traffic_split: 0.5

# Semana 4: Declarar ganador y rollout 100%
active_versions:
  sales: v1.1  # ← Si variant B gana
```

## 🔄 Rollback Instantáneo

Si variant B tiene problemas:

```yaml
# Editar prompt_versions.yaml:
experiments:
  - name: sales_pagination_6_products
    enabled: false  # ← Deshabilitar experimento

# Guardar → TODOS los usuarios vuelven a variant A (<1 segundo)
```

## 📈 Métricas a Monitorear

### KPIs Primarios
- **Conversion Rate**: % de usuarios que agregan productos al carrito
- **Time to Decision**: Tiempo promedio hasta selección de producto

### KPIs Secundarios
- **User Satisfaction**: Feedback explícito del usuario
- **Pagination Click Rate**: % de clics en "mostrar más"

### Parsing de Logs

```bash
# Contar usuarios por variant
grep "A/B test 'sales_pagination_6_products'" logs/app.log | grep "variant=A" | wc -l
grep "A/B test 'sales_pagination_6_products'" logs/app.log | grep "variant=B" | wc -l

# Ver distribución por día
grep "A/B test" logs/app.log | awk '{print $1, $2, $NF}' | sort | uniq -c
```

## 🏗️ Arquitectura

```
User Request (user_id="maria@example.com")
    ↓
OdiseoBot.__init__(user_id="maria@...")
    ↓
_build_system_prompt()
    ↓
PromptManager.get_sales_prompt(user_id="maria@...")
    ↓
_select_ab_test_version(agent='sales', user_id="maria@...")
    ↓
MD5("maria@example.com") → hash → 0-100 bucket → Variant B
    ↓
Load version v1.1 with pagination_page_size=6
    ↓
Render sales_agent.jinja2 template (25,087 chars)
    ↓
Return prompt to Gemini
    ↓
Generate response with 6 products/page
```

## 📁 Estructura de Archivos

```
Lab01-MCP/
├── prompts/
│   ├── templates/
│   │   └── sales_agent/
│   │       ├── sales_agent.jinja2      # Master template
│   │       ├── base.jinja2             # Identity & capabilities
│   │       └── modules/
│   │           ├── display_rules.jinja2  # Pagination rules
│   │           ├── examples.jinja2       # Example conversations
│   │           └── ...
│   └── config/
│       └── prompt_versions.yaml        # A/B testing config
├── agent/
│   ├── src/multi_agent/
│   │   └── prompt_manager.py          # PromptManager class
│   ├── test_modular_sales_prompt.py   # Tests (3/3)
│   ├── test_ab_testing.py             # Tests (5/5)
│   ├── test_odiseo_prompt_integration.py  # Tests (7/7)
│   └── demo_ab_testing_e2e.py         # Demo completa
└── client_mcp/
    └── core/
        └── odiseo_bot.py              # OdiseoBot integrado
```

## 🧪 Tests

```bash
# Test 1: Modular prompts (3/3 tests)
python3 test_modular_sales_prompt.py

# Test 2: A/B testing infrastructure (5/5 tests)
python3 test_ab_testing.py

# Test 3: OdiseoBot integration (7/7 tests)
python3 test_odiseo_prompt_integration.py

# Demo: End-to-end workflow
python3 demo_ab_testing_e2e.py
```

**Total: 15/15 tests passing (100%)**

## 🎯 Experimentos Disponibles

### sales_pagination_6_products (Activo)

**Hipótesis**: 6 productos reducen decision fatigue vs 4 productos

**Configuración**:
- **Variant A (Control)**: v1.0, 4 productos/página
- **Variant B (Test)**: v1.1, 6 productos/página
- **Traffic Split**: 50% (configurable)

**Métricas**:
- `conversion_rate`: % usuarios que agregan al carrito
- `time_to_decision`: Tiempo promedio a selección
- `user_satisfaction`: Feedback explícito
- `pagination_clicks`: Rate de clics "mostrar más"

**Success Criteria**:
- Variant B `conversion_rate` > Variant A + 5%
- Variant B `user_satisfaction` >= Variant A

## 🔧 Troubleshooting

### Problema: A/B testing no funciona

**Verificar**:
1. `ab_testing.enabled: true` en `prompt_versions.yaml`
2. Experimento `enabled: true`
3. `user_id` se está pasando a OdiseoBot
4. Logs muestran decisiones de A/B test

**Debug**:
```python
# Verificar bucketing manualmente
from multi_agent.prompt_manager import PromptManager

manager = PromptManager(use_templates=True)
version, pagination = manager._select_ab_test_version(
    agent='sales',
    user_id='test@example.com'
)
print(f"Version: {version}, Pagination: {pagination}")
```

### Problema: Imports fallan

**Solución**: Verificar paths en `sys.path`:
```python
import sys
from pathlib import Path
agent_src = Path(__file__).parent / "agent" / "src"
sys.path.insert(0, str(agent_src))
```

### Problema: Templates no se encuentran

**Verificar**:
```bash
ls -la prompts/templates/sales_agent/
# Debe mostrar sales_agent.jinja2, base.jinja2, modules/
```

## 📚 Documentación Completa

- **Implementación**: `docs/NOTAS_CLAUDE.md` (secciones Fase A, B, C)
- **Tests**: Archivos `test_*.py` con ejemplos de uso
- **Demo**: `demo_ab_testing_e2e.py` con 4 escenarios

## 🎓 Best Practices

1. **Siempre** pasar `user_id` a OdiseoBot para deterministic bucketing
2. **Comenzar** con `traffic_split: 0.1` (10%) para rollout gradual
3. **Monitorear** logs diariamente durante experimentos
4. **Recolectar** métricas por mínimo 2 semanas (significancia estadística)
5. **Rollback** inmediatamente si métricas caen >5%
6. **Documentar** resultados en `docs/NOTAS_CLAUDE.md`

## 🚨 Production Checklist

Antes de activar A/B testing en producción:

- [ ] Tests pasando (15/15)
- [ ] Demo ejecutada exitosamente
- [ ] `user_id` implementado en código de producción
- [ ] Sistema de logs configurado
- [ ] Dashboard de métricas preparado
- [ ] Plan de rollback documentado
- [ ] Team notificado del experimento
- [ ] Success criteria definidos
- [ ] Timeline establecido (2+ semanas)

## 💡 Tips

- **User IDs estables**: Usar email, customer_id, o UUID persistente
- **No usar session_id**: Cambia en cada sesión (rompe determinismo)
- **Monitor frecuentemente**: Primeras 48h son críticas
- **No multiple experimentos**: 1 experimento a la vez por agente
- **Document everything**: Logs, métricas, decisiones

## 📞 Soporte

Para preguntas o problemas:
1. Revisar `docs/NOTAS_CLAUDE.md`
2. Ejecutar tests para verificar funcionamiento
3. Revisar logs de A/B testing
4. Verificar configuración en `prompt_versions.yaml`

---

**Sistema production-ready** 🎉

Desarrollado: 2025-10-11
Versión: 1.0.0
Tests: 15/15 passing (100%)
Status: ✅ Production Ready
