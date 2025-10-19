# 🚀 Quick Start - A/B Testing System

**5 minutos para entender y empezar a usar el sistema**

---

## ✅ Verificar que Todo Funciona (30 segundos)

```bash
cd /home/javort/Lab01-MCP/agent

# Ejecutar todos los tests (debe mostrar 15/15 PASSED)
python3 test_modular_sales_prompt.py && \
python3 test_ab_testing.py && \
python3 test_odiseo_prompt_integration.py

# Si ves "15/15 PASSED" → Sistema OK ✅
```

---

## 🎮 Ver Demos (2 minutos)

```bash
# Demo completa (4 escenarios)
python3 demo_ab_testing_e2e.py

# Demo interactiva (paso a paso)
python3 demo_interactive.py
```

---

## 🔧 Activar en Producción (3 pasos, 5 minutos)

### Paso 1: Editar Configuración
```bash
vim prompts/config/prompt_versions.yaml
```

Cambiar estas líneas:
```yaml
ab_testing:
  enabled: true  # ← Cambiar de false a true
  experiments:
    - name: sales_pagination_6_products
      enabled: true  # ← Cambiar de false a true
      traffic_split: 0.1  # ← 10% rollout inicial
```

### Paso 2: Modificar Código
```python
# Antes:
bot = OdiseoBot(debug_mode=False)

# Después:
bot = OdiseoBot(
    debug_mode=False,
    user_id=customer.email  # ← Agregar este parámetro
)
```

### Paso 3: Monitorear
```bash
# Ver decisiones de A/B testing en tiempo real
tail -f logs/app.log | grep "A/B test"

# Output esperado:
# [INFO] A/B test 'sales_pagination_6_products': user=maria@..., variant=B, version=v1.1, pagination=6
```

---

## 📊 Analizar Métricas (cuando tengas logs)

```bash
# Crear directorio de logs si no existe
mkdir -p logs

# Parser de métricas
python3 metrics_collector.py --log-file logs/app.log

# Exportar a CSV
python3 metrics_collector.py --log-file logs/app.log --export metrics.csv
```

---

## 🔄 Rollback (si algo sale mal)

```bash
vim prompts/config/prompt_versions.yaml
```

Cambiar:
```yaml
experiments:
  - name: sales_pagination_6_products
    enabled: false  # ← Deshabilitar experimento
```

Guardar → Rollback instantáneo (<1 segundo)

---

## 📚 Más Información

- **Quick Guide**: `cat README_AB_TESTING.md`
- **Resumen Ejecutivo**: `cat RESUMEN_EJECUTIVO.md`
- **Visual Summary**: `cat VISUAL_SUMMARY.md`
- **Historia Completa**: `cat ../docs/NOTAS_CLAUDE.md`

---

## 💡 Tips Rápidos

1. **Siempre** pasar `user_id` a OdiseoBot (email, customer_id, etc.)
2. **Comenzar** con `traffic_split: 0.1` (10% rollout gradual)
3. **Monitorear** logs diariamente durante experimentos
4. **Recolectar** métricas por mínimo 2 semanas
5. **Rollback** inmediatamente si problemas

---

## 🆘 Troubleshooting

**Problema**: Tests fallan
```bash
# Verificar paths
ls -la prompts/templates/sales_agent/
ls -la prompts/config/prompt_versions.yaml
```

**Problema**: A/B testing no funciona
```bash
# Verificar config
grep "enabled" prompts/config/prompt_versions.yaml

# Debe mostrar:
#   ab_testing:
#     enabled: true
#   experiments:
#     - name: sales_pagination_6_products
#       enabled: true
```

**Problema**: No veo logs
```bash
# Crear directorio
mkdir -p logs
touch logs/app.log

# Verificar que la app escribe ahí
tail -f logs/app.log
```

---

## 🎯 Próximos Pasos Recomendados

1. ✅ **Ahora**: Ejecutar demos y tests
2. 🚀 **Hoy**: Activar A/B testing con 10% traffic
3. 📊 **Esta semana**: Implementar tracking de conversion_rate
4. 📈 **Próximas 2 semanas**: Recolectar métricas
5. 🏆 **Después**: Declarar ganador y rollout 100%

---

**Sistema production-ready** - Creado 2025-10-11
**Tests**: 15/15 Passing (100%)
**Status**: ✅ Ready to Deploy
