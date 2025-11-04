# CRITICAL ISSUES ANALYSIS - Demo Agent (2025-11-03)

## Executive Summary

Five critical issues have been identified in the demo_agent codebase that could impact functionality, security, and reliability. This document provides detailed analysis of each issue with current implementation, problems, recommended fixes, and testing strategy.

---

## ISSUE 1: Token Counting Inaccurate

### Current Implementation

**File:** `/home/javort/alfredo/MCP-Server/demo_agent/gemini_client.py` (Lines 90-128)

```python
# Lines 90-94: In generate_response() method
input_tokens = len(system_prompt.split()) + len(user_message.split())
output_tokens = len(response_text.split())
total_tokens = input_tokens + output_tokens

# Lines 124-128: In count_tokens() method
prompt_words = len(system_prompt.split())
message_words = len(user_message.split())
return (prompt_words + message_words) // 4 + 50
```

### Problem Analysis

1. **Word Count vs Token Count:** The code counts words by splitting on whitespace, not actual tokens
   - Average token-to-word ratio: 1 token ≈ 0.75 words
   - Current method: 1 word ≈ 1 token (INCORRECT)
   - **Impact:** Underestimating tokens by ~25-30%

2. **No Output Token Counting:** Only counts words in output, not actual Gemini tokens
   - Gemini may generate more/fewer tokens than word count
   - Could use 2-3x more tokens than expected

3. **Comments Indicate Awareness:** Line 91 has TODO comment but not implemented:
   ```python
   # TODO: Use actual token counting if available in genai SDK
   ```

4. **Missing Output Validation:** Line 87-88 only checks if response is empty, not token accuracy

### Impact

- Users lose quota faster than expected (2-3x more than displayed)
- Quota warnings trigger earlier than calculated
- Users blame application for poor token efficiency
- Financial implications if billing is involved
- Audit logs will have inaccurate token counts

### Root Cause

Google's `genai` SDK (v0.3.0) includes `count_tokens()` method but it's not being called:
```python
# Available in google-genai >= 0.3.0:
client.models.count_tokens(
    model="gemini-2.5-flash",
    contents=[...]  # Can pass messages here
)
```

### What Needs to Change

1. Use Gemini API's native `count_tokens()` method before and after generation
2. Track actual token count from API response usage metadata if available
3. Implement accurate token counting for both input and output
4. Add validation that counted tokens match actual API usage

### Recommended Fix Approach

**Option A - Use API count_tokens method (RECOMMENDED):**
```python
async def count_tokens(self, system_prompt: str, user_message: str) -> int:
    """Use Gemini API's actual token counting."""
    try:
        response = await self.client.models.count_tokens(
            model=self.model_name,
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(system_prompt)]),
                types.Content(role="user", parts=[types.Part.from_text(user_message)])
            ]
        )
        return response.total_tokens
    except Exception as e:
        logger.warning(f"Token counting failed: {e}, falling back to estimate")
        return self._estimate_tokens(system_prompt, user_message)

async def generate_response(...) -> tuple[str, int]:
    # Pre-count tokens
    estimated_input = await self.count_tokens(system_prompt, user_message)
    
    # Call API
    response = self.client.models.generate_content(...)
    
    # Post-count tokens (use usage metadata if available)
    # Some Gemini responses include usage metadata
    actual_tokens = getattr(response, 'usage_metadata', None)
    if actual_tokens:
        total_tokens = actual_tokens.prompt_token_count + actual_tokens.candidates_token_count
    else:
        # Fallback to estimate based on response length
        output_tokens = len(response_text.split()) // 0.75
        total_tokens = estimated_input + int(output_tokens)
    
    return response_text, total_tokens
```

**Option B - Estimate with accuracy:**
```python
def _estimate_tokens_accurate(self, text: str) -> int:
    """Better token estimation: 1 token ≈ 4 chars or 0.75 words."""
    word_count = len(text.split())
    char_count = len(text)
    # Use average of both methods
    tokens_from_words = word_count / 0.75
    tokens_from_chars = char_count / 4
    return int((tokens_from_words + tokens_from_chars) / 2)
```

### Estimated Complexity

**MEDIUM**

- Requires API method research: 30 min
- Implementation: 1-2 hours
- Testing: 1 hour
- Fallback logic: 1 hour

### Dependencies & Side Effects

1. **Dependencies:**
   - google-genai SDK's count_tokens API
   - Requires understanding of response.usage_metadata (if available)

2. **Side Effects:**
   - May increase API calls slightly (pre-count tokens)
   - Could affect performance if token counting is slow
   - Different token counts will affect quota tracking

