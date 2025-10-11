# 🔧 Troubleshooting - Odiseo Bot

Soluciones a problemas comunes al ejecutar Odiseo Bot.

---

## ❌ Error: `ModuleNotFoundError: No module named 'google.generativeai'`

### Síntoma
```
Traceback (most recent call last):
  File "src/client_mcp/core/odiseo_bot.py", line 11, in <module>
    import google.generativeai as genai
ModuleNotFoundError: No module named 'google.generativeai'
```

### Causa
El módulo `google-generativeai` está instalado, pero Python no puede encontrarlo debido a un problema con `PYTHONPATH`. Esto ocurre cuando:
1. Se ejecuta `python main.py` directamente sin configurar el entorno
2. El directorio `src/` no está en el Python path

### Solución 1: Usar el script launcher (Recomendado)
```bash
./run.sh
```

Este script configura automáticamente el `PYTHONPATH` correcto.

### Solución 2: Configurar PYTHONPATH manualmente
```bash
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
python main.py
```

### Solución 3: Instalar en modo editable
```bash
pip install -e .
python main.py
```

---

## ❌ Error: `EOF when reading a line` (loop infinito)

### Síntoma
```
👤 Tú: ❌ Error: EOF when reading a line
👤 Tú: ❌ Error: EOF when reading a line
👤 Tú: ❌ Error: EOF when reading a line
...
```

### Causa
El bot se está ejecutando en **background** o en un entorno **no interactivo** (como un script Bash), donde `input()` no puede leer del usuario.

### Solución
Ejecutar el bot en una **terminal interactiva**:

```bash
# NO funciona (background)
python main.py &

# NO funciona (pipe)
echo "test" | python main.py

# ✅ SÍ funciona (interactivo)
./run.sh
```

---

## ❌ Error: `RuntimeError: Instala la librería 'google-generativeai'`

### Síntoma
```
RuntimeError: Instala la librería 'google-generativeai' con: pip install google-generativeai
```

### Causa
La librería `google-generativeai` no está instalada o hay un conflicto de versiones.

### Solución
```bash
# Desinstalar versiones conflictivas
pip uninstall google-genai google-generativeai -y

# Reinstalar la versión correcta
pip install google-generativeai==0.8.5

# Verificar
python -c "import google.generativeai; print(google.generativeai.__version__)"
```

---

## ❌ Error: `.env` no se carga / API key no encontrada

### Síntoma
```
🔑 Introduce tu GOOGLE_API_KEY:
```

### Causa
El archivo `.env` no existe o no se está cargando correctamente.

### Solución
```bash
# 1. Verificar que .env existe
ls -la .env

# 2. Si no existe, copiarlo desde template
cp .env.example .env

# 3. Editar y agregar tu API key
nano .env  # o vim .env

# 4. Verificar el contenido
grep GOOGLE_API_KEY .env

# Debería mostrar:
# GOOGLE_API_KEY=tu_api_key_aqui
```

---

## ❌ Error: Conexión a MCP Server falla

### Síntoma
```
httpx.ConnectError: All connection attempts failed
httpcore.ConnectError: All connection attempts failed
asyncio.exceptions.CancelledError: Cancelled by cancel scope
```

### Causa
El servidor MCP no está corriendo en el puerto 8009.

### Solución 1: Iniciar el servidor MCP
```bash
# Verificar si el puerto 8009 está en uso
lsof -i :8009

# Si no está corriendo, iniciarlo:
cd /home/javort/Lab01-MCP/mcp
python server.py

# O en background:
cd /home/javort/Lab01-MCP/mcp
nohup python server.py > logs/server.log 2>&1 &
```

### Solución 2: Verificar que el servidor inició correctamente
```bash
# Verificar logs del servidor
tail -f /home/javort/Lab01-MCP/mcp/logs/server.log

# Deberías ver:
# INFO: Uvicorn running on http://0.0.0.0:8009
# ✅ REFACTORED MCP server accessible at http://0.0.0.0:8009/mcp
```

### Solución 3: Cambiar el puerto en `.env` del cliente
```bash
# Si el servidor está en otro puerto, editar .env del cliente
cd /home/javort/Lab01-MCP/client_mcp
nano .env

# Cambiar:
MCP_PORT=8009
# Por el puerto correcto
```

---

## ❌ Error: Tests fallan

### Síntoma
```
FAILED test_improvements.py::test_validator - AssertionError
```

### Solución
```bash
# Ejecutar tests con verbose
PYTHONPATH=src python tests/test_improvements.py

# Si persiste, verificar instalación
python scripts/verify_system.py
```

---

## ❌ Error: MyPy / Ruff errores

### Síntoma
```
error: Cannot find implementation or library stub for module named "google.generativeai"
```

### Solución
```bash
# Instalar type stubs
pip install types-requests types-protobuf

# Ejecutar con configuración correcta
mypy --config-file=pyproject.toml src/client_mcp/
```

---

## ❌ Error: `Could not convert part.function_call to text`

