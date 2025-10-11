# 🛡️ Fallback Strategy - Guía de Uso

**Fecha**: 2025-10-03
**Estado**: ✅ Integrada en ToolExecutor

---

## 📋 Descripción

La **FallbackStrategy** proporciona resiliencia automática al sistema, permitiendo que cuando una tool falla, se intente automáticamente con una tool alternativa configurada.

---

## ⚙️ Configuración

### Habilitar Fallback en `.env`

```bash
# Fallback Strategy
ENABLE_FALLBACK=true          # Activar fallback automático
FALLBACK_MAX_DEPTH=2          # Máximo 2 niveles de fallback
```

---

## 🎯 Uso Básico

### 1. Configurar Reglas de Fallback

En `odiseo_bot.py` después de inicializar `ToolExecutor`:

```python
async def initialize(self):
    # ... initialize ToolExecutor ...

    # Configure fallback rules
    if self.tool_executor and settings.ENABLE_FALLBACK:
        # Rule 1: search_products → fuzzy_search_smart
        self.tool_executor.add_fallback_rule(
            primary_tool="search_products",
            fallback_tool="fuzzy_search_smart",
            param_mapping={"query": "search_term"}
        )

        # Rule 2: fetch_by_sku → fetch_by_id
        self.tool_executor.add_fallback_rule(
            primary_tool="fetch_by_sku",
            fallback_tool="fetch_by_id",
            param_mapping={"sku": "product_id"}
        )
```

### 2. Ejecución Automática

Una vez configuradas las reglas, el fallback es **totalmente automático**:

```python
# User query: "Busco laptops gaming"
# Gemini calls: search_products(query="laptops gaming")

# Flujo automático:
# 1. Intenta search_products
#    ↓ Si falla...
# 2. Mapea parámetros: query → search_term
# 3. Intenta fuzzy_search_smart(search_term="laptops gaming")
#    ↓ Si falla...
# 4. Reporta error (max_depth alcanzado)
```

---

## 📊 Ejemplo Completo

### Escenario: search_products falla, fuzzy_search_smart funciona

```python
# User: "Busco laptop"
# Gemini: search_products(query="laptop")

# Log output:
# [WARNING] Tool 'search_products' failed: Connection timeout
#           Falling back to 'fuzzy_search_smart'
# [INFO]    Fallback successful: used 'fuzzy_search_smart' instead of 'search_products'
# [SUCCESS] Found 5 products via fallback
```

**Resultado**: Usuario **no nota el error**, recibe productos correctamente vía fallback.

---

## 🔧 Funciones Disponibles

### `add_fallback_rule()`

Agrega una regla de fallback.

```python
executor.add_fallback_rule(
    primary_tool="tool_principal",
    fallback_tool="tool_alternativo",
    param_mapping={"param_viejo": "param_nuevo"}  # Opcional
)
```

**Parámetros**:
- `primary_tool`: Tool que puede fallar
- `fallback_tool`: Tool alternativo a usar
- `param_mapping`: Mapeo de nombres de parámetros (opcional)

### `get_fallback_chain()`

Obtiene la cadena completa de fallbacks configurada.

```python
chain = executor.get_fallback_chain("search_products")
# Returns: ['search_products', 'fuzzy_search_smart']
```

---

## 📈 Ventajas

1. **Resiliencia**: Sistema continúa funcionando aunque falle una tool
2. **Transparencia**: Usuario no nota el error
3. **Automático**: No requiere cambios en código de negocio
4. **Configurable**: Fácil agregar/remover reglas
5. **Métricas**: Todos los intentos se registran

---

## 🔍 Logs de Fallback

### Fallback Exitoso
```
[WARNING] Tool 'search_products' failed: Timeout
          Falling back to 'fuzzy_search_smart'
[INFO]    Fallback successful: used 'fuzzy_search_smart' instead of 'search_products'
```

### Fallback Falla
```
[WARNING] Tool 'search_products' failed: Timeout
          Falling back to 'fuzzy_search_smart'
[ERROR]   Tool 'fuzzy_search_smart' failed and no fallback rules defined
[ERROR]   Maximum fallback depth (2) reached. Original tool: search_products
```

