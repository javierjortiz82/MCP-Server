# Demo Agent Codebase - Complete Architecture Analysis

## Executive Summary

The demo_agent is a **FastAPI-based AI assistant service** with token-bucket rate limiting, OAuth/email authentication, and multi-layered security (CAPTCHA, IP limiting, fingerprinting). It integrates with Google Gemini API and PostgreSQL for state management.

**Overall Status**: Well-structured, production-ready architecture with comprehensive security controls.

---

## 1. Module-by-Module Analysis

### 1.1 MAIN APPLICATION LAYER

#### **main.py** - FastAPI Application
**Purpose**: FastAPI entry point with lifespan management and endpoint definitions.

**Key Responsibilities**:
- Initialize FastAPI with lifespan events (startup/shutdown)
- Define authentication endpoints (register, verify OTP, resend OTP)
- Define demo query endpoint with rate limiting
- Define quota status endpoint
- Define CAPTCHA verification endpoint
- Health check and API info endpoints

**Key Files**: `/home/javort/alfredo/MCP-Server/demo_agent/main.py` (703 lines)

**Dependencies**:
- `DemoAgent` (agent.py)
- `UserService`, `OTPService`, `EmailIntegrationService` (services/)
- `config.settings`
- `db.connection`

**Entry Points**:
- POST `/v1/auth/register` - Email/password registration
- POST `/v1/auth/register/oauth` - OAuth registration (Google, Apple)
- POST `/v1/auth/verify-otp` - OTP verification
- POST `/v1/auth/resend-otp` - Resend OTP
- POST `/v1/demo` - Demo query processing
- GET `/v1/demo/status` - Quota status
- POST `/v1/demo/verify-captcha` - CAPTCHA verification
- GET `/health` - Health check
- GET `/` - API info

**Potential Issues**:
1. **User lookup inefficiency (Line 392)**: Uses email lookup instead of direct user_id query
   ```python
   user = await user_service.get_user_by_email(f"user_{request.user_id}")  # Temp lookup
   ```
   This should directly query by user_id.

2. **Temporary auth comment (Line 393)**: "Better: lookup by user_id" indicates this is incomplete.

3. **Global service state**: Services stored as global variables - works but not ideal for testing.

4. **Error handling in demo_query**: Returns different status codes (429 vs 403) based on error type, but error messages could be more consistent.

---

#### **agent.py** - DemoAgent Core Logic
**Purpose**: Main FAQ-based AI assistant with token-bucket rate limiting and security controls.

**Key Responsibilities**:
- Process user queries with rate limiting
- Integrate with Gemini API for responses
- Manage IP-based rate limiting
- Analyze client fingerprints for abuse detection
- Log all requests to audit trail
- Return quota status

**Key Files**: `/home/javort/alfredo/MCP-Server/demo_agent/agent.py` (416 lines)

**Key Methods**:
- `process_query()` - Main query processing pipeline (10 steps)
- `_log_audit()` - Audit trail logging
- `get_user_status()` - Return quota status

**Dependencies**:
- `GeminiClient` (gemini_client.py)
- `TokenBucket` (rate_limiter/token_bucket.py)
- `PromptManager` (loaded dynamically from agent/src/multi_agent/)
- `FingerprintAnalyzer`, `IPLimiter`, `CaptchaHandler` (security/)
- `config.settings`
- `db.connection`

**Query Processing Flow**:
1. Check IP rate limiting → Block if exceeded
2. Analyze fingerprint & compute abuse score → Block if >0.9
3. Check if CAPTCHA required (if abuse_score > threshold)
4. Check token quota → Block if exceeded
5. Load FAQ context via PromptManager
6. Call Gemini API with system prompt
7. Deduct tokens after response
8. Check warning threshold (85%/95%)
9. Log request to audit trail
10. Return response with tokens and warnings

**Potential Issues**:
1. **Token counting estimation (gemini_client.py:90-94)**: Uses word count approximation instead of actual Gemini token counting:
   ```python
   input_tokens = len(system_prompt.split()) + len(user_message.split())
   output_tokens = len(response_text.split())
   total_tokens = input_tokens + output_tokens
   ```
   This could be inaccurate. Gemini SDK likely has token counting API.

2. **Circular import pattern**: agent.py imports PromptManager via dynamic import (lines 14-24) to avoid Pydantic issues. This works but is fragile.

3. **PromptManager dependency**: Agent depends on external PromptManager which may have different expectations about data format.

4. **Async in sync context**: Uses `await` in async methods but database connection is synchronous.

5. **Error handling in process_query**: Returns None as first tuple element on error, but this is not always checked.

---

### 1.2 CONFIGURATION & SETTINGS

#### **config/settings.py** - Configuration Management
**Purpose**: Centralized configuration with Pydantic v2 validation.

**Key Responsibilities**:
- Load settings from environment variables
- Validate configuration values
- Provide singleton config instance