3. **Breaking Changes:**
   - Token count values will change (may affect dashboards/reports)
   - Audit logs will show different numbers retroactively
   - User quotas may appear to have more tokens available

### Testing Considerations

1. **Unit Tests:**
   ```python
   def test_count_tokens_accuracy(self):
       # Known text with known token counts
       text = "Hello world how are you today"  # Should be ~6-7 tokens
       count = client.count_tokens(text)
       assert 5 < count < 10
   
   def test_token_counting_matches_api(self):
       # Compare pre-count, actual API usage, and post-count
       pre_count = await client.count_tokens(system_prompt, user_message)
       response, actual_count = await client.generate_response(...)
       post_count = actual_count
       # Allow 5-10% variance
       assert abs(pre_count - post_count) / pre_count < 0.1
   ```

2. **Integration Tests:**
   - Test with various message lengths (short, medium, long)
   - Compare against manual Gemini API token counter
   - Verify token counts match usage tracking

3. **E2E Tests:**
   - Run 5-10 demo queries and verify token counting
   - Check quota tracking accuracy
   - Verify warning thresholds trigger correctly

4. **Regression Tests:**
   - Ensure no increase in API latency
   - Check token counting doesn't fail silently
   - Verify fallback behavior works

---

## ISSUE 2: User Lookup Bug

### Current Implementation

**File:** `/home/javort/alfredo/MCP-Server/demo_agent/main.py` (Lines 392-399)

```python
# Line 392: WRONG - Looking up by email
user = await user_service.get_user_by_email(f"user_{request.user_id}")  # Temp lookup

# Lines 394-399: CORRECT - But not used
user_query = """
    SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted
    FROM :SCHEMA_NAME.demo_users
    WHERE id = %s
"""
user_result = user_service.db.execute_one(user_query, (request.user_id,))
```

### Problem Analysis

1. **Email Lookup Instead of ID:**
   - Line 392 tries to lookup user by email `f"user_{request.user_id}"`
   - Assumes user_id is an integer that can be converted to email format
   - **This is wrong** - user_id is already the database ID

2. **Inconsistent Implementation:**
   - Line 392 attempts incorrect lookup but result is NOT used
   - Lines 394-399 show correct lookup by ID but executed separately
   - Result variable from line 392 (`user`) is never referenced again
   - Creates dead code and confusion

3. **Security Implications:**
   - If lookup by email worked, it could access wrong user's quotas
   - Different user could consume another user's tokens
   - Quota data would be attributed to wrong user

4. **User Service Method Issues:**
   - `get_user_by_email()` expects email string like "user@example.com"
   - Passing `f"user_{request.user_id}"` (e.g., "user_123") won't match any real email
   - Effectively creates a lookup that always fails
   - Default behavior then uses hardcoded user key or falls through

### Current Database Schema

From `/home/javort/alfredo/MCP-Server/demo_agent/services/user_service.py`:

```python
# Users table structure:
# - id (INT PRIMARY KEY) - database ID
# - email (VARCHAR) - email address
# - full_name (VARCHAR)
# - is_active (BOOLEAN)
# - is_email_verified (BOOLEAN)
# - is_suspended (BOOLEAN)
# - is_deleted (BOOLEAN)

# Looking up by:
# Correct: WHERE id = %s (line 397)
# Wrong: WHERE LOWER(email) = LOWER(%s) with "user_123" (line 392)
```

### What Needs to Change

1. **Remove line 392:** Delete the incorrect email-based lookup
2. **Use line 394-399:** Use the correct ID-based lookup
3. **Simplify:** Only execute correct query
4. **Validate:** Ensure request.user_id is properly validated

### Recommended Fix Approach

**SIMPLE FIX:**

```python
# Line 390-411 SHOULD BE:

# STEP 1: Validate user exists and is active
user_query = """
    SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted
    FROM :SCHEMA_NAME.demo_users
    WHERE id = %s
"""
try:
    user_id = int(request.user_id)  # Ensure it's valid integer
except (ValueError, TypeError):
    logger.warning(f"Invalid user_id format: {request.user_id}")
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "error": "invalid_user_id",
            "message": "Invalid user ID format.",
        },
    )

user_result = user_service.db.execute_one(user_query, (user_id,))

if not user_result:
    logger.warning(f"User ID {request.user_id} not found")
    # ... rest continues
```

**BETTER FIX (Use UserService method):**

