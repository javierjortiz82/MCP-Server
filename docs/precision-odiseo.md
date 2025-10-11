# 📊 Reporte de Precisión: Odiseo Bot

**Fecha de Ejecución**: 2025-10-03 15:41:59
**Total de Casos Evaluados**: 50
**Versión**: Post-mejoras de documentación de tools

---

## 🎯 Resumen Ejecutivo

| Métrica | Valor | Porcentaje |
|---------|-------|------------|
| **Productos Encontrados** | 46/50 | **92.0%** |
| **Tool Correcto Usado** | 43/50 | **86.0%** |
| **Calidad Promedio de Respuesta** | 84.6/100 | **85%** |
| **Tiempo Promedio de Respuesta** | 3835ms | - |
| **Tiempo Promedio de Tool** | 179.8ms | - |

---

## 📈 Análisis por Categoría de Test

### Ambiguous Implicit Need
- Tests: 4
- Encontrados: 4/4 (100%)
- Tool correcto: 3/4 (75%)

### Ambiguous Location
- Tests: 1
- Encontrados: 1/1 (100%)
- Tool correcto: 0/1 (0%)

### Ambiguous Open Ended
- Tests: 1
- Encontrados: 1/1 (100%)
- Tool correcto: 1/1 (100%)

### Ambiguous Product Vs Need
- Tests: 2
- Encontrados: 2/2 (100%)
- Tool correcto: 2/2 (100%)

### Category Colloquial
- Tests: 3
- Encontrados: 2/3 (67%)
- Tool correcto: 3/3 (100%)

### Category Simple
- Tests: 5
- Encontrados: 5/5 (100%)
- Tool correcto: 5/5 (100%)

### Fuzzy Clean
- Tests: 7
- Encontrados: 7/7 (100%)
- Tool correcto: 5/7 (71%)

### Fuzzy Typo
- Tests: 3
- Encontrados: 3/3 (100%)
- Tool correcto: 3/3 (100%)

### Not Exists Absurd
- Tests: 1
- Encontrados: 0/1 (0%)
- Tool correcto: 1/1 (100%)

### Not Exists Brand Specific
- Tests: 2
- Encontrados: 2/2 (100%)
- Tool correcto: 0/2 (0%)

### Not Exists Sku
- Tests: 1
- Encontrados: 0/1 (0%)
- Tool correcto: 1/1 (100%)

### Not Exists Specific
- Tests: 2
- Encontrados: 1/2 (50%)
- Tool correcto: 1/2 (50%)

### Semantic Benefit
- Tests: 10
- Encontrados: 10/10 (100%)
- Tool correcto: 10/10 (100%)

### Sku Exact
- Tests: 8
- Encontrados: 8/8 (100%)
- Tool correcto: 8/8 (100%)

---

## 🔍 Análisis por Complejidad

### Low Complexity
- Tests: 17
- Encontrados: 15/17 (88%)
- Tool correcto: 17/17 (100%)

### Medium Complexity
- Tests: 24
- Encontrados: 22/24 (92%)
- Tool correcto: 19/24 (79%)

### High Complexity
- Tests: 6
- Encontrados: 6/6 (100%)
- Tool correcto: 5/6 (83%)

### Very High Complexity
- Tests: 3
- Encontrados: 3/3 (100%)
- Tool correcto: 2/3 (67%)

---

## 🛠️ Uso de Tools

- **fuzzy_search_smart**: 22 llamadas (44.0%)
- **search_products**: 19 llamadas (38.0%)
- **fetch_by_sku**: 9 llamadas (18.0%)

---

## ⚠️ Tipos de Errores Encontrados

- **Wrong Tool Selection**: 7 casos
- **False Negative**: 1 casos

---

## 📋 Detalle de Casos de Prueba


### Ambiguous Implicit Need


