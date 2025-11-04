# Booking Agent Issue - Code Locations Reference

## File Locations

### Primary Files

```
/home/javort/alfredo/MCP-Server/
├── agent/src/multi_agent/
│   ├── booking_agent.py ⭐ (MAIN - 846 lines)
│   ├── agent_router.py (917 lines)
│   └── prompt_manager.py
├── agent/src/gemini_agent/
│   ├── base_agent.py (base class)
│   └── config/booking_agent_settings.py (settings)
├── client_mcp/core/
│   ├── function_call_handler.py (response parsing)
│   └── conversation_manager.py
└── mcp_server/mcp_handlers/
    └── booking_handlers.py (tool definitions)
```

---

## Exact Line References

### 1. Response Schema Definition

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 118-169

```python
118 BOOKING_RESPONSE_SCHEMA = types.Schema(
119     type="object",
120     properties={
121         "intent": types.Schema(
122             type="string",
123             enum=[
124                 "create_booking",
125                 "cancel_booking",
...
169     required=["intent", "confidence", "response_text"],
170 )
```

**What it does**: Defines structured output schema for booking responses (NOT used when tools present).

---

### 2. MCP Tools Autodiscovery

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 44-81

```python
44  # Try to import autodiscovered booking tools
45  try:
56      from mcp_handlers.booking_handlers import get_booking_tool_names
57      BOOKING_TOOLS_ALLOWED = set(get_booking_tool_names())
58      _logger.info(f"✅ Autodiscovered {len(BOOKING_TOOLS_ALLOWED)} booking tools")
...
63  except ImportError as e:
64      _logger.warning(f"⚠️ Could not autodiscover...")
65      # Fallback: Hardcoded list (8 booking tools)
72      BOOKING_TOOLS_ALLOWED = {
73          "create_booking",
74          "cancel_booking",
75          "reschedule_booking",
76          "get_available_slots",
77          "get_booking_by_id",
78          "list_customer_bookings",
79          "get_services",
80          "get_business_hours",
81      }
```

**What it does**: Loads 8 booking tools either dynamically (autodiscover) or falls back to hardcoded list.

---

### 3. CRITICAL FIX #1: Conditional Schema (Lines 428-442)

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 428-442

```python
428             # CRITICAL FIX: Only add response_schema if NO tools are available
429             # When tools are present, response_schema conflicts with function_calling:
430             # - response_schema forces Gemini to return structured JSON
431             # - function_calling expects Gemini to return function_call parts
432             # - These are mutually exclusive → response.parts becomes None
433             # Solution: Use response_schema ONLY for text-only responses (no tools)
434             if not self.mcp_tools:
435                 config_dict["response_schema"] = BOOKING_RESPONSE_SCHEMA
436                 self.logger.info(
437                     "✅ Structured output enabled: BOOKING_RESPONSE_SCHEMA with intent detection"
438                 )
439             else:
440                 self.logger.info(
441                     "⏭️ Skipping response_schema (tools present): Let Gemini choose function calls naturally"
442                 )
```

**Why it matters**: This prevents the conflict. Schema is ONLY added when no tools are present.

---

### 4. Tool Configuration (Lines 444-477)

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 444-477

```python
444             # Add tools and tool config if available
445             # Implements Gemini 2.5 Function Calling Best Practices
446             if self.mcp_tools:
447                 # Validate tools are in allowed booking tools (scope limiting)
448                 tool_names = {func.name for func in self.mcp_tools}
449                 invalid_tools = tool_names - BOOKING_TOOLS_ALLOWED
450                 if invalid_tools:
451                     self.logger.warning(
452                         f"⚠️ Invalid tools: {invalid_tools}"
453                     )
...
459                 config_dict["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
460                 config_dict["tool_config"] = types.ToolConfig(
461                     function_calling_config=types.FunctionCallingConfig(
462                         mode=types.FunctionCallingConfigMode.AUTO,
463                     )
464                 )
...
475                 self.logger.info(
476                     f"✅ Function calling configured: AUTO mode with {len(self.mcp_tools)} booking tools"
477                 )
```