```python
# Add method to UserService if doesn't exist:
async def get_user_by_id(self, user_id: int) -> UserDB | None:
    """Get user by user ID."""
    try:
        query = f"""
            SELECT id, email, full_name, display_name, auth_provider,
                   password_hash, oauth_provider_id,
                   is_email_verified, email_verified_at,
                   is_active, is_suspended, is_deleted,
                   ... (all fields)
            FROM {config.SCHEMA_NAME}.demo_users
            WHERE id = %s
        """
        result = self.db.execute_one(query, (user_id,))
        if result:
            return UserDB(**result)
        return None
    except Exception as e:
        logger.exception(f"Error in get_user_by_id: {e}")
        return None

# Then in main.py line 391-410:
user = await user_service.get_user_by_id(int(request.user_id))

if not user:
    logger.warning(f"User ID {request.user_id} not found")
    return JSONResponse(status_code=403, content={...})

if not user.is_active:
    logger.warning(f"User ID {request.user_id} is not active")
    return JSONResponse(status_code=403, content={...})
# ... etc
```

### Estimated Complexity

**SIMPLE**

- Remove wrong code: 5 min
- Test correct query: 15 min
- Add input validation: 20 min
- Add UserService method: 30 min

### Dependencies & Side Effects

1. **Dependencies:**
   - No new dependencies
   - Depends on UserService (already imported)

2. **Side Effects:**
   - Will correctly identify users going forward
   - May fail for users who were somehow using wrong lookups
   - Quota tracking will be accurate

3. **Breaking Changes:**
   - None - this is a bug fix
   - Previous "successful" lookups were actually failing

### Testing Considerations

1. **Unit Tests:**
   ```python
   def test_user_lookup_by_id(self):
       # Create test user
       user = await user_service.register_email_user(...)
       
       # Lookup by ID
       found_user = await user_service.get_user_by_id(user.id)
       assert found_user.id == user.id
       assert found_user.email == user.email
   
   def test_user_lookup_invalid_id(self):
       # Non-existent ID
       user = await user_service.get_user_by_id(99999)
       assert user is None
   
   def test_user_lookup_invalid_format(self):
       # Invalid format should be caught
       try:
           user_id = int("not_a_number")  # Should raise
       except ValueError:
           pass
   ```

2. **Integration Tests:**
   - Test /v1/demo endpoint with valid user_id
   - Test with invalid user_id formats
   - Test with non-existent user_id
   - Verify quota tracking uses correct user

3. **E2E Tests:**
   - User registration → Demo query → Verify quota tracked to correct user
   - Multiple users querying → Verify quotas separate

---

## ISSUE 3: Database Not Async-Safe

### Current Implementation

**File:** `/home/javort/alfredo/MCP-Server/demo_agent/db/connection.py` (Lines 1-146)

```python
# Lines 11-12: SYNCHRONOUS driver
import psycopg2
from psycopg2.extras import RealDictCursor

# Lines 24-44: SYNCHRONOUS connection
class DatabaseConnection:
    def __init__(self):
        self.conn = psycopg2.connect(self.connection_string)  # BLOCKING
    
    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.connection_string)  # BLOCKS EVENT LOOP
```

### Problem Analysis

1. **Synchronous Driver in Async Context:**
   - `psycopg2` is a synchronous (blocking) driver
   - Used in FastAPI async functions (demo_agent/main.py)
   - Blocks the entire event loop during database operations

2. **Impact on Concurrency:**
   - Each database query blocks entire async event loop
   - Other concurrent requests must wait
   - 1000 concurrent users = 1000 blocked contexts
   - No true concurrency benefit from FastAPI async

3. **Performance Issues:**
   - If query takes 100ms, all other requests blocked for 100ms
   - Load test with 100 concurrent requests could see 10x latency
   - Under load, application appears to "hang"

4. **Event Loop Violations:**
   - FastAPI docs warn against sync I/O in async handlers
   - May cause "sync I/O on thread" warnings
   - Could cause task cancellation issues

5. **Used in Async Functions:**
   - `demo_agent.py`: `async def process_query()` calls `db.execute()`
   - `agent.py`: `async def _log_audit()` calls `db.execute()`
   - `main.py`: `async def demo_query()` calls multiple `db.execute()`

### Example Problematic Code Flow

```python
# In main.py, line 471-478: async function with sync DB calls
@app.post("/v1/demo", response_model=DemoResponse, tags=["Demo"])
async def demo_query(request: DemoRequest):  # ASYNC but...
    # ... 
    # Line 399: BLOCKS HERE (sync query in async function)
    user_result = user_service.db.execute_one(user_query, (request.user_id,))
    
    # ... 
    # Line 258: BLOCKS HERE (sync query in async function)
    response_text, tokens_used = await self.gemini_client.generate_response(...)
```

### What's Available

From requirements.txt: `psycopg2-binary==2.9.9` only.

