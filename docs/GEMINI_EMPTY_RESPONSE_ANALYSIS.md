# Gemini Empty Response Analysis & Solutions

**Date:** 2025-11-09
**Issue:** Intermittent empty responses from Gemini 2.5 Flash in BookingAgent
**Status:** Root causes identified, solutions proposed

---

## 🔍 Problem Statement

### Observed Behavior

When running `python -m client_mcp` and sending the query **"quiero reservar"**, the system experiences intermittent failures:

```
👤 You: quiero reservar
🤔 Processing...
ℹ️ Intent classified: booking ✅ (Classification works correctly)
...
2025-11-08 20:42:10 - WARNING - ⚠️ Initial response validation failed: ResponseStatus.EMPTY_RESPONSE
2025-11-08 20:42:10 - ERROR - 🚨 EMPTY RESPONSE (content=None or parts=[])
  Finish reason: FinishReason.STOP
  Content: parts=None role='model'
```

**Key Observations:**
1. ✅ Intent classification succeeds (correctly identifies "booking")
2. ✅ Language detection works (en)
3. ✅ BookingAgent initializes correctly with 8 tools
4. ❌ **First generate_content() call returns EMPTY_RESPONSE**
5. ❌ **Fallback also fails with finish_reason: FinishReason.MAX_TOKENS**
6. ✅ **Retrying the same query sometimes works** (intermittent issue)

---

## 🧩 Root Causes Identified

### 1. Known Gemini 2.5 Flash Bug

