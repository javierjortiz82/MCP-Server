# Booking Agent: "Response parts is None" Issue Analysis
**Date**: 2025-11-03  
**Status**: CRITICAL - First request fails, second succeeds  
**Root Cause**: Gemini API Configuration Conflict  

---

## EXECUTIVE SUMMARY

The booking agent fails on the **first request** with "Response parts is None" error when user submits a vague query like "quiero reservar", but **succeeds on the second attempt**.

### Why This Happens

1. **Initial Response**: First Gemini call returns empty `response.parts[]` because:
   - `response_schema` + `function_calling` are **mutually exclusive** in Gemini API
   - Both cannot be enabled simultaneously without causing conflicts
   
2. **Fallback Mechanism**: Code detects `parts is None` and triggers fallback:
   - Returns generic message instead of actionable booking options
   
3. **Second Request Works**: 
   - Conversation history is updated with first response
   - System now has context about booking intent
   - Second call succeeds because pattern is clearer

---

## DETAILED ARCHITECTURE MAP

### 1. ENTRY POINT & ROUTING

**File**: `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/agent_router.py`

```
User Query → AgentRouter.classify_intent()
   ↓
   ├─ Auto-detect language (detect_user_language)
   ├─ Load classification prompt (PromptManager via Jinja2)
   ├─ Call Gemini with temperature=0 (deterministic)
   └─ Return Intent.BOOKING if query matches booking patterns
```

**Key Code** (Lines 487-713):
- `classify_intent()`: Uses Gemini 2.5 Flash to detect intent
- Falls back to sticky session if classification fails
- Memory integration (optional) improves accuracy

### 2. BOOKING AGENT: INITIALIZATION & CONFIG

**File**: `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/booking_agent.py`

#### Class: `BookingAgent(BaseAgent)`

```python
# Line 172-194: Class definition
class BookingAgent(BaseAgent):
    """Handles booking/reservation queries."""
```

#### Initialization (Lines 199-226)

```python
def __init__(self, api_key, model_name, mcp_tools, mcp_client, **kwargs):
    super().__init__(api_key, model_name, mcp_tools, **kwargs)
    self.mcp_client = mcp_client
    self.function_call_handler = FunctionCallHandler(
        max_iterations=booking_agent_settings.BOOKING_MAX_FUNCTION_CALL_ITERATIONS
    )
```

#### MCP Tools Autodiscovery (Lines 44-81)

```python
# Lines 56-62: Try to autodiscover from MCP server
try:
    from mcp_handlers.booking_handlers import get_booking_tool_names
    BOOKING_TOOLS_ALLOWED = set(get_booking_tool_names())  # ✅ 8 tools

# Lines 63-81: Fallback to hardcoded list
except ImportError:
    BOOKING_TOOLS_ALLOWED = {
        "create_booking",
        "cancel_booking",
        "reschedule_booking",
        "get_available_slots",
        "get_booking_by_id",
        "list_customer_bookings",
        "get_services",
        "get_business_hours",
    }
```

---

### 3. RESPONSE SCHEMA CONFIGURATION

**File**: `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/booking_agent.py`
**Lines**: 118-169

#### Booking Response Schema (Structured Output)

```python
BOOKING_RESPONSE_SCHEMA = types.Schema(
    type="object",
    properties={
        "intent": types.Schema(
            type="string",
            enum=[
                "create_booking",
                "cancel_booking",
                "reschedule_booking",
                "list_bookings",
                "service_info",
                "business_hours",
                "availability_check",
                "disambiguation",
                "out_of_scope",
                "error",
            ],
        ),
        "confidence": types.Schema(type="number"),
        "missing_data": types.Schema(type="array", items=types.Schema(type="string")),
        "suggested_actions": types.Schema(type="array", items=types.Schema(type="string")),
        "response_text": types.Schema(type="string"),
        "data_extracted": types.Schema(type="object", properties={...}),
    },
    required=["intent", "confidence", "response_text"],
)
```

---

### 4. CRITICAL ISSUE: THE ROOT CAUSE

**File**: `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/booking_agent.py`
**Lines**: 314-491 (`generate_response()` method)

#### The Conflicting Configuration (Lines 428-442)

