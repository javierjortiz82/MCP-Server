### Requerimiento Mejorado

Se requiere construir una pantalla en \home\javort\odiseo-web cuya experiencia visual sea muy similar a la interfaz de chat en <https://chatgpt.com/>.  
Esta pantalla debe incluir:

1. **Área de interacción tipo chat:**
   - Una **caja de texto** donde el usuario pueda escribir mensajes.
   - Un **botón de enviar**.
   - Mientras se espera la respuesta del servidor, se debe mostrar una **animación de carga** utilizando el archivo `logo.png` ubicado en `/public`.
   - Una vez se reciba la respuesta, la animación debe ocultarse y el mensaje debe mostrarse **con efecto de tipeo progresivo**, no todo el texto de golpe.  
     Esto debe dar la percepción de una conversación fluida con un **agente de IA** llamado **"Odiseo"**.
   - El botón de enviar debe permanecer **deshabilitado** hasta que el usuario haya ingresado texto.

2. **Botón de entrada por voz:**
   - Mostrar un botón de micrófono.
   - Por ahora, al hacer clic solo debe mostrar el mensaje:  
     **"Función no disponible"**.
   - Este mensaje debe traducirse automáticamente según el idioma del usuario usando los archivos de internacionalización existentes en:
     ```
     /src/i18n
     ```

3. **Botón para adjuntar documentos:**
   - Debe permitir seleccionar imágenes, PDF y archivos `.docx`.
   - Por ahora, al hacer clic debe mostrar el mensaje:
     **"Función no disponible"**.
   - Este mensaje también debe ser traducido usando `/src/i18n`.

---

### Manejo de Créditos (Tokens)

La pantalla debe considerar un sistema de uso basado en tokens:

- Cada vez que el usuario envía una consulta, el consumo de tokens debe actualizarse.
- La pantalla debe invocar el siguiente endpoint para procesar consultas:

#### `POST /v1/demo`
- Ubicación del código en backend: `main.py:593`
- Requisitos:
  - Usuario autenticado (Clerk o "legacy")
  - Usuario activo, email verificado, no suspendido
- Respuesta:
  - `DemoResponse` con:
    - Respuesta de IA
    - Tokens usados
    - Tokens restantes
- Posibles errores:
  - **429:** si se excede la cuota
  - **403:** si el usuario no cumple los requisitos

También debe consultarse el estado de cuota:

#### `GET /v1/demo/status`
- Ubicación del código: `main.py:802`
- Parámetros: `user_id`, `session_id` o `fingerprint`
- Respuesta:
  - Tokens usados / restantes
  - Porcentaje utilizado
  - Cantidad de requests
  - Estado de bloqueo

- Si el porcentaje usado es **> 85%**, entonces `is_warning = true`.  
  En este caso, se debe mostrar en la esquina inferior derecha una leyenda pequeña:  
  **"Se acerca al límite de uso diario"**  
  (traducida usando `/src/i18n`).

- Si el usuario supera el máximo permitido, se debe **bloquear el botón de enviar**.

---

### Lineamientos técnicos adicionales

- Seguir la **guía de estilo Airbnb**:  
  https://github.com/airbnb/javascript
- Realizar **code review**.
- No romper funcionalidad existente.
- Garantizar funcionalidad final.
- Aplicar buenas prácticas.
- No inventar nuevas funciones o comportamientos.
- Generar **código y documentación en inglés**.
- Asumir rol: **Arquitecto de Software especialista en frontend, REST y APIs**.
- El frontend se encuentra en \home\javort\odiseo-web 
- El api backend se encuentra en \home\javort\alfredo\MCP-Server\demo_agent
- No realizar commit hasta que se te indique explicitamente.
- Debes mantener el mismo estilo visual que actualmente tiene el sitio.