**NOT available:** 
- `asyncpg` - async-native PostgreSQL driver
- `databases` - async ORM wrapper

### What Needs to Change

1. **Replace psycopg2 with asyncpg** (async-native driver)
2. **Add async wrapper methods** for all database operations
3. **Update all call sites** to use await syntax
4. **Add connection pooling** for better concurrency

### Recommended Fix Approach

**MEDIUM COMPLEXITY - Two-Stage Implementation:**

**Stage 1: Add asyncpg support (keep psycopg2 as fallback)**

```python
# In requirements.txt, add:
asyncpg>=0.29.0

# In connection.py:
import asyncpg
from typing import Optional, List, Dict, Any

class AsyncDatabaseConnection:
    """Async PostgreSQL connection using asyncpg."""
    
    def __init__(self):
        self.connection_string = config.DATABASE_URL
        self.schema = config.SCHEMA_NAME
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Establish async connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
            )
            logger.info("✅ Connected to PostgreSQL (async)")
        except Exception as e:
            logger.exception(f"Failed to connect: {e}")
            raise RuntimeError(f"Database connection failed: {e}") from e
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL")
    
    async def execute(
        self,
        query: str,
        params: tuple | None = None,
        fetch_one: bool = False,
    ) -> Dict[str, Any] | List[Dict[str, Any]] | None:
        """Execute query (async)."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            query = query.replace(":SCHEMA_NAME", self.schema)
            
            async with self.pool.acquire() as conn:
                if query.strip().upper().startswith("SELECT") or "RETURNING" in query.upper():
                    if fetch_one:
                        result = await conn.fetchrow(query, *(params or ()))
                        return dict(result) if result else None
                    else:
                        results = await conn.fetch(query, *(params or ()))
                        return [dict(r) for r in results]
                else:
                    # INSERT, UPDATE, DELETE
                    await conn.execute(query, *(params or ()))
                    return None
        except Exception as e:
            logger.exception(f"Database query error: {e}")
            raise RuntimeError(f"Query execution failed: {e}") from e
    
    async def execute_one(self, query: str, params: tuple | None = None) -> Dict[str, Any] | None:
        return await self.execute(query, params, fetch_one=True)
    
    async def execute_all(self, query: str, params: tuple | None = None) -> List[Dict[str, Any]]:
        result = await self.execute(query, params, fetch_one=False)
        return result or []
```

**Stage 2: Update all call sites to use await**

```python
# Before: user_result = user_service.db.execute_one(user_query, (request.user_id,))
# After:  user_result = await user_service.db.execute_one(user_query, (request.user_id,))

# In main.py, agent.py, token_bucket.py, etc.
```

### Estimated Complexity

**COMPLEX**

- Add asyncpg: 1-2 hours
- Wrapper methods: 1 hour
- Update all call sites: 2-3 hours (many changes)
- Testing async behavior: 2 hours
- Load testing: 1 hour

**Total:** 7-9 hours

### Dependencies & Side Effects

1. **New Dependencies:**
   - asyncpg >= 0.29.0 (async-native PostgreSQL driver)
   - No other new dependencies

2. **Side Effects:**
   - Application will be concurrent (true async)
   - Database connection pooling improves
   - Potential API changes (all DB methods become async)

3. **Breaking Changes:**
   - All database calls now require `await` keyword
   - Connection initialization must be async-aware
   - Error handling patterns may differ

4. **Performance Impact:**
   - POSITIVE: Can handle 10-100x more concurrent requests
   - POSITIVE: Latency per request decreases under load
   - POSITIVE: Resource utilization improves
   - POTENTIAL NEGATIVE: Requires proper connection pool tuning

### Testing Considerations

1. **Unit Tests:**
   ```python
   @pytest.mark.asyncio
   async def test_async_database_connection(self):
       db = AsyncDatabaseConnection()
       await db.connect()
       
       # Test execute_one
       result = await db.execute_one("SELECT 1 as num")
       assert result["num"] == 1
       
       await db.disconnect()
   
   @pytest.mark.asyncio
   async def test_concurrent_queries(self):
       db = AsyncDatabaseConnection()
       await db.connect()
       
       # Run 10 queries concurrently
       tasks = [
           db.execute_one("SELECT SLEEP(0.1)")
           for _ in range(10)
       ]
       
       import time
       start = time.time()
       await asyncio.gather(*tasks)
       elapsed = time.time() - start
       
       # Should take ~0.2s (concurrent), not ~1s (sequential)
       assert elapsed < 0.3
       
       await db.disconnect()
   ```

2. **Load Tests:**
   - Before: 100 concurrent requests
   - After: 1000 concurrent requests
   - Measure latency, throughput, connection pool stats