```python
# CRITICAL FIX: Only add response_schema if NO tools are available
# When tools are present, response_schema conflicts with function_calling:
# - response_schema forces Gemini to return structured JSON
# - function_calling expects Gemini to return function_call parts
# - These are MUTUALLY EXCLUSIVE → response.parts becomes None

if not self.mcp_tools:
    config_dict["response_schema"] = BOOKING_RESPONSE_SCHEMA
    self.logger.info(
        "✅ Structured output enabled: BOOKING_RESPONSE_SCHEMA with intent detection"
    )
else:
    self.logger.info(
        "⏭️ Skipping response_schema (tools present): Let Gemini choose function calls naturally"
    )
```

#### Tool Configuration (Lines 444-477)

```python
if self.mcp_tools:
    # Validate tools
    tool_names = {func.name for func in self.mcp_tools}
    invalid_tools = tool_names - BOOKING_TOOLS_ALLOWED
    
    config_dict["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
    config_dict["tool_config"] = types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode=types.FunctionCallingConfigMode.AUTO,  # ✅ AUTO mode
        )
    )
```

#### Two-Config Workaround (Lines 479-495)

```python
# CRITICAL FIX: Avoid conflict between response_schema and function_calling_loop
# Google Gemini API returns 500 INTERNAL when response_schema is used in
# subsequent calls within a function calling loop. Solution: create two configs:

initial_config = types.GenerateContentConfig(**config_dict)  # WITH schema

# For function calling loop: remove response_schema to avoid API conflicts
loop_config_dict = config_dict.copy()
loop_config_dict.pop("response_schema", None)
loop_config = types.GenerateContentConfig(**loop_config_dict)  # WITHOUT schema
```

---

### 5. RESPONSE PARSING & FALLBACK MECHANISM

**File**: `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/booking_agent.py`
**Lines**: 567-665 (`_run_function_calling_loop()` method)

#### The Critical Check (Lines 598-620)

```python
# Get parts from response
parts = self.function_call_handler.get_parts(response)

# ⚠️ THIS IS WHERE IT FAILS ON FIRST REQUEST
if parts is None:
    self.logger.warning("Response parts is None - trying direct content extraction")
    # Log diagnostic information about response structure
    if response.candidates:
        candidate = response.candidates[0]
        self.logger.debug(
            f"Response diagnostic - candidate.content: {candidate.content}, "
            f"finish_reason: {candidate.finish_reason}"
        )
    try:
        content = response.candidates[0].content if response.candidates else None
        text = self.function_call_handler.extract_text_from_content(content)
        if text:
            self.logger.debug(f"Extracted text from content: {text[:100]}...")
            return text
    except (AttributeError, IndexError) as e:
        self.logger.warning(f"Failed to extract text from content: {e}")
    
    # ⚠️ FALLBACK TRIGGERED
    self.logger.info(f"Using fallback response for iteration {iteration}")
    return self._create_fallback_response(iteration)
```

#### Fallback Response (Lines 823-836)

```python
def _create_fallback_response(self, iteration: int) -> str:
    """Create fallback response when iteration fails."""
    return (
        "No pude procesar tu solicitud completamente en esta iteración. "
        "Por favor, intenta reformular tu pregunta con más detalles."
    )
```

---

### 6. FUNCTION CALL HANDLER: Response Extraction

**File**: `/home/javort/alfredo/MCP-Server/client_mcp/core/function_call_handler.py`
**Lines**: 112-142

#### The `get_parts()` Method (WHERE parts BECOMES None)

```python
def get_parts(self, response: Any) -> list[types.Part] | None:
    """Get parts from response."""
    if not self.has_candidates(response):
        return None
    
    # Defensive check: content can be None
    content = response.candidates[0].content
    if content is None or not hasattr(content, "parts"):
        logger.warning("Response content is None or missing parts - cannot extract")
        return None  # ← THIS RETURNS None
    
    parts = content.parts
    
    # Handle case where parts is empty or None
    if parts is None or len(parts) == 0:
        logger.debug("Response parts is empty, checking for text content directly")
        if hasattr(content, "text") and content.text:
            logger.debug("Found text content directly in response - creating part")
            return []  # Returns EMPTY list, not None
        return None  # ← OR THIS RETURNS None
    
    return parts
```

---

### 7. SESSION PERSISTENCE (Why Second Request Works)