**What it does**: Adds tool declarations and function calling config (AUTO mode = model decides when to call).

---

### 5. CRITICAL FIX #2: Two-Config Workaround (Lines 479-495)

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 479-495

```python
479             # CRITICAL FIX: Avoid conflict between response_schema and function_calling_loop
480             # Google Gemini API returns 500 INTERNAL when response_schema is used in
481             # subsequent calls within a function calling loop. Solution: create two configs:
482             # 1. initial_config: WITH response_schema (for first call, intent detection)
483             # 2. loop_config: WITHOUT response_schema (for function calling loop iterations)
484
485             initial_config = types.GenerateContentConfig(**config_dict)
486
487             # For function calling loop: remove response_schema to avoid API conflicts
488             loop_config_dict = config_dict.copy()
489             loop_config_dict.pop("response_schema", None)
490             loop_config = types.GenerateContentConfig(**loop_config_dict)
491
492             self.logger.debug(
493                 "📋 Created two configs: initial_config (WITH schema), loop_config (WITHOUT schema)"
494             )
```

**Why it matters**: Prevents 500 errors in function calling loop iterations.

---

### 6. Initial Gemini Call (Lines 498-526)

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 498-526

```python
498             # Generate initial response with system_instruction in config
499             # (uses response_schema for intent detection)
500             response = await self.client.aio.models.generate_content(
501                 model=self.model_name,
502                 contents=contents,
503                 config=initial_config,
504             )
...
505             # DEBUG: Log response details for diagnosis
506             self.logger.debug(f"Response type: {type(response).__name__}")
507             self.logger.debug(f"Has candidates: {hasattr(response, 'candidates')}")
508             if hasattr(response, "candidates") and response.candidates:
509                 candidate = response.candidates[0]
510                 self.logger.debug(f"Candidates count: {len(response.candidates)}")
511                 self.logger.debug(f"Candidate.content: {candidate.content}")
...
520                 if candidate.content is None:
521                     self.logger.error(
522                         f"🚨 Gemini returned content=None!"
523                     )
```

**What happens**: Initial response generated. May have `parts = None` on first request (the bug).

---

### 7. CRITICAL FIX #3: Function Calling Loop with Fallback (Lines 528-665)

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 528-665

Key section (Lines 598-620):

```python
598             # Get parts from response
599             parts = self.function_call_handler.get_parts(response)
600
601             # If parts is None, try to extract text directly from content as fallback
602             if parts is None:
603                 self.logger.warning("Response parts is None - trying direct content extraction")
604                 # Log diagnostic information about response structure
605                 if response.candidates:
606                     candidate = response.candidates[0]
607                     self.logger.debug(
608                         f"Response diagnostic - candidate.content: {candidate.content}, "
609                         f"finish_reason: {candidate.finish_reason}"
610                     )
611                 try:
612                     content = response.candidates[0].content if response.candidates else None
613                     text = self.function_call_handler.extract_text_from_content(content)
614                     if text:
615                         self.logger.debug(f"Extracted text from content: {text[:100]}...")
616                         return text
617                 except (AttributeError, IndexError) as e:
618                     self.logger.warning(f"Failed to extract text from content: {e}")
619                 self.logger.info(f"Using fallback response for iteration {iteration}")
620                 return self._create_fallback_response(iteration)
```

**What it does**: If `get_parts()` returns None, tries to extract text directly. If that fails, returns fallback.

---

### 8. Fallback Response (Lines 823-836)

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 823-836

```python
823     def _create_fallback_response(self, iteration: int) -> str:
824         """Create fallback response when iteration fails.
825
826         Args:
827             iteration: Current iteration number.
828
829         Returns:
830             Generic fallback response. Specific options should come from template.
831         """
832         # Fallback to generic message - template should handle specific options
833         return (
834             "No pude procesar tu solicitud completamente en esta iteración. "
835             "Por favor, intenta reformular tu pregunta con más detalles."
836         )
```

**What it does**: Returns generic error message when all extraction methods fail. This is what users see on first vague query.

---

## Supporting Code

