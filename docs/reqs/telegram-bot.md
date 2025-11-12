Quiero integrar un nuevo canal de comunicación a mi sistema de chat existente.

Actualmente tengo:

- Un servicio **CLI** en Python que se comunica con un **MCP Server**.
- Ese CLI utiliza **Gemini** como modelo para generar respuestas.
- Toda la lógica de conversación y llamadas al MCP está dentro del CLI.

**Objetivo:**  
Agregar **Telegram** como canal adicional **sin duplicar lógica** y manteniendo una arquitectura simple.

---

### Requerimientos

1. Reorganizar la aplicación para tener un **núcleo central de conversación** (por ejemplo una clase `ChatCore`) que:
   - Reciba el mensaje del usuario.
   - Mantenga o referencie el contexto por sesión.
   - Llame a Gemini.
   - Llame al MCP Server cuando corresponda.
   - Devuelva una respuesta en texto.

2. Crear **adaptadores** (o interfaces) para cada canal:
   - CLI (ya existe → solo modificar para usar `ChatCore`)
   - Telegram Bot (usando `python-telegram-bot`)

3. Cada canal debe únicamente:
   - Recibir input del usuario.
   - Pasar mensaje y `session_id` a `ChatCore`.
   - Enviar la respuesta de vuelta al usuario.

4. La lógica de negocio **no** debe estar ni en el CLI ni en el bot.
   Todo debe estar encapsulado en `ChatCore`.

---

### Lo que necesito que generes

- Un **diagrama simple de arquitectura** que muestre `ChatCore` y los adaptadores.
- Código base en Python que incluya:
  - `ChatCore`
  - Un `mcp_client` (puede ser mock o interfaz para luego implementar)
  - Adaptador para CLI
  - Adaptador para Telegram (`python-telegram-bot`)

- Explicación breve de **cómo agregar un tercer canal** en el futuro (ej: web UI, Discord, Slack, WhatsApp).

---

### Estilo del resultado

- Claro y directo.
- Código funcional y ejecutable.
- Evitar sobre-ingeniería.


# Referencias 
**CLI**  = client_mcp
**MCP Server** = mcp_server