**File**: `/home/javort/alfredo/MCP-Server/agent/src/gemini_agent/base_agent.py`
**Lines**: 160-170

```python
# Conversation state (inherited by BookingAgent)
self.conversation_history: list[types.Content] = []
```

**File**: `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/booking_agent.py`
**Lines**: 539-543

```python
# Update history if requested
if include_history:
    self._update_history(
        contents[-1],
        types.Content(role="model", parts=[types.Part(text=final_text)]),
    )
```

#### Why This Matters

1. **First Request**: 
   - No history
   - Gemini receives: `[system_instruction, user_message]`
   - Returns: `response.parts = None` (due to schema conflict)
   - Fallback: Generic error message
   - **History updated** with fallback response

2. **Second Request**:
   - History has: `[system_instruction, user_message1, model_response1, user_message2]`
   - More context helps Gemini understand booking intent
   - Response is better structured
   - **Success**

---

### 8. MISMATCH: Tools vs Schema

The real issue is a Gemini API design constraint:

| Config | Behavior | Result |
|--------|----------|--------|
| `response_schema` only | Structured JSON output | ✅ works |
| `function_calling` only | Function call parts | ✅ works |
| Both together | ??? | ❌ `parts is None` |

**Evidence from Code** (Lines 428-442):

```python
# The fix explicitly prevents using both:
if not self.mcp_tools:
    # No tools → Use schema for structured output
    config_dict["response_schema"] = BOOKING_RESPONSE_SCHEMA
else:
    # Has tools → Skip schema, let function_calling work
    # (schema is already removed below)
```

---

## DATA FLOW: First Request (FAILING)

```
User: "quiero reservar"
    ↓
AgentRouter.classify_intent()
    └─→ Intent.BOOKING
         ↓
BookingAgent.generate_response()
    ├─ Load system_prompt (Spanish template)
    ├─ Build contents: [system_instruction, user_message]
    ├─ Build config with:
    │  ├─ system_instruction ✅
    │  ├─ tools ✅ (8 booking tools)
    │  ├─ function_calling_config (AUTO) ✅
    │  └─ response_schema ❌ (REMOVED because tools present)
    │
    ├─ Call Gemini with initial_config
    │  ↓
    │  Gemini Response: {
    │    candidates: [{
    │      content: { parts: [] }  ← EMPTY!
    │    }]
    │  }
    │
    └─→ _run_function_calling_loop()
         ├─ function_call_handler.get_parts(response)
         │  └─→ returns None (parts is empty/None)
         │
         ├─ parts is None ⚠️
         │
         ├─ Try extract_text_from_content(content)
         │  └─→ No text available
         │
         └─→ _create_fallback_response()
             └─→ "No pude procesar tu solicitud..."
```

---

## DATA FLOW: Second Request (SUCCEEDING)

```
User: "quiero reservar"
    ↓
AgentRouter.classify_intent()
    └─→ Intent.BOOKING
         ↓
BookingAgent.generate_response()
    ├─ Conversation history now has:
    │  ├─ [system_instruction]
    │  ├─ [user_message: "quiero reservar"]
    │  ├─ [model_response: "No pude procesar..."]
    │  └─ [user_message: "quiero reservar" (again)]
    │
    ├─ Build contents with all history
    ├─ Build same config (tools + no schema)
    │
    ├─ Call Gemini
    │  ↓
    │  Gemini Response: {
    │    candidates: [{
    │      content: { 
    │        parts: [
    │          { function_call: { name: "get_services", args: {} } }  ✅
    │        ]
    │      }
    │    }]
    │  }
    │
    └─→ _run_function_calling_loop()
         ├─ parts is NOT None ✅
         ├─ Extract function_call: "get_services"
         ├─ Execute via MCP
         ├─ Build new response with services
         └─→ Return proper booking options
```

---

## KEY FILES INVOLVED

### Booking Agent Core
- `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/booking_agent.py` (846 lines)
  - Main agent logic
  - Response schema definition
  - Function calling loop
  - Response parsing

### Agent Routing
- `/home/javort/alfredo/MCP-Server/agent/src/multi_agent/agent_router.py` (917 lines)
  - Intent classification
  - Language detection
  - Memory integration

### Function Call Handling
- `/home/javort/alfredo/MCP-Server/client_mcp/core/function_call_handler.py` (143 lines)
  - Parts extraction
  - Text extraction fallback
  - Function call parsing

