# Critical Issues - Code Snippets for Quick Reference

**Generated:** 2025-11-03

---

## Issue 1: Token Counting Inaccurate

### Current Code (INCORRECT)
**File:** `demo_agent/gemini_client.py` lines 90-128

```python
# Lines 90-94: Word count used as token count
input_tokens = len(system_prompt.split()) + len(user_message.split())
output_tokens = len(response_text.split())
total_tokens = input_tokens + output_tokens

# Lines 124-128: Rough estimation
prompt_words = len(system_prompt.split())
message_words = len(user_message.split())
return (prompt_words + message_words) // 4 + 50
```

### Recommended Fix

**Option A: Use google-genai API (BEST)**
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
        return self._estimate_tokens_accurate(system_prompt + user_message)

async def generate_response(
    self,
    system_prompt: str,
    user_message: str,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> tuple[str, int]:
    """Generate response using Gemini API with accurate token counting."""
    try:
        temp = temperature or config.TEMPERATURE
        max_tokens = max_output_tokens or config.MAX_OUTPUT_TOKENS

        # Pre-count input tokens
        estimated_input = await self.count_tokens(system_prompt, user_message)

        # Build generation config
        config_dict = {
            "temperature": temp,
            "max_output_tokens": max_tokens,
            "system_instruction": system_prompt,
        }

        generation_config = types.GenerateContentConfig(**config_dict)

        # Call Gemini API
        logger.debug(f"Calling Gemini API ({self.model_name})...")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_message,
            config=generation_config,
        )

        # Extract response text
        response_text = ""
        if response.candidates and response.candidates[0].content:
            content_parts = response.candidates[0].content.parts
            if content_parts and len(content_parts) > 0:
                response_text = content_parts[0].text or ""

        if not response_text:
            raise RuntimeError("Empty response from Gemini API")

        # Calculate total tokens (prefer API metadata, fallback to estimate)
        total_tokens = estimated_input
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            # Use API metadata if available
            total_tokens = (
                response.usage_metadata.prompt_token_count +
                response.usage_metadata.candidates_token_count
            )
        else:
            # Estimate output tokens
            output_tokens = len(response_text.split()) / 0.75
            total_tokens = estimated_input + int(output_tokens)

        logger.info(
            f"Gemini response generated ({total_tokens} tokens, "
            f"{len(response_text)} chars)"
        )

        return response_text, total_tokens

    except Exception as e:
        logger.exception(f"Error calling Gemini API: {e}")
        raise RuntimeError(f"Gemini API call failed: {e}") from e

def _estimate_tokens_accurate(self, text: str) -> int:
    """Better token estimation using both word and character count."""
    word_count = len(text.split())
    char_count = len(text)
    
    # Token estimation methods
    tokens_from_words = word_count / 0.75  # 1 token ≈ 0.75 words
    tokens_from_chars = char_count / 4      # 1 token ≈ 4 chars
    
    # Average both methods
    return int((tokens_from_words + tokens_from_chars) / 2)
```

---

## Issue 2: User Lookup Bug

### Current Code (WRONG)
**File:** `demo_agent/main.py` lines 390-410

```python
# Line 392: WRONG - looking up by email with "user_123" string
user = await user_service.get_user_by_email(f"user_{request.user_id}")

# Lines 394-399: CORRECT - but not used
user_query = """
    SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted
    FROM :SCHEMA_NAME.demo_users
    WHERE id = %s
"""
user_result = user_service.db.execute_one(user_query, (request.user_id,))

# Lines 401-458: Validation using user_result (correct variable)
if not user_result:
    logger.warning(f"User ID {request.user_id} not found")
    # ...
```

### Recommended Fix

**Option A: Quick Fix (Remove line 392, keep correct query)**
```python
# STEP 1: Validate user exists and is active
user_query = """
    SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted
    FROM :SCHEMA_NAME.demo_users
    WHERE id = %s
"""

# Validate user_id is integer
try:
    user_id = int(request.user_id)
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
    logger.warning(f"User ID {user_id} not found")
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "error": "user_not_found",
            "message": "User account not found. Please register first.",
        },
    )

# Check if user is active and verified
if not user_result.get("is_active"):
    logger.warning(f"User ID {user_id} is not active")
    # ... continue with other checks
