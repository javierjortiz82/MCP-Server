# 📖 Ejemplos de Uso - Odiseo Bot

**SDK**: google-genai 1.41.0
**Estado**: Production Ready

Este documento proporciona ejemplos prácticos de uso del bot de ventas Odiseo con las mejores prácticas implementadas.

---

## 🚀 Inicio Rápido

### 1. Inicialización Básica

```python
import asyncio
from client_mcp.core.odiseo_bot import OdiseoBot

async def main():
    # Crear instancia del bot
    bot = OdiseoBot()

    # Inicializar (conecta a MCP, descubre tools, configura modelo)
    await bot.initialize()

    # Enviar mensaje
    response = await bot.send_message("Busco una laptop para gaming")
    print(response)

    # Cerrar conexiones
    await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Con Context Manager (Recomendado)

```python
import asyncio
from client_mcp.core.odiseo_bot import OdiseoBot

async def main():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Primera consulta
        response = await bot.send_message("¿Qué laptops tienen?")
        print(response)

        # Seguimiento en la misma conversación
        response = await bot.send_message("¿Cuál es la más económica?")
        print(response)

asyncio.run(main())
```

---

## 💡 Ejemplos por Caso de Uso

### Caso 1: Búsqueda de Productos

```python
async def ejemplo_busqueda():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Búsqueda simple
        response = await bot.send_message(
            "Busco laptops con 16GB de RAM"
        )
        print(response)

        # El bot automáticamente:
        # 1. Infiere que debe usar search_products
        # 2. Extrae parámetros: query="16GB RAM", limit=5
        # 3. Ejecuta la búsqueda
        # 4. Presenta resultados de forma natural
```

**Ejemplo de respuesta:**

```
He encontrado 3 laptops con 16GB de RAM:

1. **Gaming Laptop Pro** - $1,299.99
   - CPU: Intel i7 11800H
   - RAM: 16GB DDR4
   - Almacenamiento: 512GB SSD

2. **Business Ultrabook** - $1,099.99
   - CPU: Intel i7 1165G7
   - RAM: 16GB LPDDR4X
   - Almacenamiento: 1TB SSD

3. **Workstation Elite** - $1,899.99
   - CPU: AMD Ryzen 9 5900HX
   - RAM: 16GB DDR4
   - Almacenamiento: 1TB NVMe

¿Te gustaría conocer más detalles de alguna?
```

---

### Caso 2: Consulta de Detalles

```python
async def ejemplo_detalles():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Solicitar detalles de un producto específico
        response = await bot.send_message(
            "Dame más información sobre el producto LAPTOP001"
        )
        print(response)

        # El bot automáticamente:
        # 1. Detecta que necesita get_product_details
        # 2. Extrae product_id="LAPTOP001"
        # 3. Obtiene información detallada
        # 4. Presenta de forma estructurada
```

---

### Caso 3: Verificación de Inventario

```python
async def ejemplo_inventario():
    async with OdiseoBot() as bot:
        await bot.initialize()

        response = await bot.send_message(
            "¿Tienen disponible la laptop LAPTOP001 en la tienda de Quito?"
        )
        print(response)

        # El bot automáticamente:
        # 1. Usa check_inventory
        # 2. Parámetros: product_id="LAPTOP001", location="Quito"
        # 3. Verifica stock
        # 4. Informa disponibilidad
```

---

### Caso 4: Conversación Multi-Turn

```python
async def ejemplo_conversacion():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Turn 1: Búsqueda inicial
        r1 = await bot.send_message("Necesito una laptop para diseño gráfico")
        print(f"Bot: {r1}\n")

        # Turn 2: Refinamiento
        r2 = await bot.send_message("Prefiero una con GPU dedicada")
        print(f"Bot: {r2}\n")

        # Turn 3: Precio
        r3 = await bot.send_message("¿Cuál cuesta menos de $1000?")
        print(f"Bot: {r3}\n")

        # Turn 4: Detalles
        r4 = await bot.send_message("Dame detalles de la segunda opción")
        print(f"Bot: {r4}\n")

        # El historial se mantiene automáticamente
        # El bot entiende el contexto de toda la conversación
```

---

## 🔧 Configuración Avanzada

### Personalizar Parámetros del Modelo

```python
from client_mcp.config.settings import settings