### Síntoma
```
❌ Error enviando mensaje: Could not convert `part.function_call` to text.
```

### Causa
Gemini está haciendo function calls (llamadas a herramientas MCP), pero el código no está manejando correctamente la respuesta que contiene `function_call` en lugar de texto directo.

### Solución
**Este error fue corregido en v2.0.1**. Si aún lo ves:

```bash
# 1. Actualizar a la última versión
git pull

# 2. Verificar que tienes el fix
grep -A 5 "has_function_calls" src/client_mcp/core/odiseo_bot.py

# Deberías ver código que maneja function calls en send_message()
```

### Cómo funciona el fix
El bot ahora:
1. Detecta si la respuesta contiene function calls
2. Extrae los nombres y argumentos de las funciones
3. Envía un mensaje vacío para obtener la respuesta final después de ejecutar las funciones
4. Tiene fallback para extraer texto de partes si es necesario

---

## ❌ Error: `asyncio.exceptions.CancelledError` al salir

### Síntoma
```
asyncio.exceptions.CancelledError: Cancelled by cancel scope
```

### Causa
Este error aparece al salir del bot (comando `/exit` o Ctrl+C). El MCP connector lanza un `CancelledError` durante el shutdown, lo cual es esperado en operaciones asíncronas que se cancelan.

### Solución
**Este error fue corregido en v2.0.1**. El bot ahora:
- Captura específicamente `asyncio.CancelledError`
- Lo trata como evento normal de shutdown
- Suprime el error y continúa con cleanup
- Exporta métricas correctamente antes de salir

### Verificar el fix
```bash
# El bot debería cerrarse limpiamente
$ ./run.sh
👤 Tú: /exit
📊 Métricas exportadas a: metrics/execution_metrics.json
👋 ¡Hasta luego!
✅ Salida limpia (sin traceback)
```

---

## ❌ Error: `Input should be a valid list` (Double Validation Error)

### Síntoma
```
Tool 'fuzzy_search_smart' failed: 1 validation error for fuzzy_search_smartArguments
fields
  Input should be a valid list [type=list_type, input_value='name, description', input_type=str]
```

### Causa
Este error ocurre cuando:
1. Gemini envía un parámetro como lista: `['name', 'description']`
2. El preprocesador local lo convierte a string: `'name, description'` para pasar validación Pydantic
3. Pero el MCP server espera recibir una lista
4. **Root cause**: El schema del MCP server no define `type` para ese parámetro (`type: None`)

### Solución
**Este error fue corregido en v2.0.1** (Problema #7).

El fix implementado:
1. Modificado `_map_json_type_to_python()` en ToolValidator para usar `Any` cuando `type` es `None`
2. El preprocesador ahora mantiene la lista original cuando `type` es `None`
3. Evita la doble conversión: lista → string → error

### Verificar el fix
```bash
# Debería funcionar correctamente
$ ./run.sh
👤 Tú: tienen cobijas termicas?
🔧 Ejecutando: fuzzy_search_smart({'fields': ['name', 'description'], 'query': 'cobijas termicas', ...})
✅ [MCP Official] Resultado: [5 productos encontrados]
🤖 Bot: [Respuesta con productos]
```

### Código del fix
**Archivo**: `src/client_mcp/core/tool_validator.py:197-218`

```python
def _map_json_type_to_python(self, prop_def: dict) -> type:
    json_type = prop_def.get("type")

    # Si no hay tipo definido, usar Any para aceptar cualquier cosa
    if json_type is None:
        return Any

    # Handle array type with items
    if json_type == "array":
        items_type = prop_def.get("items", {}).get("type", "string")
        item_python_type = self._get_basic_python_type(items_type)
        return list[item_python_type]

    return self._get_basic_python_type(json_type)
```

**Preprocesador actualizado** (tool_validator.py:115-118):
```python
elif prop_type is None:
    # Schema doesn't define type - keep original list
    # This is the most common case with MCP tools
    processed[key] = value
```

---

## 🆘 Verificación del Sistema

Si tienes problemas, ejecuta el script de verificación:

```bash
python scripts/verify_system.py
```

Este script verifica:
- ✅ Imports de todos los módulos
- ✅ Configuración y .env
- ✅ Directorios requeridos
- ✅ Documentación

---

## 📚 Recursos Adicionales

- **README.md** - Instalación y uso básico
- **IMPROVEMENTS_SUMMARY.md** - Detalles de mejoras implementadas
- **ODISEO_BOT_GUIDE.md** - Guía completa de uso
- **scripts/README.md** - Documentación de CLI tools

---

## 🐛 Reportar Bugs

Si encuentras un problema no listado aquí:

1. Verifica con `python scripts/verify_system.py`
2. Revisa los logs en modo debug: `DEBUG_MODE=true` en `.env`
3. Reporta el issue con:
   - Descripción del problema
   - Traceback completo
   - Output de `verify_system.py`
   - Versión de Python: `python --version`
   - SO y versión

---

**Última actualización**: 2025-10-03