3. **Integration Tests:**
   - All existing tests should pass
   - Test with high concurrency (100+ requests)
   - Verify connection pool doesn't exhaust

4. **Compatibility Tests:**
   - Ensure all modules using DB still work
   - Test error handling paths
   - Verify fallback behavior if needed

---

## ISSUE 4: OTP Expiration Too Long

### Current Implementation

**File:** `/home/javort/alfredo/MCP-Server/demo_agent/services/otp_service.py` (Lines 47-57, 230)

```python
# Lines 47-57: OTPService.__init__()
def __init__(self):
    """Initialize OTPService with database connection."""
    self.db = get_db()
    self.otp_length = 6
    self.expiration_hours = 24  # 24 hours as per requirements
    self.cooldown_seconds = 60  # 1 minute between OTP requests
    self.max_attempts = 3  # Max verification attempts

# Line 230: Used in create_otp()
expires_at = now + timedelta(hours=self.expiration_hours)  # 24 HOURS!
```

### Problem Analysis

1. **24-Hour Expiration is Excessive:**
   - OWASP Best Practices: 5-15 minutes
   - NIST Guidelines: 10-60 minutes (tighter is better)
   - Current: 24 hours (1440 minutes) = 96-288x LONGER than recommended

2. **Brute Force Risk:**
   - 24 hours = 86,400 seconds for attacker
   - 6-digit code = 1,000,000 possibilities
   - Rate limit: 3 attempts per OTP code
   - With 86,400 seconds available: attacker could generate new OTPs frequently
   - Could request OTP, get 3 attempts, wait 60 seconds, request new OTP, repeat
   - **In 24 hours, attacker could make ~1,440 OTP requests × 3 attempts = 4,320 guesses**

3. **Session Hijacking Risk:**
   - Valid OTP could be intercepted/leaked
   - Attacker has 24 hours to use it
   - Email compromise = account compromise for full day

4. **Compliance Issues:**
   - GDPR/HIPAA may require shorter expiration
   - PCI-DSS requires 5-15 minutes for security codes
   - Could fail security audits

5. **User Experience Issues:**
   - User receives OTP, checks email 2 hours later, code might be "confusing" if used
   - Longer window means more forgotten codes
   - Support queries about "why is my code not working?"

### Security Code Standard Times

| Standard | Recommended | Current | Risk Level |
|----------|------------|---------|-----------|
| OWASP | 5-15 min | 24 hours | CRITICAL |
| NIST | 10-60 min | 24 hours | CRITICAL |
| PCI-DSS | 5-15 min | 24 hours | CRITICAL |
| Best Practice | 5-10 min | 24 hours | CRITICAL |

### What Needs to Change

1. **Reduce expiration from 24 hours to 5-15 minutes**
2. **Consider user behavior:**
   - 5 min: Email delivery + user checks = tight
   - 10 min: Comfortable window, better security
   - 15 min: Very comfortable, still secure

3. **Increase attempt limits if reducing window:**
   - Current: 3 attempts in 24 hours = very generous
   - With 10 min window: 3 attempts is sufficient

### Recommended Fix Approach

**SIMPLE - Change one constant:**

```python
# In otp_service.py, line 51:

# BEFORE:
self.expiration_hours = 24  # 24 hours as per requirements

# AFTER (RECOMMENDED):
self.expiration_minutes = 10  # 10 minutes (OWASP compliant)

# Or if using hours (for backward compatibility):
self.expiration_hours = 10 / 60  # 10 minutes

# Update line 230:
# BEFORE:
expires_at = now + timedelta(hours=self.expiration_hours)

# AFTER:
expires_at = now + timedelta(minutes=self.expiration_minutes)
```

**BETTER - Make configurable:**

```python
# In config/settings.py:
OTP_EXPIRATION_MINUTES: int = Field(
    default=10,
    description="OTP code expiration time in minutes (OWASP: 5-15)"
)

# In otp_service.py:
from demo_agent.config.settings import config

def __init__(self):
    self.db = get_db()
    self.otp_length = 6
    self.expiration_minutes = config.OTP_EXPIRATION_MINUTES  # From config
    self.cooldown_seconds = 60
    self.max_attempts = 3

# In create_otp():
expires_at = now + timedelta(minutes=self.expiration_minutes)

# Log the setting:
logger.info(
    f"OTPService initialized (expiration: {self.expiration_minutes}min, "
    f"cooldown: {self.cooldown_seconds}s, max_attempts: {self.max_attempts})"
)
```

**BEST - Configuration + attempt adjustment:**