# Ajustar temperatura para respuestas más creativas
settings.TEMPERATURE = 0.5  # Default: 0.2

# Ajustar max tokens para respuestas más largas
settings.MAX_OUTPUT_TOKENS = 1024  # Default: 512

# Cambiar modelo
settings.MODEL = "gemini-2.0-flash-exp-001"
```

### Modo Debug

```python
async def ejemplo_debug():
    # Activar modo debug
    bot = OdiseoBot(debug_mode=True)

    async with bot:
        await bot.initialize()

        # Verás logs detallados de:
        # - Function calls ejecutados
        # - Parámetros enviados
        # - Respuestas de tools
        # - Tiempo de ejecución

        response = await bot.send_message("Busco laptops gaming")
        print(response)
```

---

## 📊 Manejo de Respuestas

### Respuestas Directas (Sin Function Calling)

```python
async def ejemplo_respuesta_directa():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Pregunta general que no requiere tools
        response = await bot.send_message(
            "¿Qué diferencia hay entre RAM DDR4 y DDR5?"
        )

        # El bot responde directamente con su conocimiento
        print(response)
```

### Respuestas con Function Calling

```python
async def ejemplo_function_calling():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Pregunta que requiere datos en tiempo real
        response = await bot.send_message(
            "¿Cuántas laptops Asus tienen en stock?"
        )

        # Flujo interno:
        # 1. Bot decide usar search_products con query="Asus"
        # 2. Ejecuta función y obtiene resultados
        # 3. Procesa respuesta estructurada (JSON preservado)
        # 4. Genera respuesta natural

        print(response)
```

---

## 🛠️ Casos de Uso Especiales

### 1. Manejo de Errores

```python
async def ejemplo_manejo_errores():
    async with OdiseoBot() as bot:
        await bot.initialize()

        try:
            response = await bot.send_message("busco producto XYZ999")
            print(response)
        except Exception as e:
            print(f"Error: {e}")

        # El bot maneja automáticamente:
        # - Tools que fallan (retry con backoff)
        # - Fallback a tools alternativos
        # - Respuestas elegantes cuando no hay resultados
```

### 2. Búsquedas con Errores Tipográficos

```python
async def ejemplo_fuzzy_search():
    async with OdiseoBot() as bot:
        await bot.initialize()

        # Búsqueda con typo
        response = await bot.send_message(
            "Busco laptpo gmaing"  # typo: "laptpo gmaing"
        )

        # El bot usa fuzzy_search_smart automáticamente
        # que tolera errores de tipeo
        print(response)
        # Encuentra: "laptop gaming"
```

### 3. Filtrado por Categorías

```python
async def ejemplo_categorias():
    async with OdiseoBot() as bot:
        await bot.initialize()

        response = await bot.send_message(
            "Muéstrame solo tablets con más de 10 pulgadas"
        )

        # El bot infiere:
        # - category="tablets"
        # - Extrae criterio: "más de 10 pulgadas"
        # - Filtra resultados apropiadamente

        print(response)
```

---

## 📈 Monitoreo y Métricas

### Acceder a Métricas de la Conversación

```python
async def ejemplo_metricas():
    bot = OdiseoBot()
    await bot.initialize()

    # Enviar varios mensajes
    await bot.send_message("Busco laptops")
    await bot.send_message("¿Cuál es la más barata?")
    await bot.send_message("Dame detalles de esa")

    # Acceder a historial
    print(f"Mensajes en historial: {len(bot.conversation_history)}")

    # Verificar tools disponibles
    print(f"Tools autodescubiertos: {len(bot.mcp_tools)}")
    for tool in bot.mcp_tools:
        print(f"  - {tool.name}: {tool.description}")

    await bot.cleanup()
```

---

## 🎯 Mejores Prácticas

### ✅ DO

```python
# ✅ Usar context manager
async with OdiseoBot() as bot:
    await bot.initialize()
    response = await bot.send_message("...")

# ✅ Manejar excepciones
try:
    response = await bot.send_message("...")
except Exception as e:
    logger.error(f"Error: {e}")

# ✅ Reusar la misma instancia para conversaciones
bot = OdiseoBot()
await bot.initialize()
await bot.send_message("Hola")
await bot.send_message("Dame más info")  # Mantiene contexto