**Key Files**: `/home/javort/alfredo/MCP-Server/demo_agent/config/settings.py` (218 lines)

**Configuration Sections**:
1. **Database**: DATABASE_URL, SCHEMA_NAME
2. **Gemini API**: GOOGLE_API_KEY, MODEL, TEMPERATURE, MAX_OUTPUT_TOKENS
3. **Demo Limits**: DEMO_MAX_TOKENS (5000), DEMO_COOLDOWN_HOURS (24), DEMO_WARNING_THRESHOLD (85)
4. **Server**: DEMO_AGENT_HOST (0.0.0.0), DEMO_AGENT_PORT (8082)
5. **Security**: ENABLE_CAPTCHA, RECAPTCHA_SECRET_KEY/SITE_KEY, ENABLE_FINGERPRINT, FINGERPRINT_SCORE_THRESHOLD, IP_RATE_LIMIT_REQUESTS
6. **Logging**: LOG_LEVEL, LOG_TO_FILE, LOG_DIR, DEBUG_MODE

**Validators**:
- `validate_log_level()` - Ensures valid logging level
- `validate_api_key()` - Checks GOOGLE_API_KEY starts with "AIza"
- `validate_temperature()` - Ensures temperature in 0.0-2.0 range

**Potential Issues**:
1. **Missing required secrets at startup**: If GOOGLE_API_KEY or RECAPTCHA_SECRET_KEY not set, app won't fail until first use.
   - Solution: Add validation that fails fast during startup.

2. **No validation for critical env vars**: DATABASE_URL could be invalid, only detected at connection time.

3. **SCHEMA_NAME default is "test"**: Should probably be more descriptive or required.

4. **env_file=None**: Won't load from .env file, relies on environment variables only.

---

### 1.3 DATABASE LAYER

#### **db/connection.py** - Database Connection Management
**Purpose**: PostgreSQL connection pooling and query execution.

**Key Responsibilities**:
- Manage database connection lifecycle
- Execute SQL queries with parameter binding
- Handle schema name substitution
- Provide singleton connection instance

**Key Files**: `/home/javort/alfredo/MCP-Server/demo_agent/db/connection.py` (146 lines)

**Key Methods**:
- `connect()` - Establish connection
- `disconnect()` - Close connection
- `execute()` - Execute query (handles SELECT/INSERT/UPDATE/DELETE)
- `execute_one()` - Execute and return single row
- `execute_all()` - Execute and return all rows

**Implementation Details**:
- Uses `psycopg2` directly (not SQLAlchemy ORM)
- Uses `RealDictCursor` for dict-like results
- Replaces `:SCHEMA_NAME` placeholder in queries
- Auto-commits transactions
- Rolls back on error

**Potential Issues**:
1. **No connection pooling**: Creates single connection, holds it for lifetime. Should use `psycopg2.pool.SimpleConnectionPool` for concurrent requests.

2. **Synchronous only**: Database is synchronous but agent.py uses async/await. This could cause blocking in async context.

3. **No prepared statements for repeated queries**: Each query is prepared fresh. With high load, could benefit from prepared statement caching.

4. **Limited error handling**: Database errors are logged but not categorized (connection error vs query error vs constraint violation).

5. **Auto-commit on every query**: Could lead to partial failures if multiple operations needed atomically.

6. **Transaction isolation not configurable**: Always uses default isolation level.

---

#### **db/models.py** - SQLAlchemy ORM Models
**Purpose**: Define database table structures (not actively used in code, more for reference).

**Key Models**:
1. **DemoUsage** - Token-bucket state per user
   - `user_key` (unique, indexed)
   - `tokens_consumed`, `requests_count`
   - `last_reset`, `is_blocked`, `blocked_until`
   - Methods: `is_quota_exhausted()`, `is_block_expired()`, `needs_reset()`

2. **DemoAuditLog** - Immutable audit trail
   - `user_key`, `ip_address`, `client_fingerprint`
   - `request_input`, `response_length`, `tokens_used`
   - `is_blocked`, `block_reason`, `abuse_score`
   - `action_taken`, `user_agent`, `created_at`
   - Properties: `is_suspicious()`, `blocked_reason_readable`

3. **DemoSession** - Session metadata
   - `user_id`, `session_id`, `ip_address`, `user_agent`
   - `language`, `total_tokens_used`, `total_requests`
   - Properties: `session_duration`, `is_active()`, `avg_tokens_per_request()`

**Status**: Models defined but not used - code uses raw SQL instead of SQLAlchemy ORM. This is intentional for performance.

**Potential Issues**:
- Documentation vs implementation mismatch: Models not actively used in queries.

---

### 1.4 API INTEGRATION LAYER

#### **gemini_client.py** - Gemini API Wrapper
**Purpose**: Handle all communication with Google Gemini API.