```python
# In config/settings.py:
OTP_EXPIRATION_MINUTES: int = Field(
    default=10,
    description="OTP expiration in minutes (OWASP: 5-15, default: 10)"
)

OTP_MAX_ATTEMPTS: int = Field(
    default=5,  # Increase from 3 to 5 since window is shorter
    description="Max OTP verification attempts (total per code)"
)

# In otp_service.py:
def __init__(self):
    self.db = get_db()
    self.otp_length = 6
    self.expiration_minutes = config.OTP_EXPIRATION_MINUTES
    self.cooldown_seconds = 60  # 1 min between OTP generation
    self.max_attempts = config.OTP_MAX_ATTEMPTS
    logger.info(
        f"OTPService initialized (expiration: {self.expiration_minutes}min, "
        f"cooldown: {self.cooldown_seconds}s, max_attempts: {self.max_attempts})"
    )
```

### Estimated Complexity

**SIMPLE**

- Change constant: 2 min
- Add to config: 10 min
- Update documentation: 15 min
- Test: 30 min

### Dependencies & Side Effects

1. **Dependencies:**
   - None (Python standard library)

2. **Side Effects:**
   - Existing OTPs with 24-hour expiration won't be retroactively changed
   - New OTPs will expire in 10 minutes
   - User experience improves (less confusion)

3. **Breaking Changes:**
   - Users must verify email within 10 minutes (vs 24 hours)
   - May cause UX issues if email delivery is slow
   - Old OTPs in database won't match new expiration time

### Testing Considerations

1. **Unit Tests:**
   ```python
   @pytest.mark.asyncio
   async def test_otp_expiration_time(self):
       otp_service = OTPService()
       
       # Create OTP
       otp_code, otp_record, error = await otp_service.create_otp(
           user_id=1, email="test@example.com"
       )
       
       # Check expiration is ~10 minutes from now
       now = datetime.now(timezone.utc)
       delta = (otp_record.expires_at - now).total_seconds() / 60
       assert 9.5 < delta < 10.5  # ~10 minutes
   
   @pytest.mark.asyncio
   async def test_expired_otp_rejected(self):
       # Create OTP and manipulate expiration to be in past
       otp_code, otp_record, error = await otp_service.create_otp(...)
       
       # Manually expire it
       past_time = datetime.now(timezone.utc) - timedelta(minutes=11)
       # (update database to set expires_at = past_time)
       
       # Try to verify - should fail
       is_valid, user_id, msg = await otp_service.verify_otp(...)
       assert is_valid is False
       assert "expired" in msg.lower()
   ```

2. **Integration Tests:**
   - Test full registration flow (register → send OTP → verify within 10 min)
   - Test OTP rejection after 10 minutes
   - Test attempt counting within window

3. **E2E Tests:**
   - User registration takes 5 minutes
   - User registration takes 12 minutes (should fail)
   - Multiple OTP requests within cooldown period

4. **Security Tests:**
   - Attempt 3,600 brute force guesses (1 per second for 1 hour)
   - Should not exhaust a single OTP code due to expiration
   - Verify rate limiting works on OTP generation

---

## ISSUE 5: Token Refund Missing

### Current Implementation

**File:** `/home/javort/alfredo/MCP-Server/demo_agent/agent.py` (Lines 256-268, 317-330)

```python
# Lines 256-268: process_query() - Error handling during generation
try:
    # ... 
    # Line 258: Call Gemini API
    response_text, tokens_used = await self.gemini_client.generate_response(...)
    
    # Line 266: Deduct tokens AFTER receiving response
    tokens_remaining = await self.token_bucket.deduct_tokens(
        user_key, tokens_used=tokens_used
    )
    # ... returns success

except Exception as e:  # Lines 317-330
    logger.exception(f"Error processing query: {e}")
    await self._log_audit(...)
    error_msg = "Error procesando tu solicitud..."
    return None, 0, TokenWarning(...), error_msg
    # NOTE: No tokens refunded, tokens_remaining never updated
```

### Problem Analysis

1. **No Refund on API Failure:**
   - If Gemini API fails AFTER token estimation, tokens are never deducted (correct)
   - BUT if request times out, rate limiting may have deducted tokens already
   - If error happens AFTER checking quota but BEFORE getting response, tokens aren't used but quota was checked

2. **Race Condition in Flow:**
   - Line 220: Check quota with estimated tokens (100 token estimate)
   - Line 258: Call Gemini API - **could fail here**
   - Line 266: Deduct actual tokens - **never reaches if exception**
   - If quota check reserved tokens but API fails, tokens are lost

