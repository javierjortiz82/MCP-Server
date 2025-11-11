# Critical Issues Quick Reference - Demo Agent

**Analysis Date:** 2025-11-03  
**Full Report:** `/home/javort/alfredo/MCP-Server/docs/CRITICAL_ISSUES_ANALYSIS_2025-11-03.md`  
**Repository:** `/home/javort/alfredo/MCP-Server`  
**Branch:** `feat/web-chat-widget`

---

## Quick Summary Table

| # | Issue | File | Line | Severity | Fix Time | Priority |
|---|-------|------|------|----------|----------|----------|
| 1 | Token Counting Inaccurate | `gemini_client.py` | 90-128 | HIGH | 2-3h | 3rd |
| 2 | User Lookup Bug | `main.py` | 392-399 | CRITICAL | 1h | 1st |
| 3 | DB Not Async-Safe | `db/connection.py` | 1-146 | HIGH | 7-9h | 5th |
| 4 | OTP Expiration Too Long | `otp_service.py` | 51, 230 | MEDIUM | 1h | 2nd |
| 5 | Token Refund Missing | `agent.py` | 256-330 | HIGH | 2-3h | 4th |

---

## Issue 1: Token Counting Inaccurate

**Problem:** Counts words as tokens, underestimating by 25-30% (actual: 2-3x more tokens used)

**Current Code:**
```python
# gemini_client.py lines 90-94
input_tokens = len(system_prompt.split()) + len(user_message.split())
output_tokens = len(response_text.split())
total_tokens = input_tokens + output_tokens
```

**Quick Fix:**
```python
# Use google-genai's count_tokens() API
response = await self.client.models.count_tokens(
    model=self.model_name,
    contents=[...]
)
return response.total_tokens
```

**Impact:** Users lose quota 2-3x faster than expected  
**Complexity:** MEDIUM (2-3 hours)  
**Dependencies:** google-genai SDK's count_tokens API

---

## Issue 2: User Lookup Bug (CRITICAL)

**Problem:** Looking up by email `f"user_{request.user_id}"` instead of by ID. Could allow users to access wrong quotas.

**Current Code:**
```python
# main.py line 392 - WRONG
user = await user_service.get_user_by_email(f"user_{request.user_id}")

# main.py lines 394-399 - CORRECT but not used
user_query = """
    SELECT id, email, ...
    FROM :SCHEMA_NAME.demo_users
    WHERE id = %s
"""
user_result = user_service.db.execute_one(user_query, (request.user_id,))
```

**Quick Fix:**
```python
# Just remove line 392 and use lines 394-399
user_result = await user_service.db.execute_one(
    "SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted "
    "FROM :SCHEMA_NAME.demo_users WHERE id = %s",
    (request.user_id,)
)
```

**Impact:** Users could access wrong user's quota quota  
**Complexity:** SIMPLE (1 hour)  
**Dependencies:** None

---

## Issue 3: Database Not Async-Safe

**Problem:** psycopg2 (sync driver) blocks entire event loop. No true async concurrency.

**Current Code:**
```python
# db/connection.py lines 11-12, 34
import psycopg2
self.conn = psycopg2.connect(self.connection_string)  # BLOCKING
```

**Quick Fix:**
```python
# Add asyncpg to requirements.txt
asyncpg>=0.29.0

# Update connection.py to use asyncpg
import asyncpg
self.pool = await asyncpg.create_pool(self.connection_string)
async with self.pool.acquire() as conn:
    result = await conn.fetchrow(query, *(params or ()))
```

**Impact:** Blocks event loop, can't handle 100+ concurrent requests  
**Complexity:** COMPLEX (7-9 hours)  
**Dependencies:** asyncpg >= 0.29.0

---

## Issue 4: OTP Expiration Too Long

**Problem:** 24-hour expiration violates OWASP/NIST standards (should be 5-15 minutes). Enables brute force attacks.

**Current Code:**
```python
# otp_service.py line 51
self.expiration_hours = 24  # 24 hours as per requirements

# otp_service.py line 230
expires_at = now + timedelta(hours=self.expiration_hours)
```

**Quick Fix:**
```python
# Option 1: Direct change
self.expiration_minutes = 10

# Option 2: Configurable (better)
# Add to config/settings.py:
OTP_EXPIRATION_MINUTES: int = Field(default=10, description="OWASP compliant")

# In otp_service.py:
expires_at = now + timedelta(minutes=config.OTP_EXPIRATION_MINUTES)
```