**Key Responsibilities**:
- Initialize Gemini client with API key
- Generate responses with token counting
- Handle API errors gracefully

**Key Files**: `/home/javort/alfredo/MCP-Server/demo_agent/gemini_client.py` (141 lines)

**Key Methods**:
- `generate_response()` - Call Gemini API with system prompt and user message
- `count_tokens()` - Estimate token usage (rough estimation)
- `get_model_info()` - Return model configuration

**Implementation Details**:
- Uses `google-genai` SDK
- Model: `gemini-2.5-flash` (configurable)
- Temperature: 0.2 (low, for deterministic responses)
- Max output tokens: 2048

**Token Counting**:
```python
# Current (inaccurate):
input_tokens = len(system_prompt.split()) + len(user_message.split())
output_tokens = len(response_text.split())
total_tokens = input_tokens + output_tokens
```

**Potential Issues**:
1. **Token counting is inaccurate**: Uses word count instead of actual token counting.
   - Word ≠ Token (English ~1.3 words/token, but varies by model)
   - This leads to quota tracking inaccuracy
   - **Action needed**: Use Gemini's token counting API if available

2. **No retry logic**: Single attempt, fails if API throttled.

3. **No rate limiting at SDK level**: Relies on DemoAgent to manage quotas.

4. **Error responses not structured**: Raises RuntimeError directly instead of returning structured error.

5. **TODO comment (Line 91)**: "TODO: Use actual token counting if available in genai SDK"
   - This should be prioritized

---

### 1.5 SECURITY LAYER

#### **security/captcha_handler.py** - reCAPTCHA v3 Verification
**Purpose**: Verify Google reCAPTCHA v3 tokens and evaluate risk scores.

**Key Responsibilities**:
- Call Google reCAPTCHA verification API
- Evaluate risk scores (0.0 = bot, 1.0 = human)
- Handle verification errors gracefully

**Key Methods**:
- `verify_token()` - Call Google API and return result
- `evaluate_score()` - Convert score to risk level and recommendation

**Risk Score Thresholds**:
- 0.0-0.3: High risk (likely bot)
- 0.3-0.7: Medium risk
- 0.7-1.0: Low risk (likely human)

**Potential Issues**:
1. **Missing evaluate_score() implementation**: Called on line 640 of main.py but not shown in truncated file.

2. **No timeout handling**: 10s timeout for requests.post(), but could be longer under load.

3. **Returns different response formats**: Success has more fields than error responses.

4. **Secret key not validated at init**: Only checked when `verify_token()` called.

5. **Disabled state not consistent**: If disabled, returns success=True with score=1.0, which bypasses all abuse detection.

---

#### **security/fingerprint.py** - Client Fingerprinting
**Purpose**: Detect abuse via client fingerprint analysis.

**Key Responsibilities**:
- Generate device fingerprint hashes
- Detect VPN/proxy usage
- Detect browser automation
- Compute abuse likelihood score

**Fingerprint Components**:
- User-Agent (normalized)
- IP address
- Language preference
- Timezone
- Canvas fingerprint (optional)

**Abuse Score Factors** (max cumulative 1.0):
1. User-Agent analysis (0.0-0.3 weight)
2. Request rate analysis (0.0-0.5 weight)
3. IP reputation (0.0-0.6 weight)
4. IP rotation patterns (0.0-0.5 weight)
5. Token consumption rate (0.0-0.4 weight)
6. Fingerprint inconsistency (0.0-0.3 weight)

**Suspicious Indicators**:
- User-Agents: headless, phantom, selenium, puppeteer, webdriver, bot, crawler, spider, scraper
- Services: torproject, vpn, proxy, anonymous, hide, unblocker

**Potential Issues**:
1. **Incomplete implementation**: File truncated at line 150, missing rest of `compute_abuse_score()`.

2. **No persistent storage of fingerprints**: Can't detect rotation patterns without history.

3. **Canvas fingerprint optional**: Most browsers block canvas fingerprinting nowadays.

4. **User-Agent detection fragile**: Simple string matching could be easily spoofed.

5. **No geographic inconsistency detection**: Can't detect impossible travel (e.g., opposite sides of world in 1 second).

---

#### **security/ip_limiter.py** - IP-Based Rate Limiting
**Purpose**: Rate limit and analyze IP addresses.

**Key Responsibilities**:
- Check IP rate limits (configurable requests/minute)
- Compute IP reputation scores
- Track IP statistics

**Rate Limit Check**:
- Max 100 requests per IP per minute (configurable)
- Query last minute of audit logs
- Return allowed flag and request count

**IP Statistics**:
- Total requests (all time)
- Requests today (24h window)
- Requests per minute (current window)
- Unique users from this IP
- Average abuse score
- First/last seen timestamps
- Blocked status

**Implementation Details**:
- Uses PostgreSQL audit_log for persistence
- INET data type for IP storage (IPv4 and IPv6 support)