3. **Token Bucket Pre-check Issue:**
   ```python
   # Line 220-222: Pre-check with estimate
   can_proceed, tokens_remaining = await self.token_bucket.check_quota(
       user_key, tokens_needed=100  # ESTIMATE
   )
   
   # Line 258: API call - could fail
   response_text, tokens_used = await self.gemini_client.generate_response(...)
   
   # Line 266: Deduct actual - might not happen if exception
   tokens_remaining = await self.token_bucket.deduct_tokens(
       user_key, tokens_used=tokens_used
   )
   ```

4. **Failure Scenarios:**
   - **Timeout:** Gemini API times out after 30 seconds
   - **Rate Limit:** Gemini API returns 429 (too many requests)
   - **Auth Error:** Invalid API key or quota exceeded at Google
   - **Network Error:** Connection lost during request
   - **Parse Error:** Response received but malformed

5. **Impact:**
   - User appears to have quota when they don't
   - Multiple failed attempts consume quota without generating responses
   - Users get frustrated ("I had tokens but can't use them!")

### What Currently Happens

```
User makes request:
1. Check quota (estimate 100 tokens) ✓ Pass
   → Quota DB updated? NO (check_quota doesn't deduct, just checks)
2. Call Gemini API
   → Timeout after 30s ✗ FAIL
   → Exception raised, caught at line 317
3. Return error response with tokens_remaining=0
   → But tokens were never actually deducted!
4. User's quota shows 5000 tokens (unchanged)
   → But they just "burned" tokens on failed request
```

### What Should Happen

```
User makes request:
1. Pre-check quota (estimate) ✓ Pass
2. Call Gemini API
   → Success ✓ Get actual tokens: 250
   → Deduct tokens: 250
   → Return response with remaining=4750

OR:

1. Pre-check quota (estimate) ✓ Pass
2. Call Gemini API
   → Timeout ✗ FAIL
   → REFUND estimated tokens (none were deducted)
   → Return error response with unchanged quota

OR (Complex):

1. Reserve quota (lock 100 tokens)
   → User sees "quota temporarily reserved"
2. Call Gemini API
   → Success ✓ Get actual: 250
   → Adjust: release 100, deduct 250 = net -250
   → Return response
   → Failure: release 100 reserved tokens
   → Return error response unchanged
```

### What Needs to Change

1. **Implement token reservation/refund mechanism**
2. **Handle Gemini API failures gracefully**
3. **Add error recovery for partial failures**
4. **Ensure tokens are only deducted on success**

### Recommended Fix Approach

**Option A - Try-Catch with Success Flag (SIMPLE):**

```python
# In agent.py, process_query() method:

try:
    # ... security checks ...
    
    # Step 4: Check quota BEFORE calling API
    can_proceed, tokens_remaining = await self.token_bucket.check_quota(
        user_key, tokens_needed=100
    )
    
    if not can_proceed:
        # ... handle quota exceeded ...
        return None, 0, TokenWarning(...), error_msg
    
    # Step 5: Call Gemini API
    api_success = False
    response_text = None
    tokens_used = 0
    
    try:
        response_text, tokens_used = await self.gemini_client.generate_response(...)
        api_success = True  # Mark success
    except Exception as api_error:
        logger.exception(f"Gemini API failed: {api_error}")
        # Don't deduct tokens - API failed
        await self._log_audit(
            ...,
            tokens_used=0,  # Don't deduct
            block_reason="api_error",
            ...
        )
        return None, 0, TokenWarning(...), "Error processing request"
    
    # Step 6: Only deduct tokens if API succeeded
    if api_success:
        tokens_remaining = await self.token_bucket.deduct_tokens(
            user_key, tokens_used=tokens_used
        )
        
        # ... calculate warnings ...
        
        # Log successful request
        await self._log_audit(
            ...,
            tokens_used=tokens_used,  # Log actual
            action_taken="allowed",
            ...
        )
        
        return response_text, tokens_used, warning, None
    
except Exception as e:
    # Outer catch-all (shouldn't reach if inner try-catch works)
    logger.exception(f"Unexpected error: {e}")
    return None, 0, TokenWarning(...), "Unexpected error"
```

**Option B - Token Reservation (COMPLEX but robust):**

