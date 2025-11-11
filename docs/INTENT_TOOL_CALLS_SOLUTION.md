# Intent & Tool_Calls Storage - Root Cause Analysis & Solutions

**Date:** 2025-11-09
**Status:** IDENTIFIED - Solutions Ready to Implement

---

## 🔍 Problem Summary

Despite working correctly at runtime, two critical fields are NOT being stored in the database:

### Problem 1: `intent` Column Always NULL
```sql
SELECT intent, COUNT(*) FROM test.conversation_messages GROUP BY intent;
-- Result: All NULL despite "Intent classified: booking" in logs
```

### Problem 2: `tool_calls` Column Always NULL
```sql
SELECT tool_calls, COUNT(*) FROM test.conversation_messages WHERE tool_calls IS NOT NULL;
-- Result: 0 rows despite "🔧 Executing: get_services({})" in logs
```

---

## 🧩 Root Cause Analysis

### Intent Issue

**Current Flow:**
1. ✅ `AgentRouter.classify()` detects intent: `Intent.BOOKING`
2. ✅ `AgentOrchestrator._process_multi_agent()` uses intent for routing
3. ❌ **Intent is NEVER passed to BookingAgent**
4. ❌ BookingAgent calls `save_message(intent=None)` ← **HARDCODED NULL**

**Code Evidence:**

**File:** `agent/src/gemini_agent/base_agent.py:1428-1437`
```python
# Save user message
self.memory_manager.save_message(
    session_id=self.session_id,
    role="user",
    message_text=user_text,
    intent=None,  # ❌ ALWAYS None - not receiving from router
)

# Save model message
self.memory_manager.save_message(
    ...
    intent=None,  # ❌ ALWAYS None
)
```

**Why:**
- Intent classification happens in `AgentOrchestrator`
- Agents are called via `await agent.generate_response(query, ...)`
- `generate_response()` **does NOT accept `intent` parameter**
- BaseAgent has no way to know what intent was classified

---

### Tool_Calls Issue

**Current Flow:**
1. ✅ `BookingAgent._run_function_calling_loop()` executes tools
2. ✅ `get_services({})` called successfully via MCP
3. ✅ Function response added to `contents` array
4. ❌ **`_extract_tool_calls()` called AFTER loop completes**
5. ❌ At that point, `response.content.parts` only contains final TEXT, not function_call parts

**Code Evidence:**

**File:** `agent/src/multi_agent/booking_agent.py:577-590`
```python
# Run function calling loop
final_text = await self._run_function_calling_loop(response, contents, loop_config)

# Calculate elapsed time
elapsed_ms = int((time.time() - start_time) * 1000)

# Extract tool calls from response (for analytics)
tool_calls = self._extract_tool_calls(
    types.Content(role="model", parts=[types.Part(text=final_text)])
)  # ❌ WRONG! final_text is just text, not function_call parts
```

**Why:**
- `final_text` is the **final text response** after all tool calls are processed
- Function calling loop **replaces** function_call parts with text responses
- `_extract_tool_calls()` looks for `part.function_call` but only finds `part.text`

---

## ✅ Solution 1: Pass Intent to Agents

### Option A: Add intent parameter to generate_response() (RECOMMENDED)

**Pros:**
- Clean API
- Explicit intent passing
- Easy to implement

**Changes Required:**

**1. Update BaseAgent.generate_response() signature:**
```python
async def generate_response(
    self,
    query: str,
    *,
    include_history: bool = True,
    intent: str | None = None,  # ✅ NEW
    **kwargs: Any,
) -> str:
```

**2. Store intent in instance variable:**
```python
def generate_response(self, query, *, intent=None, **kwargs):
    self.current_intent = intent  # Store for _update_history()
    ...
```

**3. Use in _update_history():**
```python
def _update_history(self, user_content, model_content, ...):
    ...
    self.memory_manager.save_message(
        ...
        intent=self.current_intent,  # ✅ Use stored intent
    )
```

**4. Update AgentOrchestrator routing:**
```python
# In _route_to_booking()
response = await self.booking_agent.generate_response(
    query,
    customer_email=customer_email,
    intent="booking",  # ✅ Pass classified intent
    **kwargs
)
```

### Option B: Use kwargs['intent']

**Changes:**
```python
# AgentOrchestrator
await agent.generate_response(query, intent="booking", **kwargs)

# BaseAgent
def generate_response(self, query, **kwargs):
    intent = kwargs.get("intent", None)
    # Store in self.current_intent for later use
```

---

## ✅ Solution 2: Track Tool Calls During Loop

### Option A: Modify _run_function_calling_loop() to return tool_calls (RECOMMENDED)

**Changes Required:**

**1. Track tool calls during loop:**

**File:** `agent/src/multi_agent/booking_agent.py:643+`
```python
async def _run_function_calling_loop(self, response, contents, config):
    tool_calls_log = []  # ✅ NEW: Track all tool calls
    iteration = 0

    while iteration < max_iterations:
        ...
        # Check for function calls
        function_calls = self.function_call_handler.get_function_calls(parts)

        if function_calls:
            for fc in function_calls:
                # ✅ LOG each tool call
                tool_calls_log.append({
                    "tool_name": fc.name,
                    "args": dict(fc.args) if fc.args else {},
                })

                # Execute function
                result = await self.function_call_handler.call_function(...)
                ...
        else:
            # No more function calls - return text
            text = self.function_call_handler.extract_text_from_content(...)
            return text, tool_calls_log  # ✅ Return both text AND tools

    return final_text, tool_calls_log  # ✅ Return tuple
```