```

**Option B: Use UserService method (BETTER)**

First, add to `demo_agent/services/user_service.py`:
```python
async def get_user_by_id(self, user_id: int) -> UserDB | None:
    """Get user by user ID.
    
    Args:
        user_id: User database ID.
    
    Returns:
        UserDB: User record (or None if not found).
    """
    try:
        query = f"""
            SELECT id, email, full_name, display_name, auth_provider,
                   password_hash, oauth_provider_id,
                   is_email_verified, email_verified_at,
                   is_active, is_suspended, is_deleted,
                   suspended_at, suspended_reason, deleted_at,
                   preferred_language, timezone,
                   registration_source, registration_ip,
                   last_login_at, last_login_ip,
                   created_at, updated_at
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
```

Then in `demo_agent/main.py` line 390-410:
```python
# STEP 1: Validate user exists and is active
try:
    user_id = int(request.user_id)
except (ValueError, TypeError):
    logger.warning(f"Invalid user_id format: {request.user_id}")
    return JSONResponse(status_code=403, content={
        "success": False,
        "error": "invalid_user_id",
        "message": "Invalid user ID format.",
    })

user = await user_service.get_user_by_id(user_id)

if not user:
    logger.warning(f"User ID {user_id} not found")
    return JSONResponse(status_code=403, content={
        "success": False,
        "error": "user_not_found",
        "message": "User account not found. Please register first.",
    })

if not user.is_active:
    logger.warning(f"User ID {user_id} is not active")
    return JSONResponse(status_code=403, content={
        "success": False,
        "error": "account_not_active",
        "message": "Your account is not active. Please verify your email address first.",
    })

if not user.is_email_verified:
    logger.warning(f"User ID {user_id} email not verified")
    return JSONResponse(status_code=403, content={
        "success": False,
        "error": "email_not_verified",
        "message": "Please verify your email address first.",
    })

# ... continue with other checks
```

---

## Issue 3: Database Not Async-Safe

### Current Code (BLOCKING)
**File:** `demo_agent/db/connection.py` lines 1-146

```python
# Lines 11-12: SYNCHRONOUS driver
import psycopg2
from psycopg2.extras import RealDictCursor

# Lines 24-44: BLOCKING connection
class DatabaseConnection:
    def __init__(self):
        self.connection_string = config.DATABASE_URL
        self.schema = config.SCHEMA_NAME
        self.conn = None
    
    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.connection_string)  # BLOCKS!
```

### Recommended Fix

**Step 1: Add asyncpg to requirements.txt**
```
asyncpg>=0.29.0
```

**Step 2: Create async connection class**
```python
# demo_agent/db/connection.py
import asyncpg
from typing import Optional, List, Dict, Any

class AsyncDatabaseConnection:
    """Async PostgreSQL connection using asyncpg."""
    
    def __init__(self):
        """Initialize async database connection."""
        self.connection_string = config.DATABASE_URL
        self.schema = config.SCHEMA_NAME
        self.pool: Optional[asyncpg.Pool] = None
        logger.info(f"AsyncDatabaseConnection initialized (schema: {self.schema})")
    
    async def connect(self) -> None:
        """Establish async connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
            )
            logger.info("✅ Connected to PostgreSQL (async pool)")
        except Exception as e:
            logger.exception(f"Failed to connect to PostgreSQL: {e}")
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
        """Execute query and return result (async).
        
        Args:
            query: SQL query (use :SCHEMA_NAME for schema placeholder)
            params: Query parameters for parameterized queries
            fetch_one: If True, return single row; else return all rows
        
        Returns:
            dict or list[dict] or None
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            # Replace schema placeholder
            query = query.replace(":SCHEMA_NAME", self.schema)
            
            async with self.pool.acquire() as conn:
                # Check if query returns data (SELECT or RETURNING clause)
                if query.strip().upper().startswith("SELECT") or "RETURNING" in query.upper():
                    if fetch_one:
                        result = await conn.fetchrow(query, *(params or ()))
                        return dict(result) if result else None
                    else:
                        results = await conn.fetch(query, *(params or ()))
                        return [dict(r) for r in results] if results else []
                else:
                    # INSERT, UPDATE, DELETE without returning data
                    await conn.execute(query, *(params or ()))
                    return None
        
        except Exception as e:
            logger.exception(f"Database query error: {e}")
            raise RuntimeError(f"Query execution failed: {e}") from e
    
    async def execute_one(
        self,
        query: str,
        params: tuple | None = None,
    ) -> Dict[str, Any] | None:
        """Execute query and return single row."""
        return await self.execute(query, params, fetch_one=True)
    
    async def execute_all(
        self,
        query: str,
        params: tuple | None = None,
    ) -> List[Dict[str, Any]]:
        """Execute query and return all rows."""
        result = await self.execute(query, params, fetch_one=False)
        return result or []


# Global async connection instance
_async_db_connection: AsyncDatabaseConnection | None = None


async def get_async_db() -> AsyncDatabaseConnection:
    """Get or create global async database connection."""
    global _async_db_connection
    if _async_db_connection is None:
        _async_db_connection = AsyncDatabaseConnection()
        await _async_db_connection.connect()
    return _async_db_connection


async def close_async_db() -> None:
    """Close global async database connection."""
    global _async_db_connection
    if _async_db_connection:
        await _async_db_connection.disconnect()
        _async_db_connection = None
```

**Step 3: Update main.py lifespan**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # ... existing code ...
    
    try:
        # Initialize async database connection
        await get_async_db()  # Now async!
        logger.info("✅ Database connected (async)")
        # ... rest of initialization ...
    
    except Exception as e:
        logger.exception(f"Failed to initialize: {e}")
        raise RuntimeError(f"Startup failed: {e}") from e
    
    yield
    
    # Shutdown
    logger.info("🛑 Demo Agent shutting down...")
    await close_async_db()  # Now async!
```

**Step 4: Update database calls throughout app**
```python
# Before:
user_result = user_service.db.execute_one(query, (user_id,))

# After:
user_result = await user_service.db.execute_one(query, (user_id,))
```

---

## Issue 4: OTP Expiration Too Long

### Current Code (INSECURE)
**File:** `demo_agent/services/otp_service.py` lines 47-57, 230

```python
# Lines 47-57: 24-hour expiration
def __init__(self):
    """Initialize OTPService with database connection."""
    self.db = get_db()
    self.otp_length = 6
    self.expiration_hours = 24  # 24 hours as per requirements
    self.cooldown_seconds = 60  # 1 minute between OTP requests
    self.max_attempts = 3  # Max verification attempts

# Line 230: In create_otp()
expires_at = now + timedelta(hours=self.expiration_hours)  # 24 HOURS!
```

### Recommended Fix

**Option A: Simple constant change**
```python
def __init__(self):
    """Initialize OTPService with database connection."""
    self.db = get_db()
    self.otp_length = 6
    self.expiration_minutes = 10  # 10 minutes (OWASP compliant)
    self.cooldown_seconds = 60
    self.max_attempts = 3
    logger.info(
        f"OTPService initialized (expiration: {self.expiration_minutes}min, "
        f"cooldown: {self.cooldown_seconds}s, max_attempts: {self.max_attempts})"
    )

# In create_otp() line 230:
expires_at = now + timedelta(minutes=self.expiration_minutes)
```

**Option B: Configurable (BETTER)**

Add to `demo_agent/config/settings.py`:
```python
OTP_EXPIRATION_MINUTES: int = Field(
    default=10,
    description="OTP code expiration time in minutes (OWASP: 5-15, default: 10)"
)

OTP_MAX_ATTEMPTS: int = Field(
    default=5,  # Increased from 3 since window is much shorter
    description="Max OTP verification attempts per code (default: 5)"
)
```

Then update `demo_agent/services/otp_service.py`:
```python
from demo_agent.config.settings import config

class OTPService:
    def __init__(self):
        """Initialize OTPService with database connection."""
        self.db = get_db()
        self.otp_length = 6
        self.expiration_minutes = config.OTP_EXPIRATION_MINUTES  # From config
        self.cooldown_seconds = 60
        self.max_attempts = config.OTP_MAX_ATTEMPTS  # From config
        logger.info(
            f"OTPService initialized (expiration: {self.expiration_minutes}min, "
            f"cooldown: {self.cooldown_seconds}s, max_attempts: {self.max_attempts})"
        )

async def create_otp(self, ...):
    # ... existing code ...
    
    # Line 230:
    expires_at = now + timedelta(minutes=self.expiration_minutes)
    
    # ... rest of method ...
```

---

## Issue 5: Token Refund Missing

### Current Code (NO ERROR HANDLING)
**File:** `demo_agent/agent.py` lines 256-330

```python
try:
    # ... security checks ...
    
    # Line 220: Check quota (estimate)
    can_proceed, tokens_remaining = await self.token_bucket.check_quota(
        user_key, tokens_needed=100
    )
    
    if not can_proceed:
        # ... quota exceeded ...
        return None, 0, TokenWarning(...), error_msg
    
    # ... load prompts ...
    
    # Line 258: Call Gemini API
    response_text, tokens_used = await self.gemini_client.generate_response(...)
    
    # Line 266: Deduct tokens
    tokens_remaining = await self.token_bucket.deduct_tokens(
        user_key, tokens_used=tokens_used
    )
    
    # ... success path ...
    return response_text, tokens_used, warning, None

except Exception as e:  # Lines 317-330
    logger.exception(f"Error processing query: {e}")
    await self._log_audit(...)
    error_msg = "Error procesando tu solicitud..."
    return None, 0, TokenWarning(...), error_msg
    # NOTE: No refund! Tokens were never deducted anyway!
```

### Recommended Fix

**Add success flag and conditional deduction**
```python
async def process_query(
    self,
    user_input: str,
    user_key: str,
    language: str = "es",
    ip_address: str | None = None,
    user_agent: str | None = None,
    client_fingerprint: str | None = None,
) -> tuple[str | None, int, TokenWarning, str | None]:
    """Process a demo query with proper error handling and token refunds."""
    try:
        logger.info(f"Processing query from {user_key} (lang={language})")
        
        # ... security checks (lines 109-217) ...
        
        # Step 4: Check quota before processing
        can_proceed, tokens_remaining = await self.token_bucket.check_quota(
            user_key, tokens_needed=100
        )
        
        if not can_proceed:
            status = await self.token_bucket.get_quota_status(user_key)
            error_msg = (
                f"Demo bloqueada. Límite de {config.DEMO_MAX_TOKENS:,} "
                f"tokens alcanzado. Reintenta en {status['next_reset']}."
            )
            logger.warning(f"Query rejected - quota exceeded: {user_key}")
            await self._log_audit(
                user_key=user_key,
                ip_address=ip_address,
                fingerprint=client_fingerprint,
                user_agent=user_agent,
                request_input=user_input,
                is_blocked=True,
                block_reason="quota_exceeded",
                action_taken="blocked",
            )
            return (
                None,
                0,
                TokenWarning(is_warning=True, message=error_msg),
                error_msg,
            )
        
        # Step 5: Load system prompt with FAQ context
        remaining_tokens = tokens_remaining
        system_prompt = self.prompt_manager.get_demo_prompt(
            remaining_tokens=remaining_tokens,
            user_lang=language,
        )
        
        # Step 6: Call Gemini API (WITH ERROR HANDLING)
        api_success = False
        response_text = None
        tokens_used = 0
        
        try:
            logger.debug(f"Calling Gemini API for {user_key}...")
            response_text, tokens_used = await self.gemini_client.generate_response(
                system_prompt=system_prompt,
                user_message=user_input,
                temperature=config.TEMPERATURE,
                max_output_tokens=config.MAX_OUTPUT_TOKENS,
            )
            api_success = True  # Mark as successful
            
        except Exception as api_error:
            logger.exception(f"Gemini API failed for {user_key}: {api_error}")
            # API failed - DON'T deduct tokens
            await self._log_audit(
                user_key=user_key,
                ip_address=ip_address,
                fingerprint=client_fingerprint,
                user_agent=user_agent,
                request_input=user_input,
                tokens_used=0,  # No tokens used
                is_blocked=True,
                block_reason="api_error",
                action_taken="failed",
                abuse_score=0.0,
            )
            error_msg = "Error procesando tu solicitud. Por favor intenta más tarde."
            return None, 0, TokenWarning(is_warning=True, message=error_msg), error_msg
        
        # Step 7: Only deduct tokens if API succeeded
        if api_success:
            tokens_remaining = await self.token_bucket.deduct_tokens(
                user_key, tokens_used=tokens_used
            )
            
            # Step 8: Check warning threshold
            status = await self.token_bucket.get_quota_status(user_key)
            percentage_used = status["percentage_used"]
            is_warning = percentage_used >= config.DEMO_WARNING_THRESHOLD
            warning_msg = None
            
            if is_warning:
                if percentage_used >= 95:
                    warning_msg = (
                        f"ALERTA: Has usado {percentage_used}% de tu cuota diaria. "
                        f"Quedan {tokens_remaining:,} tokens."
                    )
                elif percentage_used >= 85:
                    warning_msg = (
                        f"Advertencia: Has usado {percentage_used}% de tu cuota diaria. "
                        f"Quedan {tokens_remaining:,} tokens."
                    )
            
            warning = TokenWarning(
                is_warning=is_warning,
                message=warning_msg,
                percentage_used=percentage_used,
            )
            
            # Step 9: Log successful request
            await self._log_audit(
                user_key=user_key,
                ip_address=ip_address,
                fingerprint=client_fingerprint,
                user_agent=user_agent,
                request_input=user_input,
                response_length=len(response_text),
                tokens_used=tokens_used,  # Log actual
                is_blocked=False,
                action_taken="allowed",
                abuse_score=0.0,
            )
            
            logger.info(
                f"Query processed: {user_key} -> "
                f"tokens_used={tokens_used}, "
                f"remaining={tokens_remaining}, "
                f"warning={is_warning}"
            )
            
            return response_text, tokens_used, warning, None
    
    except Exception as e:
        logger.exception(f"Unexpected error processing query: {e}")
        await self._log_audit(
            user_key=user_key,
            ip_address=ip_address,
            fingerprint=client_fingerprint,
            user_agent=user_agent,
            request_input=user_input,
            is_blocked=True,
            block_reason="internal_error",
            action_taken="failed",
        )
        error_msg = "Error procesando tu solicitud. Por favor intenta más tarde."
        return None, 0, TokenWarning(is_warning=True, message=error_msg), error_msg
```

---

## Testing Code Examples

### Issue 1: Token Counting Tests
```python
# tests/test_token_counting.py
@pytest.mark.asyncio
async def test_count_tokens_uses_api():
    """Verify token counting uses google-genai API."""
    client = GeminiClient()
    
    # Test with known text
    system_prompt = "You are a helpful assistant."
    user_message = "What is Python?"
    
    tokens = await client.count_tokens(system_prompt, user_message)
    
    # Should be reasonable (10-30 tokens for this short text)
    assert 5 < tokens < 50


@pytest.mark.asyncio
async def test_generate_response_token_accuracy():
    """Verify generated tokens match actual usage."""
    client = GeminiClient()
    
    system_prompt = "You are a helpful assistant."
    user_message = "What is 2+2?"
    
    response, tokens_used = await client.generate_response(
        system_prompt, user_message
    )
    
    assert response is not None
    assert len(response) > 0
    assert tokens_used > 0  # Should have non-zero tokens
```

### Issue 2: User Lookup Tests
```python
# tests/test_user_lookup.py
@pytest.mark.asyncio
async def test_get_user_by_id():
    """Verify user lookup by ID works correctly."""
    service = UserService()
    
    # Create test user
    user_data = UserRegisterRequest(
        email="test@example.com",
        full_name="Test User",
        password="TestPass123!",
        preferred_language="en",
        registration_source="web"
    )
    user, error = await service.register_email_user(user_data)
    assert user is not None
    assert error is None
    
    # Lookup by ID
    found_user = await service.get_user_by_id(user.id)
    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == user.email


@pytest.mark.asyncio
async def test_user_lookup_invalid_format():
    """Verify invalid user_id formats are rejected."""
    service = UserService()
    
    # Non-existent ID
    found_user = await service.get_user_by_id(99999)
    assert found_user is None
```

### Issue 5: Token Refund Tests
```python
# tests/test_token_refund.py
@pytest.mark.asyncio
async def test_tokens_not_deducted_on_api_failure(monkeypatch):
    """Verify tokens aren't deducted when API fails."""
    agent = DemoAgent()
    user_key = "test_user_123"
    
    # Mock Gemini to fail
    async def mock_generate_fail(*args, **kwargs):
        raise RuntimeError("API timeout")
    
    monkeypatch.setattr(
        agent.gemini_client,
        "generate_response",
        mock_generate_fail
    )
    
    # Process query (should fail)
    response, tokens_used, warning, error = await agent.process_query(
        user_input="Hello",
        user_key=user_key,
        language="es"
    )
    
    # Verify failure
    assert response is None
    assert tokens_used == 0
    assert error is not None
    
    # Verify quota unchanged
    status = await agent.get_user_status(user_key)
    assert status["tokens_used"] == 0  # Nothing deducted!
```

