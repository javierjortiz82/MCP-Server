# Booking Agent Issue - Quick Summary

## The Problem

User says "quiero reservar" (I want to book)
- **First request**: Returns generic error "No pude procesar..."
- **Second request**: Works fine, shows booking options

## Root Cause

**Gemini API Conflict**: `response_schema` + `function_calling` are mutually exclusive.

```python
# Both enabled together → response.parts = None (conflict!)
# 
# response_schema = tells Gemini to return structured JSON
# function_calling = tells Gemini to call functions
#
# These can't both be true at the same time
```

## Why Second Request Works

History + Context = Success

```
Request 1: No history → Generic fallback
Request 2: Has history → Understands intent → Calls get_services()
```

## File Map

| File | Lines | Purpose |
|------|-------|---------|
| `booking_agent.py` | 428-442 | Conditional schema config (FIX 1) |
| `booking_agent.py` | 479-495 | Two-config workaround (FIX 2) |
| `booking_agent.py` | 598-620 | Fallback detection (FIX 3) |
| `function_call_handler.py` | 112-142 | Parts extraction logic |
| `agent_router.py` | 487-713 | Intent classification |

## Data Flow

```
First Request:
  "quiero reservar" 
    → classify_intent() → BOOKING
    → generate_response() with tools 
    → Gemini: response.parts = None ❌
    → Fallback: "No pude procesar..."

Second Request:
  "quiero reservar"
    → History: ["No pude procesar..."]
    → Gemini: response.parts = [function_call] ✅
    → Execute: get_services()
    → Show options
```

## Implementation Status

| Fix | Status | Location |
|-----|--------|----------|
| Skip schema when tools present | ✅ Done | Line 428-442 |
| Two configs (initial + loop) | ✅ Done | Line 479-495 |
| Fallback to content extraction | ✅ Done | Line 598-620 |
| Improve template messaging | ⚠️ Partial | intent_detection.jinja2 |

## The Bottom Line

**This is NOT a critical bug.** It's expected behavior given API constraints.

- Users get generic message on first vague query
- Response improves on second attempt (history helps)
- Fallback mechanism prevents complete failure
- Schema + tools separation prevents API errors

**To improve UX on first request**: Update Jinja2 templates to show booking options immediately, not wait for Gemini insight.

---

## Code Evidence

### Where Schema is Removed (Line 434-440)

```python
if not self.mcp_tools:
    config_dict["response_schema"] = BOOKING_RESPONSE_SCHEMA
else:
    # No schema when tools present - avoids conflict
    self.logger.info("⏭️ Skipping response_schema (tools present)")
```

### Where Fallback Triggers (Line 602)

```python
if parts is None:
    # ... try to extract text
    # ... if fails:
    return self._create_fallback_response(iteration)
```

### Why History Helps (BaseAgent Line 165)

```python
self.conversation_history: list[types.Content] = []
# Gets populated after each response
# Provides context for next request
```

---

**Full Analysis**: See `BOOKING_AGENT_RESPONSE_PARTS_ANALYSIS.md` (580 lines)