**Impact:** Security vulnerability - allows brute force and session hijacking  
**Complexity:** SIMPLE (1 hour)  
**Dependencies:** None

---

## Issue 5: Token Refund Missing

**Problem:** If Gemini API fails, tokens aren't deducted, but quota check consumed estimation. Users appear to have quota they don't.

**Current Code:**
```python
# agent.py lines 220-268
# Pre-check quota (estimates 100 tokens)
can_proceed, _ = await self.token_bucket.check_quota(user_key, tokens_needed=100)

try:
    # Call API - could fail here
    response_text, tokens_used = await self.gemini_client.generate_response(...)
    
    # Deduct tokens - never reaches if exception
    tokens_remaining = await self.token_bucket.deduct_tokens(user_key, tokens_used)
except Exception:  # lines 317-330
    # No refund logic!
    return None, 0, TokenWarning(...), error_msg
```

**Quick Fix:**
```python
# Add try-catch with success flag
api_success = False
try:
    response_text, tokens_used = await self.gemini_client.generate_response(...)
    api_success = True
except Exception as e:
    logger.exception(f"API failed: {e}")
    # Return without deducting tokens
    return None, 0, TokenWarning(...), "Error"

# Only deduct if API succeeded
if api_success:
    tokens_remaining = await self.token_bucket.deduct_tokens(
        user_key, tokens_used
    )
```

**Impact:** Users lose tokens on failed requests with no response  
**Complexity:** MEDIUM (2-3 hours)  
**Dependencies:** None

---

## Recommended Fix Order

1. **Issue 2 (User Lookup)** - CRITICAL, 1 hour
   - Blocks everything else
   - Security vulnerability (wrong user quota)

2. **Issue 4 (OTP Expiration)** - 1 hour
   - Security vulnerability
   - Simple fix

3. **Issue 1 (Token Counting)** - 2-3 hours
   - Affects quota tracking accuracy
   - Medium complexity

4. **Issue 5 (Token Refund)** - 2-3 hours
   - Affects fairness
   - Medium complexity

5. **Issue 3 (Async DB)** - 7-9 hours
   - Performance issue, not blocking
   - Complex, requires many changes

**Total Estimated Time:** 14-18 hours

---

## File Locations

| Component | File Path |
|-----------|-----------|
| Gemini Client | `/home/javort/alfredo/MCP-Server/demo_agent/gemini_client.py` |
| Main API | `/home/javort/alfredo/MCP-Server/demo_agent/main.py` |
| Database | `/home/javort/alfredo/MCP-Server/demo_agent/db/connection.py` |
| OTP Service | `/home/javort/alfredo/MCP-Server/demo_agent/services/otp_service.py` |
| Agent | `/home/javort/alfredo/MCP-Server/demo_agent/agent.py` |
| Token Bucket | `/home/javort/alfredo/MCP-Server/demo_agent/rate_limiter/token_bucket.py` |
| User Service | `/home/javort/alfredo/MCP-Server/demo_agent/services/user_service.py` |
| Config | `/home/javort/alfredo/MCP-Server/demo_agent/config/settings.py` |

---

## Testing Strategy Summary

### Issue 1: Token Counting
- Unit: Test count_tokens accuracy vs known values
- Integration: Compare pre-count, actual API, post-count
- E2E: Run demo queries, verify token tracking

### Issue 2: User Lookup
- Unit: Test get_user_by_id with valid/invalid IDs
- Integration: Test /v1/demo with various user_ids
- E2E: Register user → query → verify quota tracked correctly

### Issue 3: Async DB
- Unit: Test async connection, concurrent queries
- Load: 100 → 1000 concurrent requests
- Integration: All existing tests with async/await

### Issue 4: OTP Expiration
- Unit: Verify expiration time is 10 minutes
- Integration: Register → OTP expires after 10 min
- Security: Brute force attempts fail after expiration

### Issue 5: Token Refund
- Unit: Test token deduction only on success
- Integration: Mock API failures, verify no deduction
- E2E: Multiple failed requests → quota unchanged

---

**For detailed analysis of each issue, see:**
`/home/javort/alfredo/MCP-Server/docs/CRITICAL_ISSUES_ANALYSIS_2025-11-03.md`