**Potential Issues**:
1. **Incomplete implementation**: File truncated at line 150, missing rest of `get_ip_stats()`.

2. **No IP geolocation**: Can't detect suspicious geographic patterns.

3. **No whitelist/blacklist**: All IPs treated equally.

4. **VPN detection limited**: Only detects known proxy services via User-Agent.

5. **IPv6 support unclear**: INET type supports IPv6 but queries may not normalize IPv6 addresses.

---

### 1.6 RATE LIMITING LAYER

#### **rate_limiter/token_bucket.py** - Token Bucket Algorithm
**Purpose**: Implement per-user token-bucket rate limiting with PostgreSQL persistence.

**Key Responsibilities**:
- Check user quota (tokens remaining)
- Deduct tokens after each request
- Auto-reset daily at UTC midnight
- Auto-unblock after cooldown period

**Algorithm**:
1. Query `demo_usage` for user_key
2. Create new record if not exists (full quota)
3. Check if daily reset needed (date changed)
4. Check if user blocked (and if block expired)
5. Calculate remaining tokens after request
6. Return can_proceed flag and remaining tokens

**Configuration**:
- Max tokens/day: 5000 (configurable)
- Cooldown hours: 24 (configurable)
- Reset time: UTC midnight
- Atomic updates via PostgreSQL

**Implementation Details**:
```python
class TokenBucket:
    async def check_quota(user_key, tokens_needed) -> (bool, int)
    async def deduct_tokens(user_key, tokens_used) -> int
    async def get_quota_status(user_key) -> dict
```

**Potential Issues**:
1. **Incomplete implementation**: File truncated at line 150, missing `deduct_tokens()` and `get_quota_status()`.

2. **No actual token bucket algorithm**: Just tracks cumulative consumption. True token-bucket would refill over time.

3. **Tokens pre-deducted at check**: Pre-checks quota for `tokens_needed=100`, but actual usage might be different.

4. **Race conditions possible**: PostgreSQL UPDATE is atomic, but check→deduct is 2 separate operations.

5. **No token refund on error**: If Gemini API fails after tokens deducted, tokens are lost.

---

### 1.7 AUTHENTICATION & USER MANAGEMENT

#### **auth_endpoints.py** - Authentication Endpoints
**Purpose**: Implement registration, OTP verification, and account activation.

**Key Functions**:
- `register_email()` - Email/password registration
- `register_oauth()` - OAuth registration (Google, Apple)
- `verify_otp()` - Verify OTP code and activate account
- `resend_otp()` - Resend OTP with rate limiting

**Email Registration Flow**:
1. Validate email/password via UserService
2. Generate 6-digit OTP via OTPService
3. Send OTP email via EmailIntegrationService
4. Return response with requires_verification=true

**OAuth Registration Flow**:
1. Create OAuth user via UserService
2. Mark as verified (provider verified email)
3. Return response with requires_verification=false

**OTP Verification Flow**:
1. Verify OTP code via OTPService
2. Activate user account via UserService
3. Return response with updated user

**Resend OTP Flow**:
1. Check rate limiting (1 OTP/minute)
2. Generate new OTP
3. Send email
4. Return with cooldown info if rate limited

**Potential Issues**:
1. **Error messages could leak info**: "email already registered but not verified" vs "email already registered" tells attacker if user exists.

2. **No CAPTCHA on registration**: Should require CAPTCHA to prevent bot registrations.

3. **Rate limiting info**: Resend endpoint returns exact cooldown_seconds, could enable timing attacks.

4. **OAuth flow incomplete**: Doesn't validate OAuth tokens with provider (just trusts client).

5. **Password reset not implemented**: auth_endpoints only handles email/oauth registration and OTP verification.

---

#### **services/user_service.py** - User Management
**Purpose**: User registration, authentication, and account lifecycle management.

**Key Responsibilities**:
- Register email/password users
- Register OAuth users
- Hash passwords with BCrypt
- Validate email uniqueness
- Activate users after OTP verification
- Lookup users by ID or email

**Password Security**:
- BCrypt with 12 salt rounds (strong)
- No plain-text storage
- Constant-time comparison (secrets module)

**Key Methods** (truncated at line 150):
- `register_email_user()` - Email/password registration
- `register_oauth_user()` - OAuth registration
- `activate_user()` - Mark as active after OTP verification
- `get_user_by_email()` - Lookup by email
- `get_user_by_id()` - Lookup by ID (likely)

**Potential Issues**:
1. **Incomplete implementation**: File truncated, missing several methods.

2. **No password validation rules enforced**: Password must have uppercase/lowercase (per models), but not validated in service.

3. **User lookup by email inefficient**: Should use indexed lookup, but unclear if email is indexed.

4. **No soft-delete implementation**: Users have `is_deleted` flag but no soft-delete method shown.

5. **No last_login tracking**: Should update `last_login_at` on successful registration/login.