```python
# Add to TokenBucket class:

async def reserve_tokens(self, user_key: str, tokens_needed: int) -> str | None:
    """Reserve tokens (lock them temporarily).
    
    Returns:
        reservation_id: Unique ID for this reservation (or None if failed)
    """
    # ... implementation
    pass

async def refund_reserved_tokens(self, user_key: str, reservation_id: str) -> bool:
    """Refund previously reserved tokens."""
    # ... implementation
    pass

async def deduct_reserved_tokens(
    self, user_key: str, reservation_id: str, tokens_used: int
) -> int:
    """Deduct actual tokens from reservation."""
    # ... implementation
    pass

# In process_query():
# 1. Reserve tokens
reservation_id = await self.token_bucket.reserve_tokens(user_key, 100)
if not reservation_id:
    return None, 0, TokenWarning(...), "Quota exceeded"

try:
    # 2. Call API
    response_text, tokens_used = await self.gemini_client.generate_response(...)
    
    # 3. Deduct from reservation
    tokens_remaining = await self.token_bucket.deduct_reserved_tokens(
        user_key, reservation_id, tokens_used
    )
    
    return response_text, tokens_used, warning, None

except Exception as e:
    # 4. Refund on error
    await self.token_bucket.refund_reserved_tokens(user_key, reservation_id)
    
    logger.exception(f"Error: {e}")
    return None, 0, TokenWarning(...), "Error processing request"
```

**RECOMMENDED: Option A (simpler, effective)**

### Estimated Complexity

**Option A: MEDIUM**
- Add api_success flag: 10 min
- Restructure error handling: 30 min
- Test error paths: 1 hour

**Option B: COMPLEX**
- Design reservation system: 1 hour
- Implement in TokenBucket: 2-3 hours
- Update all call sites: 1 hour
- Test race conditions: 1-2 hours

### Dependencies & Side Effects

1. **Dependencies (Option A):**
   - None (restructuring existing code)

2. **Dependencies (Option B):**
   - None (internal to TokenBucket)

3. **Side Effects:**
   - Failed API calls won't deduct tokens
   - Users may see improved quota consistency
   - Logging will differentiate successes from failures

4. **Breaking Changes:**
   - None (internal refactoring)
   - API contract unchanged

### Testing Considerations

1. **Unit Tests:**
   ```python
   @pytest.mark.asyncio
   async def test_tokens_not_deducted_on_api_failure(self):
       # Mock Gemini client to fail
       with patch.object(
           demo_agent.gemini_client, 'generate_response',
           side_effect=RuntimeError("API timeout")
       ):
           response, tokens_used, warning, error = await demo_agent.process_query(...)
       
       # Check tokens weren't deducted
       assert response is None
       assert tokens_used == 0
       assert error is not None
       
       # Verify quota unchanged
       status = await demo_agent.get_user_status(user_key)
       assert status["tokens_used"] == 0  # Unchanged
   
   @pytest.mark.asyncio
   async def test_tokens_deducted_on_api_success(self):
       # Normal successful flow
       response, tokens_used, warning, error = await demo_agent.process_query(...)
       
       assert response is not None
       assert tokens_used > 0
       assert error is None
       
       # Verify quota updated
       status = await demo_agent.get_user_status(user_key)
       assert status["tokens_used"] == tokens_used
   ```

2. **Integration Tests:**
   - Test with mocked Gemini failures (timeout, 429, auth error)
   - Test that audit log correctly records success/failure
   - Test multiple failures in succession

3. **E2E Tests:**
   - Simulate API failures with actual error injection
   - Verify quota tracking across multiple requests
   - Test edge case: API succeeds but parsing fails

4. **Chaos Tests:**
   - Kill API mid-response
   - Simulate network timeouts
   - Inject random failures

---

## Summary Table

| Issue | Severity | Complexity | Est. Time | Impact |
|-------|----------|-----------|-----------|--------|
| 1. Token Counting | HIGH | MEDIUM | 2-3h | 2-3x token undercount |
| 2. User Lookup | CRITICAL | SIMPLE | 1h | Wrong user's quota |
| 3. Async-Safe DB | HIGH | COMPLEX | 7-9h | Blocked event loop |
| 4. OTP Expiration | MEDIUM | SIMPLE | 1h | Security vulnerability |
| 5. Token Refund | HIGH | MEDIUM | 2-3h | Lost tokens |

---

## Recommended Fix Order

1. **FIRST:** Issue 2 (User Lookup) - CRITICAL, 1 hour, blocks everything
2. **SECOND:** Issue 4 (OTP Expiration) - SIMPLE, 1 hour, security
3. **THIRD:** Issue 1 (Token Counting) - MEDIUM, 2-3 hours, accuracy
4. **FOURTH:** Issue 5 (Token Refund) - MEDIUM, 2-3 hours, fairness
5. **FIFTH:** Issue 3 (Async DB) - COMPLEX, 7-9 hours, performance

**Total estimated effort:** 14-18 hours

---

**Report Generated:** 2025-11-03
**Analyzed By:** Claude Code Analysis System
**Repository:** /home/javort/alfredo/MCP-Server
**Branch:** feat/web-chat-widget