### Function Call Handler: get_parts()

**File**: `client_mcp/core/function_call_handler.py`
**Lines**: 112-142

```python
112     def get_parts(self, response: Any) -> list[types.Part] | None:
113         """Get parts from response.
114
115         Args:
116             response: Gemini API response
117
118         Returns:
119             Parts list or None if not available
120         """
121         if not self.has_candidates(response):
122             return None
123
124         # Defensive check: content can be None
125         content = response.candidates[0].content
126         if content is None or not hasattr(content, "parts"):
127             logger.warning("Response content is None or missing parts")
128             return None  # ← RETURNS None HERE
129
130         parts = content.parts
131
132         # Handle case where parts is empty or None
133         if parts is None or len(parts) == 0:
134             logger.debug("Response parts is empty")
135             if hasattr(content, "text") and content.text:
136                 logger.debug("Found text content directly")
137                 return []  # Returns EMPTY list
138             return None  # ← OR RETURNS None HERE
139
140         return parts
```

**Critical**: Lines 128 and 138 can return None, triggering fallback.

---

### Conversation History (Why Second Request Works)

**File**: `agent/src/gemini_agent/base_agent.py`
**Lines**: 160-170

```python
160         # Conversation state
161         self.conversation_history: list[types.Content] = []
```

**File**: `agent/src/multi_agent/booking_agent.py`
**Lines**: 539-543

```python
539             # Update history if requested
540             if include_history:
541                 self._update_history(
542                     contents[-1],
543                     types.Content(role="model", parts=[types.Part(text=final_text)]),
544                 )
```

**What it does**: Saves response to history. Next request includes full history, providing context.

---

### Agent Router: Intent Classification

**File**: `agent/src/multi_agent/agent_router.py`
**Lines**: 487-713

```python
487     async def classify_intent(
488         self,
489         query: str,
490         *,
491         context: dict[str, Any] | None = None,
492         persist_intent: bool = True,
493         session_language: str | None = None,
494     ) -> Intent:
```

**What it does**: Classifies user query as SALES, BOOKING, or GENERAL. Routes to appropriate agent.

---

## Configuration Files

### Booking Agent Settings

**File**: `agent/src/gemini_agent/config/booking_agent_settings.py`

Key settings:
- `BOOKING_MAX_FUNCTION_CALL_ITERATIONS`: Max loop iterations (default: 10)
- `TOKEN_ESTIMATE_RATIO`: Tokens per character (default: 0.25)
- `BOOKING_MAX_PROMPT_SIZE_CHARS`: Warning threshold (default: 30,000)
- `BOOKING_MAX_CONTENT_SIZE_CHARS`: Warning threshold (default: 100,000)

---

## Summary: The Chain of Events

```
1. User says "quiero reservar"
   ↓ agent_router.py:495 classify_intent()
2. Returns Intent.BOOKING
   ↓ booking_agent.py:314 generate_response()
3. Check if tools present → YES (8 booking tools)
   ↓ booking_agent.py:434 if not self.mcp_tools
4. Skip response_schema (to avoid conflict)
   ↓ booking_agent.py:500 call Gemini
5. Gemini returns response with parts=None or empty
   ↓ booking_agent.py:599 function_call_handler.get_parts()
6. Returns None, triggering fallback
   ↓ booking_agent.py:602 if parts is None
7. Try extract_text_from_content() → fails
   ↓ booking_agent.py:823 _create_fallback_response()
8. Return: "No pude procesar tu solicitud..."
   ↓ booking_agent.py:541-543 save to history
9. Next request: History has previous response
   ↓ booking_agent.py:393 _build_contents() includes history
10. Gemini now understands context → returns function_call
    ↓ booking_agent.py:599 get_parts() returns function_call
11. Execute get_services() → SUCCESS
    ↓ Show booking options
```

---

**Quick Navigation**:
- **Quick Summary**: See `BOOKING_AGENT_QUICK_SUMMARY.md`
- **Full Analysis**: See `BOOKING_AGENT_RESPONSE_PARTS_ANALYSIS.md`