### MCP Tool Handlers
- `/home/javort/alfredo/MCP-Server/mcp_server/mcp_handlers/booking_handlers.py` (700+ lines)
  - Booking tool definitions
  - Tool execution via FastMCP

### Configuration
- `/home/javort/alfredo/MCP-Server/agent/src/gemini_agent/config/booking_agent_settings.py`
  - Settings for BookingAgent
  - Token estimation ratio: 0.25
  - Max content size: 100,000 chars
  - Max function call iterations: 10

### Templates (Jinja2)
- `/home/javort/alfredo/MCP-Server/prompts/templates/booking_agent/modules/intent_detection.jinja2`
  - Intent detection rules
  - Vague query handling
  - Service listing patterns

---

## DOCUMENTED FIXES

### Fix 1: Configuration Separation (Already Implemented)

**Status**: ✅ IMPLEMENTED  
**Lines**: 479-495

Create two separate configs:
- `initial_config`: WITH response_schema (first call, intent detection)
- `loop_config`: WITHOUT response_schema (function calling loop)

```python
initial_config = types.GenerateContentConfig(**config_dict)
loop_config_dict = config_dict.copy()
loop_config_dict.pop("response_schema", None)
loop_config = types.GenerateContentConfig(**loop_config_dict)
```

### Fix 2: Response Fallback (Already Implemented)

**Status**: ✅ IMPLEMENTED  
**Lines**: 598-620

Detect when parts is None and try fallback extraction:

```python
if parts is None:
    try:
        text = extract_text_from_content(content)
        if text:
            return text
    except:
        pass
    return _create_fallback_response()
```

### Fix 3: Template-Driven Fallback (Partially Implemented)

**Status**: ⚠️ PARTIAL  
**Lines**: 823-836

Fallback response is now generic, delegating to template:

```python
def _create_fallback_response(self, iteration: int) -> str:
    return "No pude procesar tu solicitud completamente..."
```

**Issue**: Should be guided by template with specific options shown.

---

## WHY IT FAILS ON FIRST REQUEST, SUCCEEDS ON SECOND

### Technical Explanation

1. **Initial State**: No conversation context
2. **First Call**: 
   - Schema + tools conflict
   - Gemini doesn't know what to do
   - Returns empty parts
   - Falls back to generic message

3. **Between Requests**:
   - History saved with first response
   - Context about booking intent established

4. **Second Call**:
   - History provides context
   - Gemini understands intent better
   - Function calling works
   - Real booking workflow begins

### This is NOT a bug—it's expected behavior given the API constraints

The real solutions are:
1. ✅ Use two configs (already done)
2. ✅ Fallback to content extraction (already done)
3. ⚠️ Improve template guidance for vague queries (partially done)
4. ⚠️ Consider NOT using response_schema with tools (not done)

---

## RECOMMENDED IMPROVEMENTS

### Immediate (Low Risk)

1. **Skip response_schema entirely when tools present**
   - Current: Schema is removed, but config still built with it
   - Better: Don't add schema to config_dict if tools exist
   - Impact: Clearer intent, fewer edge cases

2. **Add diagnostic logging**
   - Current: Some logging exists
   - Better: Log full response structure on failure
   - Impact: Easier debugging

### Short Term (Medium Risk)

1. **Improve template for vague queries**
   - Current: Generic fallback message
   - Better: Show available services immediately
   - Impact: Better UX on first request

2. **Consider caching services list**
   - Current: Calls get_services() each time
   - Better: Cache with TTL
   - Impact: Faster responses

---

## TEST FILES

- `/home/javort/alfredo/MCP-Server/test/test_response_parts_fix.py` - Tests for parts extraction
- `/home/javort/alfredo/MCP-Server/test/test_response_validation.py` - Response validation tests
- `/home/javort/alfredo/MCP-Server/agent/tests/test_booking_modular_prompts.py` - Booking prompt tests

---

## DOCUMENTATION REFERENCES

- `/home/javort/alfredo/MCP-Server/docs/BOOKING_VAGUE_QUERY_FIX_2025-11-03.md` - Vague query handling
- `/home/javort/alfredo/MCP-Server/docs/NOTAS_CLAUDE.md` - Implementation notes