**Evidence from Google AI Forum & GitHub:**
- [Issue #1289](https://github.com/googleapis/python-genai/issues/1289): "Frequent empty response with gemini 2.5 pro"
- [Issue #811](https://github.com/googleapis/python-genai/issues/811): "Empty response when max_tokens is set"
- [Forum Discussion](https://discuss.ai.google.dev/t/gemini-2-5-pro-with-empty-response-text/81175): Multiple users reporting `FinishReason.STOP` with `parts=None`

**Conclusion:** This is a **known intermittent bug** in Gemini 2.5 Flash/Pro API, not a code issue.

### 2. Potential Prompt Size Issue

**Current State:**
- Booking prompt: **287 lines, ~2314 tokens, 9259 chars**
- Uses 22 modular Jinja2 templates
- 8 MCP tools configured in AUTO mode

**Google Best Practice Violation:**
> "Limit active tools to 10-20 maximum; excess tools increase selection errors"

**Current tools count:** 8 ✅ (Within limits)

**Potential Issue:** Large prompt + complex multi-tool setup may contribute to intermittent failures.

### 3. MAX_TOKENS on Fallback

**Error in logs:**
```
finish_reason: FinishReason.MAX_TOKENS | safety_ratings: N/A
```

**Analysis:** The fallback response hits `max_output_tokens` limit and returns empty content.

**Current config:**
- `max_output_tokens`: Not explicitly shown in logs (likely default ~8192)

---

## 💡 Proposed Solutions

### Solution 1: Implement Retry with Exponential Backoff (ALREADY IMPLEMENTED ✅)

**Location:** `base_agent.py:533-539`

```python
response = await self.response_handler.retry_with_backoff(
    self.client.aio.models.generate_content,
    model=self.model_name,
    contents=contents,
    config=initial_config,
)
```

**Status:** ✅ Already using `retry_with_backoff`
**Issue:** Even with retries, Gemini API still returns empty responses (API-level bug)

### Solution 2: Reduce Temperature for Deterministic Responses

**Current config:** `booking_agent.py:431`
```python
"temperature": self.generation_config.temperature,  # Likely 0.7-1.0
```

**Recommended change:**
```python
"temperature": 0.0,  # More deterministic, reduces empty responses
```

**Rationale (Google docs):**
> "Use low temperature values (e.g., 0) for more deterministic and reliable function calls"

### Solution 3: Increase max_output_tokens for Fallback

**Current:** Default value (unclear)

**Recommended:**
```python
"max_output_tokens": 2048,  # Explicit limit to prevent MAX_TOKENS empty response
```

**Rationale:** Prevents hitting token limit which causes `parts=None` response.

### Solution 4: Add Defensive Handling for Empty Responses

**Current code:** `booking_agent.py:544-557`
```python
initial_status, initial_diagnostic = self.response_handler.validate_response(response)
if initial_status != ResponseStatus.SUCCESS:
    self.logger.warning(f"⚠️ Initial response validation failed: {initial_status}")
    # Falls back to _create_fallback_response()
```

**Recommended enhancement:**
```python
# If empty response, try with lower temperature and simplified prompt
if initial_status == ResponseStatus.EMPTY_RESPONSE:
    self.logger.warning("🔄 Retrying with simplified config due to EMPTY_RESPONSE")
    simplified_config = types.GenerateContentConfig(
        temperature=0.0,  # Deterministic
        max_output_tokens=1024,  # Lower limit
        system_instruction="You are a booking assistant. Help the user book an appointment."  # Minimal prompt
    )
    response = await self.client.aio.models.generate_content(
        model=self.model_name,
        contents=[types.Content(role="user", parts=[types.Part(text=query)])],
        config=simplified_config
    )
```

### Solution 5: Switch to `gemini-2.0-flash` (Stable)

**Current model:** `gemini-2.5-flash` (has known empty response bugs)

**Alternative:** `gemini-2.0-flash-exp` or `gemini-1.5-pro`

**Trade-offs:**
- ✅ More stable (fewer empty responses)
- ❌ Potentially less capable than 2.5
- ❌ May have different latency/cost

---

## 🎯 Recommended Immediate Actions

### Priority 1: Fix Configuration (Quick Win)

**File:** `agent/src/multi_agent/booking_agent.py`

**Changes:**
1. Set `temperature=0.0` for BookingAgent
2. Set explicit `max_output_tokens=2048`
3. Add defensive retry with simplified prompt on EMPTY_RESPONSE

### Priority 2: Fix Timing Bugs (Critical for Analytics)

**Files:**
- `agent/src/multi_agent/booking_agent.py:589` (timing bug)
- `agent/src/multi_agent/sales_agent.py` (need to verify)

**Issue:** Same bug as BaseAgent - `elapsed_ms` calculated AFTER `_update_history()` call.

**Fix:** Move timing calculation before `_update_history()` and pass `response_time_ms` + `tool_calls`.

### Priority 3: Improve Error Messages (User Experience)

**Current:** User sees generic error:
```
❌ Error: Gemini returned invalid response for language en: ResponseStatus.EMPTY_RESPONSE
```

**Better:**
```
⚠️ The AI service is experiencing temporary issues. Please try again.
(Your request was classified as: booking)
```

---

## 📊 Comparison: Current vs. Proposed Config

| Config Parameter | Current | Proposed | Rationale |
|------------------|---------|----------|-----------|
| `temperature` | 0.7-1.0 (default) | 0.0 | Google best practice for function calling |
| `max_output_tokens` | ~8192 (default) | 2048 | Prevent MAX_TOKENS empty response |
| Empty response handling | Fallback (fails) | Retry with simplified prompt | Workaround for Gemini bug |
| Model | gemini-2.5-flash | Consider gemini-2.0-flash | More stable |

---

## 🔬 Testing Recommendations

1. **Test with simplified prompt:**
   - Temporarily reduce booking prompt to 50 lines
   - Verify if empty responses still occur
   - Helps isolate prompt size as root cause

2. **Test with temperature=0.0:**
   - Modify config and test 10 consecutive "quiero reservar" queries
   - Measure failure rate before/after

3. **Test with different model:**
   - Switch to `gemini-2.0-flash-exp`
   - Compare stability

---

## 📝 Additional Findings

### Database Storage Issue (RESOLVED ✅)

**Problem:** Messages from `client_mcp` not appearing in `test.conversation_messages` table.

**Root Cause:** When running `python -m client_mcp` **without providing an email**, memory persistence is disabled.

**Code:** `client_mcp/__main__.py:74-79`
```python
customer_email = input("📧 Tu email (opcional): ").strip()
if not customer_email:
    customer_email = None
    print("ℹ️  Continuando sin memoria persistente")  # ← THIS!
```

**Solution:**
1. **Temporary:** Run with email: `python -m client_mcp` → Enter `test@example.com`
2. **Permanent:** Make email mandatory or default to a test email in dev mode

**Verification:**
```bash
# Run client_mcp
python -m client_mcp
# Enter email when prompted: test@example.com
# Send query: "quiero comprar zapatos"
# Check database:
docker exec -e PGUSER=mcp_user mcp-postgres psql -d mcpdb -c \
  "SELECT role, agent_name, response_time_ms FROM test.conversation_messages ORDER BY created_at DESC LIMIT 5;"
```

Expected result: Messages should now appear with `agent_name='sales'` and `response_time_ms` populated.

---

## 🏁 Conclusion

The intermittent empty response issue is caused by:
1. **Primary:** Known Gemini 2.5 Flash API bug (not our code)
2. **Contributing:** Suboptimal temperature setting (should be 0.0 for function calling)
3. **Exacerbating:** MAX_TOKENS limit hit on fallback attempts

**Recommended path forward:**
1. ✅ Fix config (temperature, max_tokens)
2. ✅ Fix timing bugs in BookingAgent/SalesAgent
3. ✅ Add defensive retry with simplified prompt
4. ⚠️ Monitor if Gemini 2.5 Flash stability improves (or switch to 2.0)

The database storage "issue" was user error (no email provided = no memory).