# ✅ Limpiar recursos
await bot.cleanup()
```

### ❌ DON'T

```python
# ❌ No crear nueva instancia por mensaje (pierde contexto)
for msg in messages:
    bot = OdiseoBot()
    await bot.initialize()
    await bot.send_message(msg)  # Cada uno sin contexto previo

# ❌ No olvidar cleanup
bot = OdiseoBot()
await bot.initialize()
await bot.send_message("...")
# Falta: await bot.cleanup()

# ❌ No hardcodear tool names
# El bot infiere automáticamente qué tool usar
```

---

## 🔍 Debugging Avanzado

### Ver Function Calls en Tiempo Real

```python
async def ejemplo_debug_avanzado():
    bot = OdiseoBot(debug_mode=True)

    # Monitorear logs
    import logging
    logging.basicConfig(level=logging.DEBUG)

    async with bot:
        await bot.initialize()

        # Los logs mostrarán:
        # - "🔧 Function call: search_products"
        # - "📥 Parámetros: {query: 'laptop', limit: 5}"
        # - "📤 Resultado: {items: [...], count: 3}"
        # - "⏱️  Execution time: 234ms"

        response = await bot.send_message("Busco laptop")
        print(response)
```

### Inspeccionar Historial de Conversación

```python
async def ejemplo_inspeccionar_historial():
    bot = OdiseoBot()
    await bot.initialize()

    await bot.send_message("Hola")
    await bot.send_message("Busco laptop")

    # Inspeccionar historial
    for i, content in enumerate(bot.conversation_history):
        print(f"\nTurn {i}:")
        print(f"  Role: {content.role}")
        print(f"  Parts: {len(content.parts)}")

        for part in content.parts:
            if part.text:
                print(f"  Text: {part.text[:100]}...")
            elif part.function_call:
                print(f"  Function: {part.function_call.name}")
            elif part.function_response:
                print(f"  Response: {part.function_response.name}")

    await bot.cleanup()
```

---

## 📚 Recursos Adicionales

### Archivos de Configuración

- **`.env`**: Variables de entorno (API keys, MCP server config)
- **`prompts/system_prompt.txt`**: System prompt base
- **`prompts/tools_template.txt`**: Template para instrucciones de tools

### Scripts de Validación

```bash
# Validar implementación profesional
python scripts/test_professional_implementation.py

# Validar tipos
python scripts/test_type_structure.py

# Validar inicialización
python scripts/test_bot_initialization.py

# Validar integración completa
python scripts/test_full_integration.py
```

### Documentación

- `PROFESSIONAL_AUDIT_REPORT.md` - Análisis técnico detallado
- `MIGRATION_SUMMARY.md` - Guía de migración de SDK
- `IMPLEMENTATION_COMPLETE.md` - Resumen de implementación
- `USAGE_EXAMPLES.md` - Este documento

---

## 🎓 Ejemplos Completos

### Ejemplo Completo: Sistema de Recomendación

```python
import asyncio
from client_mcp.core.odiseo_bot import OdiseoBot

async def sistema_recomendacion():
    """Sistema completo de recomendación de laptops."""

    async with OdiseoBot() as bot:
        await bot.initialize()

        print("🤖 Asistente de Ventas Activo\n")

        # Paso 1: Entender necesidades
        necesidades = await bot.send_message(
            "Necesito una laptop para edición de video profesional, "
            "presupuesto de $1500"
        )
        print(f"Bot: {necesidades}\n")

        # Paso 2: Consultar specs específicas
        specs = await bot.send_message(
            "¿Cuál tiene la mejor GPU?"
        )
        print(f"Bot: {specs}\n")

        # Paso 3: Verificar disponibilidad
        disponibilidad = await bot.send_message(
            "¿Está disponible en Quito?"
        )
        print(f"Bot: {disponibilidad}\n")

        # Paso 4: Cerrar venta
        cierre = await bot.send_message(
            "Me interesa, ¿cuáles son las opciones de pago?"
        )
        print(f"Bot: {cierre}\n")

if __name__ == "__main__":
    asyncio.run(sistema_recomendacion())
```

---

**Última actualización**: 2025-10-03
**Versión**: 1.0.0
**SDK**: google-genai 1.41.0