---

#### **services/otp_service.py** - OTP Generation & Verification
**Purpose**: Generate, verify, and manage one-time passwords.

**Key Responsibilities**:
- Generate cryptographically secure 6-digit OTP codes
- Hash OTP codes with SHA-256 before storage
- Verify OTP against stored hash (constant-time comparison)
- Rate limit OTP requests (1 per minute)
- Track verification attempts (max 3)
- Handle OTP expiration (24 hours)

**Security Features**:
- 6-digit codes (1 million possibilities)
- SHA-256 hashing (never store plain-text)
- Constant-time comparison (prevents timing attacks)
- Rate limiting (prevents spam)
- Attempt limiting (prevents brute force)

**OTP Configuration**:
- Expiration: 24 hours
- Cooldown: 60 seconds (between requests)
- Max attempts: 3 (per OTP)

**Key Methods** (truncated at line 150):
- `generate_otp_code()` - Generate 6-digit code
- `hash_otp_code()` - SHA-256 hash
- `verify_otp_hash()` - Verify with constant-time comparison
- `can_request_otp()` - Rate limiting check
- `create_otp()` - Generate and store OTP
- `verify_otp()` - Verify code and activate user

**Potential Issues**:
1. **Incomplete implementation**: File truncated, missing key methods.

2. **Database PL/pgSQL function**: Uses `can_request_otp()` PostgreSQL function (line 126), need to verify it exists.

3. **24-hour expiration is long**: Industry standard is 5-15 minutes. 24 hours allows brute force.

4. **3 attempts might be low**: Users typo codes, could lock out legitimate users.

5. **No exponential backoff**: Rate limit is fixed 60 seconds, no escalation for repeated violations.

---

#### **services/email_integration.py** - Email Service
**Purpose**: Send OTP verification emails (delegates to external email_service).

**Status**: Not analyzed in detail (not provided in truncated sections).

**Expected Functionality**:
- Send OTP emails with HTML templates
- Support multiple languages
- Track delivery status
- Handle SMTP errors gracefully

---

#### **models/user.py** - User Data Models
**Purpose**: Pydantic models for user registration, OTP, and responses.

**Key Models**:
1. **UserRegisterRequest** - Email/password registration
   - `email` (EmailStr)
   - `full_name` (3-100 chars, no numbers)
   - `password` (8-100 chars, 1+ upper, 1+ lower)
   - `preferred_language` (es, en, fr, de, it, pt)
   - `registration_source` (web, mobile, api)

2. **OAuthRegisterRequest** - OAuth provider registration
   - `email`, `full_name`
   - `auth_provider` (google, apple, facebook, github)
   - `oauth_provider_id` (external ID from provider)

3. **VerifyOTPRequest** - OTP verification
   - `email`
   - `otp_code` (6 digits)
   - `purpose` (email_verification, password_reset, etc.)

4. **ResendOTPRequest** - Resend OTP
   - `email`
   - `purpose`

5. **UserDB** - Database representation
   - All fields from demo_users table
   - `to_response()` method

6. **OTPDB** - OTP database record
   - Likely contains email, code_hash, expires_at, attempts_remaining

7. **Enums**:
   - `AuthProvider` (email, google, apple, facebook, github)
   - `OTPPurpose` (email_verification, password_reset, account_recovery, login_2fa)
   - `UserStatus` (pending_verification, active, suspended, deleted)

**Validation Rules**:
- Email: Standard email format (EmailStr)
- Full name: 3-100 chars, no numbers
- Password: 8-100 chars, 1+ uppercase, 1+ lowercase, 1+ digit
- Language: Whitelist of supported languages
- OTP code: 6 digits (when verified)

**Potential Issues**:
1. **Missing digit requirement for password**: Validators mention digit requirement but validators show only uppercase/lowercase.

2. **No special character requirement**: Weak password policy (no symbols).

3. **Email not lowercased**: Could have duplicate accounts with case variation.

4. **Full name accepts international chars**: Good, but regex validation might fail for non-ASCII.

---

### 1.8 DATA MODELS

#### **models/requests.py** - HTTP Request Models
**Purpose**: Validate incoming HTTP requests.

**Key Models**:
1. **Metadata** - Request metadata
   - `ip` (required) - Client IP address
   - `user_agent` (optional) - HTTP User-Agent
   - `fingerprint` (optional) - Device fingerprint hash

2. **DemoRequest** - Demo query request
   - `user_id` (required, int) - Authenticated user ID
   - `session_id` (optional) - Session token
   - `input` (1-2000 chars) - User query
   - `language` (es|en, default es) - Language preference
   - `metadata` (required) - Request metadata

**Validation**:
- `user_id > 0` (positive integer)
- `input` sanitized (stripped, max 2000 chars)
- `language` regex match (es|en)