---

## ⚡ Performance

### Con Retry + Fallback

El sistema combina **Retry** y **Fallback** para máxima resiliencia:

```
1. Intenta search_products
   → Retry 1: Falla
   → Retry 2: Falla
   → Retry 3: Falla (max attempts)

2. Activa Fallback → fuzzy_search_smart
   → Retry 1: Éxito ✅

Total: 4 intentos automáticos
```

**Configuración recomendada**:
```bash
# Development (rápido)
RETRY_MAX_ATTEMPTS=2
FALLBACK_MAX_DEPTH=1

# Production (robusto)
RETRY_MAX_ATTEMPTS=3
FALLBACK_MAX_DEPTH=2
```

---

## 🎯 Casos de Uso

### 1. Búsqueda de Productos
```python
# Exact search fails → Fuzzy search
add_fallback_rule(
    "search_products",
    "fuzzy_search_smart",
    {"query": "search_term"}
)
```

### 2. Fetch por SKU
```python
# SKU not found → Try as product ID
add_fallback_rule(
    "fetch_by_sku",
    "fetch_by_id",
    {"sku": "product_id"}
)
```

### 3. Múltiples Niveles
```python
# search → fuzzy_search → all_products
add_fallback_rule("search_products", "fuzzy_search_smart")
add_fallback_rule("fuzzy_search_smart", "get_all_products")

# Chain: search_products → fuzzy_search_smart → get_all_products
```

---

## 🚫 Prevención de Loops

El sistema previene **loops infinitos** con:

1. **Max Depth**: Límite de niveles de fallback (default: 2)
2. **Detección de ciclos**: No permite `A → B → A`
3. **Flag interno**: `_use_fallback=False` en llamadas recursivas

---

## 📊 Métricas de Fallback

Los fallbacks se registran en métricas:

```python
stats = executor.get_stats("search_products")

# Output:
{
    "total_calls": 10,
    "successful_calls": 8,
    "failed_calls": 2,
    "fallback_used": 2,  # Veces que usó fallback
    "fallback_success": 2  # Fallbacks exitosos
}
```

---

## 🔗 Integración con Otras Mejoras

FallbackStrategy se combina con:

- ✅ **Retry**: Cada tool (primaria y fallback) usa retry
- ✅ **Validation**: Parámetros validados en ambas tools
- ✅ **Metrics**: Todos los intentos registrados
- ✅ **Cache**: Schemas cacheados para performance
- ✅ **Tracking**: User query asociado a todas las llamadas

---

## 🎓 Best Practices

1. **Configura fallbacks al inicio**: En `initialize()` o `__init__()`
2. **Mapea parámetros correctamente**: Verifica que los nombres coincidan
3. **No abuses de niveles**: Max 2-3 niveles de profundidad
4. **Monitorea métricas**: Revisa cuántos fallbacks ocurren
5. **Logging**: Mantén logs de fallbacks para debugging

---

## ✅ Checklist de Implementación

- [ ] Habilitar `ENABLE_FALLBACK=true` en `.env`
- [ ] Configurar `FALLBACK_MAX_DEPTH` apropiado
- [ ] Agregar reglas con `add_fallback_rule()` al inicio
- [ ] Verificar mapeo de parámetros entre tools
- [ ] Monitorear logs de fallback
- [ ] Revisar métricas periódicamente

---

## 📞 Troubleshooting

### Fallback no se activa
```python
# Verificar que esté habilitado
print(settings.ENABLE_FALLBACK)  # Debe ser True

# Verificar que hay reglas
print(executor.get_fallback_chain("tool_name"))  # No debe estar vacío
```

### Recursión infinita
```python
# No crear ciclos
add_fallback_rule("A", "B")
add_fallback_rule("B", "A")  # ❌ EVITAR ESTO
```

### Parámetros no coinciden
```python
# Verificar mapeo correcto
add_fallback_rule(
    "tool_A",
    "tool_B",
    param_mapping={
        "param_A": "param_B",  # Nombres exactos
        "limit": "max_results"
    }
)
```

---

**FallbackStrategy** - Resiliencia automática para Odiseo Bot 🛡️