**40. tengo que estudiar mejor**
- Tipo: `ambiguous`
- Complejidad: `high`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 6198ms (tool: 594.0ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para ayudarte a estudiar mejor, te recomiendo:

🤖 **Set Robótico Educativo** - ¡Aprende jugando y programando!
   🏷️ SKU: KIDS-0013
   🏭 Marca: EduBots
   💰 Precio: $59.99
   ⭐ Lo mejor: Kit completo para aprender robótica y programación de forma divertida
   📋 Detalles: Multicolor, ideal para todas las edades

¿Te gustaría saber si requiere conocimientos previos o si incluye tutoriales paso a paso? ¿O te interesaría ver otros productos para estudiar mejor como lámparas de escritorio, organizadores o auriculares con cancelación de ruido?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='tengo que estudiar mejor', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='tengo que estudiar mejor', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.64ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='tengo que estudiar mejor', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.90ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='tengo que estudiar mejor', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.10ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='tengo que estudiar mejor', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.72ms
• Estado: ✅ Éxito
---
🔧
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='tengo que estudiar mejor', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.03ms
• Estado: ✅ Éxito
```

</details>

---

**42. mi celular se cae mucho**
- Tipo: `ambiguous`
- Complejidad: `high`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 4525ms (tool: 580.1ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para proteger tu celular de las caídas, te recomiendo:

🛡️ **Protector Vidrio 3D** - ¡La mejor defensa para tu pantalla!
   🏷️ SKU: MOB-0003
   🏭 Marca: GlassGuard
   💰 Precio: $9.99
   ⭐ Lo mejor: Vidrio templado resistente a golpes y rayaduras
   📋 Detalles: Transparente, anti-huella, tamaño 6.5in

¿Te gustaría saber si es compatible con tu modelo de celular o si tenemos fundas anti-golpes disponibles?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='mi celular se cae mucho', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='mi celular se cae mucho', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.67ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='mi celular se cae mucho', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.90ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='mi celular se cae mucho', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.11ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='mi celular se cae mucho', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.73ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='mi celular se cae mucho', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 580.12ms
• Estado: ✅ Éxito
```

</details>

---

**43. trabajo mucho en la computadora**
- Tipo: `ambiguous`
- Complejidad: `very_high`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 4479ms (tool: 264.1ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Si trabajas mucho en la computadora, te recomiendo:

💻 **Laptop Ultralight 13"** - ¡Potencia y comodidad para largas jornadas!
   🏷️ SKU: COMP-0009
   🏭 Marca: ThinBook
   💰 Precio: $999.00
   ⭐ Lo mejor: Ligera y con buen rendimiento para trabajar sin problemas
   📋 Detalles: 16GB RAM, SSD 512GB, pantalla de 13 pulgadas, color gris

¿Te gustaría saber qué tipo de procesador tiene o cuánto dura la batería? ¿O te interesaría ver otros productos para trabajar más cómodo como sillas ergonómicas, monitores o teclados?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='trabajo mucho en la computadora', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='trabajo mucho en la computadora', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.64ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='trabajo mucho en la computadora', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.90ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='trabajo mucho en la computadora', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.11ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='trabajo mucho en la computadora', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='trabajo mucho en la computadora', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 264.13ms
• Estado: ✅ Éxito
```

</details>

---

**44. me gusta jugar videojuegos**
- Tipo: `ambiguous`
- Complejidad: `very_high`
- Tool esperado: `search_products`
- Tool usado: `fuzzy_search_smart` ✗
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 1323ms (tool: 9.7ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
¡Genial! Si te gusta jugar videojuegos, te puedo ofrecer:

📺 **Smart TV 50" 4K** - ¡Para una experiencia de juego inmersiva!
   🏷️ SKU: TV-0005
   🏭 Marca: ViewPlus
   💰 Precio: $399.00
   ⭐ Lo mejor: Imagen 4K con HDR para colores vibrantes y detalles nítidos
   📋 Detalles: Televisor de 50 pulgadas, color negro

¿Te gustaría saber si tiene baja latencia para gaming o si es compatible con consolas de última generación? ¿O te interesaría ver otros productos para gaming como teclados, ratones, auriculares o sillas?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='videojuegos', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='videojuegos', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.56ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='videojuegos', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 8.85ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='videojuegos', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.70ms
• Estado: ✅ Éxito
```

</details>

---

### Ambiguous Location


**38. busco algo para mi escritorio**
- Tipo: `ambiguous`
- Complejidad: `high`
- Tool esperado: `search_products`
- Tool usado: `fuzzy_search_smart` ✗
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 4232ms (tool: 9.0ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Para tu escritorio, te puedo ofrecer:

✍️ **Escritorio Ajustable** - ¡Trabaja de pie o sentado, como prefieras!
   🏷️ SKU: OFF-0019
   🏭 Marca: ErgoDesk
   💰 Precio: $259.00
   ⭐ Lo mejor: Altura ajustable eléctricamente para máxima comodidad
   📋 Detalles: Color blanco, tamaño 120x60 cm

¿Te gustaría saber si tiene memoria para guardar alturas predefinidas o si es fácil de ensamblar? ¿O te interesaría ver otros productos para tu escritorio como lámparas, organizadores o sillas ergonómicas?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='escritorio', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.39ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='escritorio', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.57ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='escritorio', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 8.95ms
• Estado: ✅ Éxito
```

</details>

---

### Ambiguous Open Ended


**41. algo para regalar a mi mamá**
- Tipo: `ambiguous`
- Complejidad: `very_high`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 6021ms (tool: 447.7ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Qué lindo detalle! Para regalar a tu mamá, te recomiendo:

🛌 **Almohada Memory Foam** - ¡Para que descanse como se merece!
   🏷️ SKU: BED-0025
   🏭 Marca: SleepWell
   💰 Precio: $45.00
   ⭐ Lo mejor: Almohada ortopédica con memoria de forma para un sueño reparador
   📋 Detalles: Color blanco, tamaño Standard

¿Te gustaría saber si es hipoalergénica o si es adecuada para personas que duermen de lado o boca arriba? ¿O te interesaría ver otros regalos para mamá como productos de belleza, accesorios o artículos para el hogar?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para regalar a mi mamá', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para regalar a mi mamá', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.73ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para regalar a mi mamá', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.92ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para regalar a mi mamá', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.11ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para regalar a mi mamá', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para regalar a mi mamá', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 447.69ms
• Estado: ✅ Éxito
```

</details>

---

### Ambiguous Product Vs Need


**37. necesito una laptop**
- Tipo: `ambiguous`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 4064ms (tool: 9.6ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Te puedo ofrecer:

💻 **Laptop Ultralight 13"** - ¡Ligera, potente y lista para acompañarte a donde vayas!
   🏷️ SKU: COMP-0009
   🏭 Marca: ThinBook
   💰 Precio: $999.00
   ⭐ Lo mejor: Ultraligera y fácil de transportar
   📋 Detalles: 16GB RAM, SSD 512GB, pantalla de 13 pulgadas, color gris

¿La necesitas para trabajo, estudio, gaming o algo más? Con esa info puedo darte mejores recomendaciones.
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='laptop', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='laptop', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.58ms
• Estado: ✅ Éxito
```

</details>

---

**39. quiero zapatillas**
- Tipo: `ambiguous`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 3132ms (tool: 8.8ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Te puedo ofrecer:

👟 **Zapatillas RunFast 2** - ¡Comodidad y rendimiento en cada paso!
   🏷️ SKU: SPORT-0014
   🏭 Marca: RunFast
   💰 Precio: $89.00
   ⭐ Lo mejor: Amortiguación superior para proteger tus articulaciones
   📋 Detalles: Color azul, talla 42

¿Las necesitas para correr, entrenar, uso casual o algo más? Con esa info puedo darte mejores recomendaciones.
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='zapatillas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.39ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='zapatillas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.56ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='zapatillas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 8.84ms
• Estado: ✅ Éxito
```

</details>

---

### Category Colloquial


**31. tienes cosas para el auto**
- Tipo: `category_browse`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 16
- Calidad de respuesta: 90/100
- Tiempo: 4637ms (tool: 10.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! En cosas para el auto, te puedo ofrecer:

🚗 **GPS Navigator 7"** - ¡Nunca te pierdas en la carretera!
   🏷️ SKU: AUTO-0016
   🏭 Marca: NavRoad
   💰 Precio: $129.99
   ⭐ Lo mejor: Mapas offline para que no dependas de la conexión
   📋 Detalles: Pantalla de 7 pulgadas, color negro

¿Te gustaría saber si tiene alertas de tráfico en tiempo real o si es compatible con Android Auto/Apple CarPlay? ¿O te interesaría ver otros productos para el auto como cargadores, soportes para celular o kits de limpieza?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='cosas para el auto', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='cosas para el auto', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.57ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='cosas para el auto', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 10.48ms
• Estado: ✅ Éxito
```

</details>

---

**32. qué vendes para deportistas**
- Tipo: `category_browse`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 4697ms (tool: 9.0ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Para deportistas, te puedo ofrecer:

👟 **Zapatillas RunFast 2** - ¡Para que rindas al máximo en cada carrera!
   🏷️ SKU: SPORT-0014
   🏭 Marca: RunFast
   💰 Precio: $89.00
   ⭐ Lo mejor: Amortiguación superior para proteger tus articulaciones
   📋 Detalles: Color azul, talla 42

¿Te gustaría saber qué tipo de amortiguación tienen o si están disponibles en otras tallas? ¿O te interesaría ver otros productos para deportistas como smartwatches, ropa deportiva o accesorios de entrenamiento?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='para deportistas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='para deportistas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.55ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='para deportistas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 10.47ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='para deportistas', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.02ms
• Estado: ✅ Éxito
```

</details>

---

**35. tienes gadgets tecnológicos**
- Tipo: `category_browse`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ❌ 0
- Calidad de respuesta: 20/100
- Tiempo: 2945ms (tool: 11.2ms)
- ⚠️ Error: `false_negative`

<details>
<summary>Ver respuesta completa</summary>

```
😔 No encontré gadgets tecnológicos en nuestro inventario actual.

Pero déjame ayudarte: ¿Qué tipo de gadget tecnológico estás buscando? Por ejemplo:
• ¿Para el hogar?
• ¿Para el trabajo?
• ¿Para el entretenimiento?

Con eso puedo recomendarte alternativas que sí tenemos.

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='gadgets tecnológicos', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 11.22ms
• Estado: ✅ Éxito
```

</details>

---

### Category Simple


**29. qué tienes en gaming**
- Tipo: `category_browse`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 3572ms (tool: 10.7ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! En gaming, te puedo ofrecer:

🎮 **Silla Gaming XLR** - ¡Comodidad y estilo para tus sesiones de juego!
   🏷️ SKU: GAM-0011
   🏭 Marca: ProChair
   💰 Precio: $189.99
   ⭐ Lo mejor: Diseño ergonómico y luces RGB personalizables
   📋 Detalles: Color negro/rojo, soporte lumbar ajustable

¿Te gustaría saber si tiene reposabrazos ajustables o si el respaldo es reclinable? ¿O te interesaría ver otros productos gaming como teclados, ratones o auriculares?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='gaming', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.41ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='gaming', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.68ms
• Estado: ✅ Éxito
```

</details>

---

**30. muéstrame productos de cocina**
- Tipo: `category_browse`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 4232ms (tool: 10.1ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! En productos de cocina, te puedo ofrecer:

🔪 **Licuadora Pro 1200W** - ¡Prepara tus recetas favoritas en segundos!
   🏷️ SKU: KITCH-0008
   🏭 Marca: BlendMaster
   💰 Precio: $89.50
   ⭐ Lo mejor: Potente motor de 1200W para resultados perfectos
   📋 Detalles: Vaso de vidrio resistente, color rojo

¿Te gustaría saber si tiene diferentes velocidades o si es fácil de limpiar? ¿O te interesaría ver otros productos de cocina como ollas, sartenes o utensilios?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='productos de cocina', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.40ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='productos de cocina', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.57ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='productos de cocina', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.08ms
• Estado: ✅ Éxito
```

</details>

---

**33. productos relacionados con música**
- Tipo: `category_browse`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2534ms (tool: 9.6ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! En productos relacionados con música, te puedo ofrecer:

🎹 **Teclado MIDI 49** - ¡Da rienda suelta a tu creatividad musical!
   🏷️ SKU: MUS-0027
   🏭 Marca: TuneMaster
   💰 Precio: $199.00
   ⭐ Lo mejor: Ideal para producción musical y composición
   📋 Detalles: Controlador MIDI con 49 teclas, color negro

¿Te gustaría saber si es compatible con tu software de producción musical o si tiene pads sensibles a la velocidad? ¿O te interesaría ver otros productos relacionados con música como auriculares de estudio, micrófonos o interfaces de audio?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='música', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.40ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='música', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.56ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='música', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.09ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='música', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.62ms
• Estado: ✅ Éxito
```

</details>

---

**34. qué hay en la sección de hogar**
- Tipo: `category_browse`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 5896ms (tool: 9.9ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! En la sección de hogar, te puedo ofrecer:

🤖 **Robot Aspirador S50** - ¡Deja que la limpieza sea cosa del pasado!
   🏷️ SKU: HOME-0007
   🏭 Marca: CleanBot
   💰 Precio: $299.99
   ⭐ Lo mejor: Limpieza automática con mapeo inteligente y control por app
   📋 Detalles: Color blanco, ideal para todo tipo de pisos

¿Te gustaría saber si es compatible con asistentes de voz o cuánto tiempo tarda en cargar? ¿O te interesaría ver otros productos para el hogar como lámparas, almohadas o productos de cocina?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='hogar', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.39ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='hogar', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.56ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='hogar', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 10.47ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='hogar', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='hogar', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.87ms
• Estado: ✅ Éxito
```

</details>

---

**36. artículos para oficina y trabajo**
- Tipo: `category_browse`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 16
- Calidad de respuesta: 90/100
- Tiempo: 5602ms (tool: 11.4ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! En artículos para oficina y trabajo, te puedo ofrecer:

🌐 **Switch Ethernet 8 Puertos** - ¡Conexión estable y rápida para tu oficina!
   🏷️ SKU: COM-0037
   🏭 Marca: NetGear
   💰 Precio: $59.99
   ⭐ Lo mejor: Ideal para conectar varios dispositivos a la red
   📋 Detalles: Switch gigabit con 8 puertos, color negro

¿Te gustaría saber si es compatible con redes PoE o si es fácil de configurar? ¿O te interesaría ver otros artículos para oficina y trabajo como sillas ergonómicas, teclados, ratones o monitores?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='artículos para oficina y trabajo', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.39ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='artículos para oficina y trabajo', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.57ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='artículos para oficina y trabajo', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 10.47ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='artículos para oficina y trabajo', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='artículos para oficina y trabajo', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 11.36ms
• Estado: ✅ Éxito
```

</details>

---

### Fuzzy Clean


**9. busco auriculares bluetooth**
- Tipo: `fuzzy_product_name`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2368ms (tool: 10.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Encontré estos auriculares Bluetooth:

🎧 **Auriculares Inalámbricos X1** - Sonido inmersivo sin cables
   🏷️ SKU: AUD-0001
   🏭 Marca: SonicWave
   💰 Precio: $79.99
   ⭐ Lo mejor: Cancelación de ruido y 30h de batería
   📋 Detalles: Color negro, conexión Bluetooth

¿Te gustaría saber más sobre su calidad de sonido o si son resistentes al agua?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='auriculares bluetooth', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.49ms
• Estado: ✅ Éxito
```

</details>

---

**10. necesito un teclado mecanico rgb**
- Tipo: `fuzzy_product_name`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2986ms (tool: 9.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Por supuesto! Aquí tienes un teclado mecánico RGB:

⌨️ **Teclado Mecánico MK-80** - ¡Ilumina tu juego!
   🏷️ SKU: GAM-0012
   🏭 Marca: KeyForge
   💰 Precio: $119.00
   ⭐ Lo mejor: Retroiluminación RGB personalizable
   📋 Detalles: Switches táctiles, color negro, tamaño completo

¿Te gustaría saber qué tipo de switches usa o si tiene software para personalizar la iluminación?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='teclado mecanico rgb', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.34ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='teclado mecanico rgb', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.50ms
• Estado: ✅ Éxito
```

</details>

---

**11. quiero comprar una laptop para programar**
- Tipo: `fuzzy_product_name`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `search_products` ✗
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 3363ms (tool: 594.3ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
¡Perfecto! Encontré esta opción que podría interesarte:

💻 **Laptop Ultralight 13"** - ¡Ideal para programar en cualquier lugar!
   🏷️ SKU: COMP-0009
   🏭 Marca: ThinBook
   💰 Precio: $999.00
   ⭐ Lo mejor: Ultraligera y fácil de transportar
   📋 Specs: 16GB RAM, SSD 512GB, pantalla de 13 pulgadas

¿Te gustaría saber qué tipo de procesador tiene o cuánto dura la batería?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='laptop para programar', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.28ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='laptop para programar', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.34ms
• Estado: ✅ Éxito
```

</details>

---

**15. mouse gaming con luces**
- Tipo: `fuzzy_product_name`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2763ms (tool: 11.0ms)

<details>
<summary>Ver respuesta completa</summary>

```
Lo siento, no encontré un mouse gaming con luces directamente. Sin embargo, encontré una silla gaming con luces RGB que podría interesarte:

🎮 **Silla Gaming XLR** - ¡Ilumina tu setup!
   🏷️ SKU: GAM-0011
   🏭 Marca: ProChair
   💰 Precio: $189.99
   ⭐ Lo mejor: Diseño ergonómico y luces RGB personalizables
   📋 Detalles: Color negro/rojo, soporte lumbar ajustable

¿Te gustaría saber más sobre esta silla o prefieres que busque otras opciones de mouse gaming?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='mouse gaming con luces', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 11.02ms
• Estado: ✅ Éxito
```

</details>

---

**16. smartwatch con gps**
- Tipo: `fuzzy_product_name`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 16
- Calidad de respuesta: 90/100
- Tiempo: 3252ms (tool: 11.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Encontré este smartwatch:

⌚ **Reloj SmartFit** - Tu compañero ideal para el deporte
   🏷️ SKU: FASH-0026
   🏭 Marca: TimeTech
   💰 Precio: $129.99
   ⭐ Lo mejor: GPS integrado para registrar tus rutas
   📋 Detalles: Monitor de frecuencia cardíaca y notificaciones

¿Te gustaría saber si es resistente al agua o cuánto dura la batería con el GPS activado?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='smartwatch con gps', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.43ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='smartwatch con gps', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 11.47ms
• Estado: ✅ Éxito
```

</details>

---

**17. bicicleta plegable urbana**
- Tipo: `fuzzy_product_name`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2547ms (tool: 9.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Encontré esta bicicleta plegable urbana:

🚲 **Bicicleta Plegable** - ¡La ciudad a tu alcance!
   🏷️ SKU: SPORT-0040
   🏭 Marca: FoldBike
   💰 Precio: $349.99
   ⭐ Lo mejor: Cuadro plegable para fácil transporte
   📋 Detalles: Color negro, ideal para la ciudad

¿Te gustaría saber cuánto pesa o qué tipo de frenos tiene?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='bicicleta plegable urbana', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.48ms
• Estado: ✅ Éxito
```

</details>

---

**18. cámara fotográfica profesional**
- Tipo: `fuzzy_product_name`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `search_products` ✗
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5970ms (tool: 663.0ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
Ok, no encontré una cámara *profesional* como tal, pero encontré esta cámara que podría ser una buena alternativa:

📷 **Cámara GoTravel 12MP** - ¡Captura tus aventuras!
   🏷️ SKU: CAM-0006
   🏭 Marca: TravelCam
   💰 Precio: $249.00
   ⭐ Lo mejor: Compacta y fácil de llevar a todos lados
   📋 Detalles: Color plateado, ideal para viajes

¿Te gustaría saber si tiene zoom óptico o si graba video en 4K?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='cámara fotográfica profesional', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.07ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='cámara fotográfica profesional', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.26ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='cámara fotográfica profesional', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 662.96ms
• Estado: ✅ Éxito
```

</details>

---

### Fuzzy Typo


**12. auriculars inalambrico**
- Tipo: `fuzzy_typo`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2902ms (tool: 9.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Encontré estos auriculares inalámbricos:

🎧 **Auriculares Inalámbricos X1** - Libertad sin cables
   🏷️ SKU: AUD-0001
   🏭 Marca: SonicWave
   💰 Precio: $79.99
   ⭐ Lo mejor: Cancelación de ruido y batería de 30 horas
   📋 Detalles: Color negro, conexión Bluetooth

¿Te gustaría saber si tienen micrófono integrado o si son compatibles con asistentes de voz?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='auriculars inalambrico', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.39ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='auriculars inalambrico', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.55ms
• Estado: ✅ Éxito
```

</details>

---

**13. silla ergonomica para oficna**
- Tipo: `fuzzy_typo`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 16
- Calidad de respuesta: 90/100
- Tiempo: 3532ms (tool: 11.8ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Encontré esta silla ergonómica para oficina:

💺 **Silla Oficina Comfort** - ¡Comodidad y soporte para tu espalda!
   🏷️ SKU: OFF-0020
   🏭 Marca: OfficeEase
   💰 Precio: $149.99
   ⭐ Lo mejor: Soporte lumbar ajustable
   📋 Detalles: Color gris, asiento acolchado

¿Te gustaría saber si tiene reposabrazos ajustables o si el respaldo es reclinable?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='silla ergonomica para oficna', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.29ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='silla ergonomica para oficna', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 9.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='silla ergonomica para oficna', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 16 producto(s) encontrado(s)
• Tiempo de ejecución: 11.84ms
• Estado: ✅ Éxito
```

</details>

---

**14. roboot aspirador intelignte**
- Tipo: `fuzzy_typo`
- Complejidad: `high`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ✅ 15
- Calidad de respuesta: 90/100
- Tiempo: 2971ms (tool: 9.1ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Encontré este robot aspirador inteligente:

🤖 **Robot Aspirador S50** - ¡Limpieza sin esfuerzo!
   🏷️ SKU: HOME-0007
   🏭 Marca: CleanBot
   💰 Precio: $299.99
   ⭐ Lo mejor: Mapeo inteligente y control por app
   📋 Detalles: Color blanco, ideal para todo tipo de pisos

¿Te gustaría saber si es compatible con asistentes de voz o cuánto tiempo tarda en cargar?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='roboot aspirador intelignte', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 10.44ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='roboot aspirador intelignte', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 15 producto(s) encontrado(s)
• Tiempo de ejecución: 9.09ms
• Estado: ✅ Éxito
```

</details>

---

### Not Exists Absurd


**47. necesito un Tesla Model Y**
- Tipo: `not_exists`
- Complejidad: `low`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ❌ 0
- Calidad de respuesta: 30/100
- Tiempo: 3016ms (tool: 11.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
Lo siento, no tenemos el Tesla Model Y disponible. No disponemos de vehículos.

😔 No encontré productos con esos términos exactos.

¿Te puedo ayudar con otra cosa?

---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='Tesla Model Y', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 11.26ms
• Estado: ✅ Éxito
```

</details>

---

### Not Exists Brand Specific


**48. quiero un microondas Samsung**
- Tipo: `not_exists`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `search_products` ✗
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5991ms (tool: 613.7ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
A pesar de no encontrar un microondas Samsung, encontré esta cobija térmica que te mantendrá calentito mientras esperas que descongelen tus alimentos:

🔥 **Cobija Termica 220x240** - ¡Para esos días fríos!
   🏷️ SKU: BED-0030
   🏭 Marca: WarmHome
   💰 Precio: $39.90
   ⭐ Lo mejor: Microfibra suave y térmica para máximo confort
   📋 Detalles: Color gris, tamaño 220x240 cm

¿Te gustaría saber si es lavable a máquina o si tenemos otros colores disponibles?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='microondas', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='microondas Samsung', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 11.24ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='microondas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.69ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='microondas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.91ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='microondas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 613.69ms
• Estado: ✅ Éxito
```

</details>

---

**49. tienes lavadora automática LG**
- Tipo: `not_exists`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `search_products` ✗
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 6069ms (tool: 455.0ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
A pesar de no encontrar una lavadora automática, encontré este robot aspirador que te ayudará a mantener tu casa limpia mientras esperas que tu ropa se lave en otro lugar:

🤖 **Robot Aspirador S50** - ¡Limpieza automática para tu hogar!
   🏷️ SKU: HOME-0007
   🏭 Marca: CleanBot
   💰 Precio: $299.99
   ⭐ Lo mejor: Limpia tu casa automáticamente con mapeo inteligente
   📋 Detalles: Color blanco, ideal para todo tipo de pisos

¿Te gustaría saber si es compatible con asistentes de voz o cuánto tiempo tarda en cargar?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='lavadora automática', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='lavadora automática LG', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 11.23ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='lavadora automática', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.65ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='lavadora automática', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.91ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='lavadora automática', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 615.
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='lavadora automática', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 455.04ms
• Estado: ✅ Éxito
```

</details>

---

### Not Exists Sku


**50. SKU inexistente XYZ-9999**
- Tipo: `not_exists`
- Complejidad: `low`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ❌ 0
- Calidad de respuesta: 20/100
- Tiempo: 2186ms (tool: 8.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
Lo siento, no encontré ningún producto con el SKU XYZ-9999 en nuestro inventario.

😔 No encontré productos con esos términos exactos.

¿Te puedo ayudar con otra cosa?
---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='XYZ-9999'`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 8.72ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='XYZ-9999'`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 8.25ms
• Estado: ✅ Éxito
```

</details>

---

### Not Exists Specific


**45. tienes iPhone 15 Pro Max**
- Tipo: `not_exists`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `fuzzy_search_smart` ✓
- Productos encontrados: ❌ 0
- Calidad de respuesta: 20/100
- Tiempo: 2812ms (tool: 12.9ms)

<details>
<summary>Ver respuesta completa</summary>

```
😔 Lo siento, no encontré el iPhone 15 Pro Max en nuestro inventario actual.

Pero déjame ayudarte: ¿Qué características específicas del iPhone 15 Pro Max te interesan? Por ejemplo:
• ¿La cámara?
• ¿El rendimiento?
• ¿El tamaño de la pantalla?

Con eso puedo recomendarte alternativas equivalentes o superiores que sí tenemos.
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='iPhone 15 Pro Max', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 11.23ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='iPhone 15 Pro Max', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 12.94ms
• Estado: ✅ Éxito
```

</details>

---

**46. busco PlayStation 5 Digital**
- Tipo: `not_exists`
- Complejidad: `medium`
- Tool esperado: `fuzzy_search_smart`
- Tool usado: `search_products` ✗
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 6580ms (tool: 625.3ms)
- ⚠️ Error: `wrong_tool_selection`

<details>
<summary>Ver respuesta completa</summary>

```
Sigo sin encontrar el PlayStation 5 Digital. En cambio, encontré este Smart TV que te permitirá disfrutar al máximo de tus juegos:

📺 **Smart TV 50" 4K** - ¡Para una experiencia de juego inmersiva!
   🏷️ SKU: TV-0005
   🏭 Marca: ViewPlus
   💰 Precio: $399.00
   ⭐ Lo mejor: Imagen 4K con HDR para colores vibrantes y detalles nítidos
   📋 Detalles: Televisor de 50 pulgadas, color negro

¿Te gustaría saber si tiene baja latencia para gaming o si es compatible con consolas de última generación?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='PlayStation 5 Digital', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fuzzy_search_smart`
• Parámetros: `query='PlayStation 5 Digital', limit=10, strict_threshold=0.3, word_threshold=0.4, fallback_threshold=0.2`
• Resultados: 0 producto(s) encontrado(s)
• Tiempo de ejecución: 11.22ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='PlayStation 5 Digital', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 600.08ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='PlayStation 5 Digital', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 266.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='PlayStation 5 Digital', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 625.28ms
• Estado: ✅ Éxito
```

</details>

---

### Semantic Benefit


**19. algo para mantener mi casa limpia sin esfuerzo**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 3680ms (tool: 357.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Tengo la solución perfecta!

🤖 **Robot Aspirador S50** - ¡Tu asistente de limpieza personal!
   🏷️ SKU: HOME-0007
   🏭 Marca: CleanBot
   💰 Precio: $299.99
   ⭐ Lo mejor: Limpia tu casa automáticamente con mapeo inteligente
   📋 Detalles: Control por app, ideal para todo tipo de pisos

¿Te gustaría saber si es compatible con asistentes de voz o cuánto tiempo tarda en cargar?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para mantener mi casa limpia sin esfuerzo', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.22ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para mantener mi casa limpia sin esfuerzo', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 600.54ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para mantener mi casa limpia sin esfuerzo', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 357.28ms
• Estado: ✅ Éxito
```

</details>

---

**20. necesito mejorar la velocidad de mi PC**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 3738ms (tool: 262.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para mejorar la velocidad de tu PC, te recomiendo:

🚀 **SSD NVMe 1TB** - ¡Dale un turbo a tu computadora!
   🏷️ SKU: COMP-0038
   🏭 Marca: FastDrive
   💰 Precio: $119.99
   ⭐ Lo mejor: Acelera el inicio de Windows y tus programas
   📋 Detalles: Unidad NVMe con altas tasas de lectura/escritura

¿Te gustaría saber si es compatible con tu PC o si necesitas algún adaptador?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito mejorar la velocidad de mi PC', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.16ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito mejorar la velocidad de mi PC', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 595.38ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito mejorar la velocidad de mi PC', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 262.26ms
• Estado: ✅ Éxito
```

</details>

---

**21. quiero escuchar música con excelente calidad de audio**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 4456ms (tool: 258.4ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para disfrutar de tu música con la mejor calidad, te recomiendo:

🎧 **Auriculares Estudio S-80** - ¡Sonido profesional en tus oídos!
   🏷️ SKU: MUS-0049
   🏭 Marca: StudioPro
   💰 Precio: $129.00
   ⭐ Lo mejor: Calidad de audio excepcional para los oídos más exigentes
   📋 Detalles: Auriculares de monitoreo para estudio, color negro

¿Te gustaría saber qué tipo de drivers tienen o si son circumaurales (cubren toda la oreja)?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero escuchar música con excelente calidad de audio', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.17ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero escuchar música con excelente calidad de audio', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 598.22ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero escuchar música con excelente calidad de audio', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 265.53ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero escuchar música con excelente calidad de audio', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 258.43ms
• Estado: ✅ Éxito
```

</details>

---

**22. algo para proteger mi smartphone de golpes**
- Tipo: `semantic_need`
- Complejidad: `low`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 4722ms (tool: 250.9ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para proteger tu smartphone de golpes, te recomiendo:

🛡️ **Protector Vidrio 3D** - ¡La mejor defensa para tu pantalla!
   🏷️ SKU: MOB-0003
   🏭 Marca: GlassGuard
   💰 Precio: $9.99
   ⭐ Lo mejor: Vidrio templado resistente a golpes y rayaduras
   📋 Detalles: Transparente, anti-huella, tamaño 6.5in

¿Te gustaría saber si es compatible con tu modelo de smartphone o si tenemos otros tipos de protectores?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para proteger mi smartphone de golpes', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.19ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para proteger mi smartphone de golpes', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.95ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para proteger mi smartphone de golpes', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 261.88ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para proteger mi smartphone de golpes', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 255.15ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para proteger mi smartphone de golpes', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 250.87ms
• Estado: ✅ Éxito
```

</details>

---

**23. necesito trabajar más cómodo desde casa**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5051ms (tool: 325.4ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para que trabajes más cómodo desde casa, te recomiendo:

💺 **Silla Oficina Comfort** - ¡Tu espalda te lo agradecerá!
   🏷️ SKU: OFF-0020
   🏭 Marca: OfficeEase
   💰 Precio: $149.99
   ⭐ Lo mejor: Soporte lumbar ajustable para largas jornadas
   📋 Detalles: Color gris, asiento acolchado

¿Te gustaría saber si tiene reposabrazos ajustables o si el respaldo es reclinable?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito trabajar más cómodo desde casa', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.19ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito trabajar más cómodo desde casa', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 595.69ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito trabajar más cómodo desde casa', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 259.95ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito trabajar más cómodo desde casa', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 253.14ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito trabajar más cómodo desde casa', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 248.86ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito trabajar más cómodo desde casa', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 325.43ms
• Estado: ✅ Éxito
```

</details>

---

**24. quiero hacer ejercicio cardiovascular en mi departamento**
- Tipo: `semantic_need`
- Complejidad: `high`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5613ms (tool: 694.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para hacer ejercicio cardiovascular en tu departamento, te recomiendo:

🚲 **Bicicleta Plegable** - ¡Cardio sin ocupar espacio!
   🏷️ SKU: SPORT-0040
   🏭 Marca: FoldBike
   💰 Precio: $349.99
   ⭐ Lo mejor: Se pliega para guardar fácilmente en espacios pequeños
   📋 Detalles: Color negro, ideal para ejercicio cardiovascular en casa

¿Te gustaría saber si tiene diferentes niveles de resistencia o cuánto peso soporta?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero hacer ejercicio cardiovascular en mi departamento', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.16ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero hacer ejercicio cardiovascular en mi departamento', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 595.00ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero hacer ejercicio cardiovascular en mi departamento', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.08ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero hacer ejercicio cardiovascular en mi departamento', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 253.30ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero hacer ejercicio cardiovascular en mi departamento', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.05ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado:
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero hacer ejercicio cardiovascular en mi departamento', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 694.32ms
• Estado: ✅ Éxito
```

</details>

---

**25. algo para que mi perro duerma bien**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5273ms (tool: 427.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para que tu perro duerma como un rey, te recomiendo:

🐾 **Cama Mascota Deluxe** - ¡El descanso que tu perro merece!
   🏷️ SKU: PET-0042
   🏭 Marca: PetComfort
   💰 Precio: $39.00
   ⭐ Lo mejor: Acolchada y suave para un sueño reparador
   📋 Detalles: Color gris, funda lavable, tamaño Large

¿Te gustaría saber las dimensiones exactas o si tenemos otros tamaños disponibles?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para que mi perro duerma bien', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.19ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para que mi perro duerma bien', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.68ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para que mi perro duerma bien', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 261.06ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para que mi perro duerma bien', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.17ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para que mi perro duerma bien', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.79ms
• Estado: ✅ Éxito
---
🔧 **
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para que mi perro duerma bien', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 427.48ms
• Estado: ✅ Éxito
```

</details>

---

**26. necesito reducir el dolor de espalda al dormir**
- Tipo: `semantic_need`
- Complejidad: `high`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5264ms (tool: 430.9ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para reducir el dolor de espalda al dormir, te recomiendo:

🛌 **Almohada Memory Foam** - ¡El soporte perfecto para tu cuello y espalda!
   🏷️ SKU: BED-0025
   🏭 Marca: SleepWell
   💰 Precio: $45.00
   ⭐ Lo mejor: Almohada ortopédica con memoria de forma
   📋 Detalles: Color blanco, tamaño Standard

¿Te gustaría saber si es hipoalergénica o si es adecuada para personas que duermen de lado o boca arriba?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito reducir el dolor de espalda al dormir', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.19ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito reducir el dolor de espalda al dormir', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.81ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito reducir el dolor de espalda al dormir', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.91ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito reducir el dolor de espalda al dormir', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.09ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito reducir el dolor de espalda al dormir', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.74ms

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='necesito reducir el dolor de espalda al dormir', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 430.90ms
• Estado: ✅ Éxito
```

</details>

---

**27. quiero jugar videojuegos sin lag ni problemas**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 2721ms (tool: 412.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para jugar videojuegos sin lag ni problemas, te recomiendo:

💻 **Laptop Ultralight 13"** - ¡Rendimiento y portabilidad para gamers!
   🏷️ SKU: COMP-0009
   🏭 Marca: ThinBook
   💰 Precio: $999.00
   ⭐ Lo mejor: 16GB de RAM y SSD para juegos fluidos
   📋 Detalles: Color gris, pantalla de 13 pulgadas

¿Te gustaría saber qué tarjeta gráfica tiene o si cumple con los requisitos de tus juegos favoritos?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero jugar videojuegos sin lag ni problemas', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.18ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero jugar videojuegos sin lag ni problemas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.59ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero jugar videojuegos sin lag ni problemas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.90ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero jugar videojuegos sin lag ni problemas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.12ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero jugar videojuegos sin lag ni problemas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.74ms
• Estado: ✅ Éxito
---

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='quiero jugar videojuegos sin lag ni problemas', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 412.29ms
• Estado: ✅ Éxito
```

</details>

---

**28. algo para iluminar mi habitación con ambiente moderno**
- Tipo: `semantic_need`
- Complejidad: `medium`
- Tool esperado: `search_products`
- Tool usado: `search_products` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 5607ms (tool: 430.2ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Entiendo! Para iluminar tu habitación con un ambiente moderno, te recomiendo:

💡 **Lámpara LED Smart** - ¡Iluminación inteligente a tu alcance!
   🏷️ SKU: HOME-0043
   🏭 Marca: BrightHome
   💰 Precio: $29.99
   ⭐ Lo mejor: Controla la luz desde tu smartphone con conexión WiFi
   📋 Detalles: Color blanco, diseño moderno y minimalista

¿Te gustaría saber si es compatible con asistentes de voz o si tiene diferentes modos de iluminación?

---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para iluminar mi habitación con ambiente moderno', k=5`
• Resultados: 1 producto(s) encontrado(s)
• Tiempo de ejecución: 10.19ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para iluminar mi habitación con ambiente moderno', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 594.75ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para iluminar mi habitación con ambiente moderno', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 260.94ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para iluminar mi habitación con ambiente moderno', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 254.13ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para iluminar mi habitación con ambiente moderno', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 249.73ms
• Estado: ✅ Éxito
---
🔧
---
🔧 **DEBUG INFO**
• Tool invocado: `search_products`
• Parámetros: `query='algo para iluminar mi habitación con ambiente moderno', k=5`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 430.23ms
• Estado: ✅ Éxito
```

</details>

---

### Sku Exact


**1. quiero el TOY-0018**
- Tipo: `exact_sku`
- Complejidad: `low`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 100/100
- Tiempo: 2635ms (tool: 9.1ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Aquí está!

🧩 **Puzzle 1000 Piezas - Mundo** - Para los amantes de los desafíos
   🏷️ SKU: TOY-0018
   🏭 Marca: PuzzleArt
   💰 Precio: $24.50
   ⭐ Lo mejor: Ideal para relajarse y desconectar
   📋 Detalles: 1000 piezas, diseño colorido del mundo

¿Te gustaría agregar este puzzle a tu carrito?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='TOY-0018'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 9.12ms
• Estado: ✅ Éxito
```

</details>

---

**2. necesito producto COMP-0038**
- Tipo: `exact_sku`
- Complejidad: `low`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 2614ms (tool: 9.2ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Por supuesto! Aquí tienes la información del producto:

🚀 **SSD NVMe 1TB** - ¡Velocidad que transforma tu PC!
   🏷️ SKU: COMP-0038
   🏭 Marca: FastDrive
   💰 Precio: $119.99
   ⭐ Lo mejor: Acelera el inicio de Windows y tus juegos favoritos
   📋 Specs: NVMe, 1TB, altas tasas de lectura/escritura

¿Te gustaría saber más sobre su compatibilidad o tiempos de envío?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='COMP-0038'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 9.20ms
• Estado: ✅ Éxito
```

</details>

---

**3. HOME-0007 por favor**
- Tipo: `exact_sku`
- Complejidad: `low`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 2517ms (tool: 8.5ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Aquí tienes!

🤖 **Robot Aspirador S50** - Limpieza inteligente para tu hogar
   🏷️ SKU: HOME-0007
   🏭 Marca: CleanBot
   💰 Precio: $299.99
   ⭐ Lo mejor: Mapeo inteligente y control por app
   📋 Detalles: Color blanco, ideal para todo tipo de pisos

¿Te gustaría saber más sobre su autonomía o compatibilidad con asistentes de voz?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='HOME-0007'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 8.50ms
• Estado: ✅ Éxito
```

</details>

---

**4. información del SKU GAM-0012**
- Tipo: `exact_sku`
- Complejidad: `low`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 2468ms (tool: 8.3ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Claro! Aquí tienes la información del producto GAM-0012:

⌨️ **Teclado Mecánico MK-80** - ¡Para gamers exigentes!
   🏷️ SKU: GAM-0012
   🏭 Marca: KeyForge
   💰 Precio: $119.00
   ⭐ Lo mejor: Switches táctiles y retroiluminación RGB
   📋 Detalles: Color negro, tamaño completo

¿Te gustaría saber qué tipo de switches usa o si es compatible con macros?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='GAM-0012'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 8.29ms
• Estado: ✅ Éxito
```

</details>

---

**5. cuánto cuesta el MUS-0027?**
- Tipo: `exact_sku`
- Complejidad: `medium`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 85/100
- Tiempo: 2075ms (tool: 8.2ms)

<details>
<summary>Ver respuesta completa</summary>

```
El **Teclado MIDI 49** (SKU: MUS-0027) de la marca TuneMaster cuesta $199.00. ¿Te interesa saber más sobre sus características?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='MUS-0027'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 8.24ms
• Estado: ✅ Éxito
```

</details>

---

**6. tienes en stock AUTO-0016**
- Tipo: `exact_sku`
- Complejidad: `medium`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 85/100
- Tiempo: -133ms (tool: 8.6ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Sí! Tenemos en stock el **GPS Navigator 7"** (SKU: AUTO-0016) de la marca NavRoad. Su precio es de $129.99. ¿Te gustaría saber más sobre sus mapas offline o cómo funciona el tráfico en tiempo real?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='AUTO-0016'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 8.58ms
• Estado: ✅ Éxito
```

</details>

---

**7. dame detalles SPORT-0014**
- Tipo: `exact_sku`
- Complejidad: `low`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 3205ms (tool: 7.9ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Aquí tienes los detalles!

👟 **Zapatillas RunFast 2** - ¡Para que llegues más lejos!
   🏷️ SKU: SPORT-0014
   🏭 Marca: RunFast
   💰 Precio: $89.00
   ⭐ Lo mejor: Amortiguación superior para proteger tus articulaciones
   📋 Detalles: Color azul, talla 42

¿Te gustaría saber qué tipo de amortiguación tienen o si están disponibles en otras tallas?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='SPORT-0014'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 8.28ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='SPORT-0014'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 7.94ms
• Estado: ✅ Éxito
```

</details>

---

**8. el SKU que me recomendaste PHOTO-0028**
- Tipo: `exact_sku`
- Complejidad: `medium`
- Tool esperado: `fetch_by_sku`
- Tool usado: `fetch_by_sku` ✓
- Productos encontrados: ✅ 10
- Calidad de respuesta: 90/100
- Tiempo: 2832ms (tool: 9.1ms)

<details>
<summary>Ver respuesta completa</summary>

```
¡Aquí tienes la información del producto!

📸 **Tripode Aluminio 1.8m** - Estabilidad para tus fotos y videos
   🏷️ SKU: PHOTO-0028
   🏭 Marca: SteadyShot
   💰 Precio: $49.00
   ⭐ Lo mejor: Ligero y resistente, ideal para viajes
   📋 Detalles: Color negro, altura máxima 1.8m

¿Te gustaría saber cuánto pesa o qué tipo de cabezal tiene?

---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='PHOTO-0028'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 8.16ms
• Estado: ✅ Éxito
---
🔧 **DEBUG INFO**
• Tool invocado: `fetch_by_sku`
• Parámetros: `sku='PHOTO-0028'`
• Resultados: 10 producto(s) encontrado(s)
• Tiempo de ejecución: 9.13ms
• Estado: ✅ Éxito
```

</details>

---

## 🎓 Conclusiones y Oportunidades de Mejora

### Fortalezas Identificadas

✅ **Respuestas de alta calidad**: 85/100 promedio

### Oportunidades de Mejora

⚠️ **Tasa de falsos negativos**: 4 casos no encontraron productos cuando deberían
⚠️ **Selección incorrecta de tools**: 7 casos usaron tool incorrecto
⚠️ **7 casos con selección incorrecta de tool**
⚠️ **1 falsos negativos** (no encontró cuando debería)
⚠️ **Categoría 'category_colloquial' con baja precisión**: 67%

---

## 📊 Datos Completos

Todos los resultados detallados están disponibles en `test_precision_results.json`

**Generado**: 2025-10-03 15:41:59
**Herramienta**: test_precision_odiseo.py
**Framework**: FastMCP + Google GenAI SDK