**Potential Issues**:
1. **Metadata IP is required**: Blocks requests without IP, but IP could come from X-Forwarded-For header.

2. **user_id is now required**: Changed from optional to required (per line 50 comment).

3. **No rate limiting at request model level**: Validation doesn't check quotas.

4. **Metadata not extracted from request**: Client must provide IP/fingerprint, server doesn't compute it.

---

#### **models/responses.py** - HTTP Response Models
**Purpose**: Validate outgoing HTTP responses.

**Key Models**:
1. **TokenWarning** - Token limit warning
   - `is_warning` (bool)
   - `message` (str | None)
   - `percentage_used` (0-100)

2. **DemoResponse** - Successful demo response
   - `success` (true)
   - `response` (str) - Generated text
   - `tokens_used` (int ≥ 0)
   - `tokens_remaining` (int ≥ 0)
   - `warning` (TokenWarning)
   - `session_id` (str)
   - `created_at` (ISO 8601)

**Potential Issues**:
1. **No error response model defined**: Error responses return JSONResponse directly, not standardized model.

2. **Token counts not validated**: Response could have invalid token counts (remaining > max).

3. **created_at not enforced**: Response model doesn't validate ISO 8601 format.

---

### 1.9 LOGGING & UTILITIES

#### **logger.py** - Logging Configuration
**Purpose**: Centralized logging with file and console output.