**2. Update caller to receive tool_calls:**

**File:** `agent/src/multi_agent/booking_agent.py:577`
```python
# BEFORE:
final_text = await self._run_function_calling_loop(response, contents, loop_config)

# AFTER:
final_text, tool_calls_from_loop = await self._run_function_calling_loop(
    response, contents, loop_config
)

# Use tool_calls_from_loop instead of _extract_tool_calls()
tool_calls = tool_calls_from_loop if tool_calls_from_loop else None
```

**3. Remove ineffective _extract_tool_calls() call:**
```python
# DELETE THIS (doesn't work after loop completes):
# tool_calls = self._extract_tool_calls(...)
```

---

### Option B: Store tool_calls in instance variable

**Changes:**
```python
class BookingAgent(BaseAgent):
    def __init__(self, ...):
        ...
        self.current_tool_calls = []  # Track for current request

    async def _run_function_calling_loop(self, ...):
        self.current_tool_calls = []  # Reset
        ...
        for fc in function_calls:
            self.current_tool_calls.append({
                "tool_name": fc.name,
                "args": dict(fc.args),
            })
        ...

    async def generate_response(self, ...):
        ...
        await self._run_function_calling_loop(...)
        tool_calls = self.current_tool_calls if self.current_tool_calls else None
```

---

## 📊 Expected Results After Implementation

### Database State - BEFORE:
```sql
SELECT agent_name, intent, tool_calls
FROM test.conversation_messages
WHERE role = 'model'
LIMIT 5;

 agent_name    | intent | tool_calls
---------------+--------+------------
 booking_agent | NULL   | NULL       ❌
 sales_agent   | NULL   | NULL       ❌
```

### Database State - AFTER:
```sql
 agent_name    | intent   | tool_calls
---------------+----------+----------------------------------------------------------
 booking_agent | booking  | [{"tool_name": "get_services", "args": {}}]            ✅
 sales_agent   | sales    | [{"tool_name": "fuzzy_search_smart", "args": {...}}]   ✅
 general_agent | general  | NULL                                                    ✅
```

---

## 🎯 Implementation Priority

### HIGH PRIORITY (Implement Now):
1. ✅ **Intent passing** - Straightforward, high value for analytics
2. ✅ **Tool calls tracking** - Critical for debugging and monitoring

### Implementation Order:
1. **Intent First** (easier, less code changes)
   - Add `intent` parameter to `generate_response()`
   - Update all routing calls in `AgentOrchestrator`
   - Test with booking/sales/general queries

2. **Tool Calls Second** (more complex)
   - Modify `_run_function_calling_loop()` to return tuple
   - Update callers to unpack tuple
   - Test with queries that trigger tools

---

## 🧪 Testing Plan

### Test 1: Intent Storage
```bash
# Send queries for each intent
python -m client_mcp
> quiero reservar              # Should store intent='booking'
> quiero comprar zapatos       # Should store intent='sales'
> cuales son los horarios      # Should store intent='general'

# Verify
docker exec -e PGUSER=mcp_user mcp-postgres psql -d mcpdb -c "
SELECT agent_name, intent, COUNT(*)
FROM test.conversation_messages
WHERE role = 'model'
GROUP BY agent_name, intent;
"
```

### Test 2: Tool Calls Storage
```bash
# Send queries that trigger tools
> quiero reservar                    # Triggers get_services()
> busco laptop gaming                # Triggers fuzzy_search_smart()

# Verify
docker exec -e PGUSER=mcp_user mcp-postgres psql -d mcpdb -c "
SELECT agent_name, tool_calls
FROM test.conversation_messages
WHERE tool_calls IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;
"
```

---

## 📝 Files to Modify

### Intent Implementation:
1. `agent/src/gemini_agent/base_agent.py` - Add intent parameter
2. `agent/src/multi_agent/booking_agent.py` - Pass through intent
3. `agent/src/multi_agent/sales_agent.py` - Pass through intent (if overrides)
4. `client_mcp/core/agent_orchestrator.py` - Pass intent to agents

### Tool Calls Implementation:
1. `agent/src/multi_agent/booking_agent.py` - Track tools in loop, return tuple
2. `agent/src/multi_agent/sales_agent.py` - Same (if has function calling loop)
3. `agent/src/gemini_agent/base_agent.py` - Remove/fix _extract_tool_calls() usage

---

## ⚠️ Known Limitations

1. **demo_agent** doesn't use BaseAgent - needs separate implementation for intent
2. **Tool execution time** not tracked (only tool name + args)
3. **Nested tool calls** (tool calling another tool) not fully captured
4. **Failed tool calls** vs successful not distinguished

---

## 🚀 Next Steps

1. Implement Intent Solution (Option A recommended)
2. Test intent storage with all 3 agent types
3. Implement Tool Calls Solution (Option A recommended)
4. Test tool_calls storage with booking + sales queries
5. Document final implementation in NOTAS_CLAUDE.md
6. Remove debug logging added during investigation