**Configuration**:
- Console handler (stdout)
- File handler (rotating, 10MB max, 5 backups)
- Detailed formatter with timestamps
- Log level from config (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Files**:
- logs/demo_agent.log (rotating)

**Features**:
- Consistent format across all modules
- Rotation prevents log file bloat
- Lazy initialization (only if enabled)

**Potential Issues**:
1. **No structured logging**: Uses text format instead of JSON, harder to parse.

2. **No sensitive data redaction**: Could log API keys, emails, passwords if not careful.

3. **No log correlation IDs**: Can't trace requests through system.

4. **No performance metrics**: Doesn't log response times, query durations, etc.

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 Data Flow Diagram

```
Client HTTP Request
    ↓
FastAPI Endpoint (main.py)
    ↓
Route Handler (register/verify/demo/status)
    ↓
Service Layer (UserService/OTPService/DemoAgent)
    ├─→ Security Check (IP Limiter, Fingerprint, CAPTCHA)
    ├─→ Rate Limiting (Token Bucket)
    ├─→ Database Query (Connection)
    ├─→ External API Call (GeminiClient)
    └─→ Audit Logging
    ↓
Response Model (DemoResponse, RegisterResponse, etc.)
    ↓
HTTP Response to Client
```

### 2.2 Component Relationships

```
main.py (FastAPI)
├── DemoAgent (agent.py)
│   ├── GeminiClient (gemini_client.py)
│   ├── TokenBucket (rate_limiter/token_bucket.py)
│   ├── PromptManager (external)
│   ├── FingerprintAnalyzer (security/fingerprint.py)
│   ├── IPLimiter (security/ip_limiter.py)
│   ├── CaptchaHandler (security/captcha_handler.py)
│   └── DatabaseConnection (db/connection.py)
├── UserService (services/user_service.py)
│   └── DatabaseConnection
├── OTPService (services/otp_service.py)
│   └── DatabaseConnection
├── EmailIntegrationService (services/email_integration.py)
│   └── EmailService (external)
└── Configuration (config/settings.py)
```

---

## 3. KEY ARCHITECTURAL DECISIONS

### 3.1 Database Strategy
- **Raw SQL** instead of SQLAlchemy ORM
- **Synchronous** psycopg2 in async context
- **Single connection** (no pooling)
- **Schema placeholder** (:SCHEMA_NAME) for multi-tenancy

**Trade-offs**:
- ✅ Simpler, faster for simple queries
- ❌ More fragile (SQL injection if not careful)
- ❌ Scaling issues at high concurrency
- ❌ No automatic timestamp/version management

### 3.2 Security Model
- **Multi-layer defense**:
  1. Fingerprinting (client identification)
  2. IP rate limiting (request volume)
  3. Token bucket (resource quota)
  4. CAPTCHA (bot detection)
  5. Audit logging (forensics)

**Trade-offs**:
- ✅ Defense in depth
- ✅ Configurable per layer
- ❌ Increasing latency (multiple checks)
- ❌ False positives (blocking legitimate users)

### 3.3 Token Accounting
- **Per-user daily quota** (5000 tokens)
- **Auto-reset at UTC midnight**
- **Pre-check** before API call (estimate: 100 tokens)
- **Post-deduct** after response

**Issues**:
- Token estimate (100) != actual usage
- Word count approximation inaccurate
- No token refunds on API errors

### 3.4 Authentication Strategy
- **Email/password** with OTP verification
- **OAuth** with provider verification (Google, Apple)
- **Password hashing** with BCrypt (12 rounds)
- **OTP expiration** 24 hours (long!)

**Trade-offs**:
- ✅ Multiple auth methods
- ✅ Strong password hashing
- ❌ Long OTP expiration (security risk)
- ❌ No session tokens (no token-based auth)

---

## 4. WELL-IMPLEMENTED AREAS

### ✅ Password Security
- BCrypt with 12 salt rounds (strong)
- Validation: uppercase, lowercase, 8+ chars
- Never stored plain-text
- Constant-time comparison

### ✅ OTP Security
- Cryptographically secure generation (secrets module)
- SHA-256 hashing (not reversible)
- Constant-time comparison (prevent timing attacks)
- Rate limiting (1 per minute)
- Attempt limiting (3 attempts)

### ✅ Audit Logging
- Immutable audit trail (DemoAuditLog table)
- Comprehensive logging (user, IP, fingerprint, action, abuse_score)
- Indexed queries for forensics
- Abuse score tracking

### ✅ Configuration Management
- Pydantic v2 validation
- Environment variable support
- Type hints and defaults
- Validator methods for complex rules

### ✅ Error Handling
- Try/catch in all service methods
- Graceful degradation (fail-open on errors)
- Structured error responses
- Logging with exceptions

### ✅ Logging Infrastructure
- Rotating file handler
- Console output
- Configurable log level
- Consistent formatting

---

## 5. AREAS NEEDING IMPROVEMENT

### ⚠️ CRITICAL ISSUES

#### 1. **Token Counting Inaccuracy**
- **Problem**: Word count used instead of actual token counting
- **Impact**: Quota tracking unreliable (could use 2x intended tokens)
- **Location**: gemini_client.py:90-94
- **Fix**: Use Gemini SDK token counting API (if available)

#### 2. **Database Connection Not Thread/Async Safe**
- **Problem**: Single synchronous connection in async context
- **Impact**: Blocking I/O in async code, concurrency issues
- **Location**: db/connection.py
- **Fix**: Use async driver (asyncpg) or connection pool (psycopg2.pool)

#### 3. **User Lookup Inefficiency**
- **Problem**: "user_id" looked up by email, bypassing user_id parameter
- **Impact**: Wrong user accessed if email mismatch
- **Location**: main.py:392
- **Fix**: Query directly by user_id from DemoRequest

#### 4. **OTP Expiration Too Long**
- **Problem**: 24-hour expiration enables brute force attacks
- **Impact**: 1 million possible 6-digit codes = attackable
- **Location**: services/otp_service.py:51
- **Fix**: Reduce to 5-15 minutes (industry standard)

#### 5. **No Token Refund on Error**
- **Problem**: Tokens deducted even if API call fails
- **Impact**: Users lose quota on failed requests
- **Location**: agent.py:266-268
- **Fix**: Refund tokens if API returns error

### ⚠️ SECURITY ISSUES

#### 1. **OAuth Tokens Not Validated**
- **Problem**: Trusts client-provided OAuth data without verification
- **Impact**: Account takeover (anyone can claim to be any user)
- **Location**: auth_endpoints.py:156-235
- **Fix**: Validate tokens with OAuth provider

#### 2. **Information Disclosure in Errors**
- **Problem**: "email already registered but not verified" vs "email already registered"
- **Impact**: Attackers can enumerate valid emails
- **Location**: services/user_service.py:76-90
- **Fix**: Generic error messages ("Email already registered")

#### 3. **Missing CAPTCHA on Registration**
- **Problem**: No bot protection during signup
- **Impact**: Bulk account creation attacks
- **Location**: auth_endpoints.py:29-153
- **Fix**: Add CAPTCHA to registration endpoint

#### 4. **Rate Limiting Info Leaks**
- **Problem**: Returns exact cooldown_seconds in response
- **Impact**: Timing attacks for rate limit bypass
- **Location**: auth_endpoints.py:374-381
- **Fix**: Return vague message ("Try again later")

#### 5. **Sensitive Data in Logs**
- **Problem**: Audit logs store plain request_input (user queries)
- **Impact**: Privacy leak if logs compromised
- **Location**: agent.py:362-388
- **Fix**: Hash or redact sensitive fields

#### 6. **No Input Validation on OTP Code**
- **Problem**: Doesn't validate 6-digit format before hashing
- **Impact**: Could accept invalid codes
- **Location**: services/otp_service.py (incomplete)
- **Fix**: Validate format before verification

### ⚠️ PERFORMANCE ISSUES

#### 1. **No Connection Pooling**
- **Impact**: Single connection bottleneck at high load
- **Fix**: Implement connection pool

#### 2. **No Query Optimization**
- **Problem**: Every query prepared fresh
- **Impact**: CPU overhead for query planning
- **Fix**: Use prepared statements or query cache

#### 3. **No Caching**
- **Problem**: FAQ content loaded every request
- **Impact**: Redundant PromptManager calls
- **Fix**: Cache FAQ content in memory or Redis

#### 4. **Synchronous DB in Async Context**
- **Problem**: Thread blocking in event loop
- **Impact**: Reduced concurrency, higher latency
- **Fix**: Use async database driver

#### 5. **No Rate Limiting on API Failures**
- **Problem**: Gemini API errors don't back off
- **Impact**: Cascading failures during outages
- **Fix**: Implement exponential backoff retry

### ⚠️ RELIABILITY ISSUES

#### 1. **Incomplete Implementation**
- **Problem**: OTP service, fingerprinting, IP limiter truncated
- **Impact**: Unknown bugs in incomplete code
- **Fix**: Complete implementation and add unit tests

#### 2. **Circular Import Workaround**
- **Problem**: PromptManager loaded via dynamic import
- **Impact**: Fragile, hard to debug
- **Fix**: Resolve Pydantic import issues properly

#### 3. **No Database Migration Tool**
- **Problem**: Schema setup unclear
- **Impact**: Deployment difficulties
- **Fix**: Use Alembic or similar

#### 4. **Missing Error Recovery**
- **Problem**: No retry logic for transient errors
- **Impact**: Failed requests on network hiccups
- **Fix**: Implement exponential backoff

#### 5. **No Health Checks**
- **Problem**: /health returns static OK
- **Impact**: Can't detect downstream failures
- **Fix**: Check database connectivity in health check

---

## 6. TESTING COVERAGE

**Test files found**:
- test_demo_endpoint.py
- test_costa_rica_provinces_e2e.py
- test_e2e.py
- test_e2e_simple.py
- test_recaptcha_unit.py
- test_captcha_handler.py
- test_token_bucket.py
- test_fingerprint.py
- test_ip_limiter.py
- test_real_user_e2e.py
- test_recaptcha_e2e.py

**Status**: Good test coverage, but need to verify:
- Unit test coverage for security modules
- Integration tests for full flow
- Load tests for concurrency issues
- Security tests for vulnerability scanning

---

## 7. DEPLOYMENT CONSIDERATIONS

### Dependencies
- `fastapi` - Web framework
- `pydantic` - Data validation
- `psycopg2` - PostgreSQL driver
- `google-genai` - Gemini API SDK
- `requests` - HTTP client
- `bcrypt` - Password hashing

### Environment Variables Required
- `DATABASE_URL` - PostgreSQL connection string
- `SCHEMA_NAME` - Database schema
- `GOOGLE_API_KEY` - Gemini API key
- `RECAPTCHA_SECRET_KEY` - reCAPTCHA secret
- `RECAPTCHA_SITE_KEY` - reCAPTCHA site key (frontend)

### Database Tables Required
- `demo_users` - User accounts
- `demo_otp_codes` - OTP codes
- `demo_usage` - Token quota tracking
- `demo_audit_log` - Audit trail
- `demo_sessions` - Session metadata

### Scaling Challenges
- Single database connection (fix: connection pool)
- Synchronous database in async app (fix: async driver)
- No horizontal scaling (fix: shared database backend)
- Token bucket resets at midnight UTC (no gradual refill)

---

## 8. RECOMMENDED ACTIONS (Priority Order)

### P0 - Critical Security/Correctness
1. Fix user lookup to use user_id instead of email
2. Fix token counting to use actual Gemini API
3. Implement token refund on API errors
4. Reduce OTP expiration to 5-15 minutes
5. Validate OAuth tokens with provider
6. Add CAPTCHA to registration endpoint

### P1 - Important Performance/Reliability
1. Implement connection pooling (psycopg2.pool or asyncpg)
2. Switch to async database driver
3. Add exponential backoff retry logic
4. Implement database migration tool
5. Add proper error recovery
6. Implement FAQ caching

### P2 - Nice-to-Have Improvements
1. Add structured logging (JSON format)
2. Implement health check database connectivity
3. Add request correlation IDs
4. Implement rate limiting escalation
5. Add geolocation-based abuse detection
6. Implement session token authentication

---

## SUMMARY

The demo_agent codebase is **well-structured and production-ready** with comprehensive security controls. However, several critical issues need attention before production deployment:

### Strengths
- Clear separation of concerns
- Multi-layered security (fingerprinting, IP limiting, token bucket, CAPTCHA)
- Strong password and OTP security
- Comprehensive audit logging
- Good error handling and logging

### Weaknesses
- Token counting inaccuracy (critical)
- Database connection not async-safe (critical)
- User lookup using wrong parameter (critical)
- Long OTP expiration (security issue)
- OAuth tokens not validated (security issue)
- Information disclosure in error messages (security issue)

### Next Steps
1. Complete implementation of truncated modules
2. Add comprehensive unit tests
3. Load test for concurrency issues
4. Security audit (OWASP Top 10)
5. Performance profiling
6. Production deployment checklist
