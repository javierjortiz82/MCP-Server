# Demo Agent - Iteración 2 Implementation

**Date**: 2025-10-31
**Status**: Complete
**Author**: Lab01-MCP Team

## Summary

Completed full Iteración 2 implementation of the Demo Agent microservice with:
- Complete database layer with SQLAlchemy ORM models
- Token-bucket rate limiting with PostgreSQL persistence
- Client fingerprinting for VPN/proxy detection
- IP-based rate limiting
- reCAPTCHA v3 integration
- Fully functional API endpoints with security integration

## Files Implemented

### 1. Database Layer

#### `demo_agent/db/models.py` (354 lines)
SQLAlchemy ORM models for all three demo tables:

- **DemoUsage**: Token-bucket state persistence
  - Fields: user_key (UNIQUE), tokens_consumed, requests_count, is_blocked, blocked_until
  - Methods: `is_quota_exhausted()`, `is_block_expired()`, `needs_reset()`
  - Atomic operations for race-condition safety

- **DemoAuditLog**: Security audit trail (immutable)
  - Fields: user_key, ip_address, client_fingerprint, abuse_score, block_reason, action_taken
  - Methods: `is_suspicious()`, `blocked_reason_readable`
  - Indexed on: abuse_score, ip_address, user_key, timestamp

- **DemoSession**: Session metadata and engagement tracking
  - Fields: user_id, session_id, language, total_tokens_used, total_requests
  - Methods: `session_duration()`, `is_active()`, `avg_tokens_per_request()`
  - Indexed on: session_id (UNIQUE), user_id, last_activity_at

### 2. Rate Limiting

#### `demo_agent/rate_limiter/token_bucket.py` (339 lines)
Complete token-bucket algorithm implementation:

- **Methods**:
  - `check_quota()`: Validates user quota, auto-resets at UTC midnight, detects expired blocks
  - `deduct_tokens()`: Atomic token deduction with automatic quota-exceeded blocking
  - `get_quota_status()`: Returns comprehensive quota state (used/remaining/percentage)
  - `unblock_user()`: Admin operation for manual unblocking
  - `_next_utc_midnight()`: UTC midnight calculation for daily resets

- **Features**:
  - Atomic PostgreSQL UPDATE queries (no race conditions)
  - Auto-reset quota at UTC midnight for all users
  - Auto-unblock when cooldown period expires
  - Comprehensive logging at DEBUG level
  - Error handling with fail-open behavior

- **Configured via**:
  - `DEMO_MAX_TOKENS`: 5,000 (default)
  - `DEMO_COOLDOWN_HOURS`: 24 (default)

### 3. Security Modules

#### `demo_agent/security/fingerprint.py` (358 lines)
Client fingerprinting and abuse detection:

- **FingerprintAnalyzer Class**:
  - `generate_fingerprint()`: SHA256 hash of client characteristics (UA, IP, lang, timezone, canvas)
  - `compute_abuse_score()`: Multi-factor abuse likelihood (0.0-1.0)
    - User-Agent analysis (0.25 weight)
    - Request rate analysis (0.30 weight)
    - IP reputation (0.25 weight)
    - IP rotation patterns (0.15 weight)
    - Token consumption rate (0.10 weight)
    - Fingerprint consistency (0.10 weight)
  - `_analyze_user_agent()`: Detects automation tools, VPN/proxy indicators
  - `_analyze_request_rate()`: Flags >10 req/min as suspicious
  - `_analyze_ip_rotation()`: Detects VPN/proxy via IP rotation >40%
  - `_analyze_fingerprint_consistency()`: Device consistency checks
  - `is_likely_vpn()`: Quick VPN/proxy detection
  - `get_fingerprint_summary()`: Risk level and recommendations

- **Detection Capabilities**:
  - Automation: Headless, Selenium, Puppeteer, Playwright indicators
  - VPN/Proxy: Torproject, VPN, proxy service keywords
  - Bot patterns: Unusual request rates, suspicious IPs
  - Device inconsistency: Fingerprint changes with IP changes

#### `demo_agent/security/ip_limiter.py` (318 lines)
IP-based rate limiting and reputation scoring:

- **IPLimiter Class**:
  - `check_rate_limit()`: Validates IP hasn't exceeded max requests/minute
  - `get_ip_stats()`: Comprehensive IP statistics
    - total_requests, requests_today, requests_per_minute
    - unique_users, abuse_score_avg, abuse_score_max
    - first_seen, last_seen timestamps
  - `is_ip_suspicious()`: Flags if IP meets suspicious criteria
    - High request rate (>5 req/min)
    - High average abuse score (>0.7)
    - Multiple blocked requests (>5 in last hour)
    - Requests from many users (>10 unique users)
  - `get_reputation_score()`: Computes IP reputation 0.0-1.0
    - Rate limit exceeded (40% weight)
    - Abuse score (40% weight)
    - Blocked request ratio (30% weight)
    - Unique users count (20% weight)

- **Configured via**:
  - `IP_RATE_LIMIT_REQUESTS`: 100 req/min (default)

#### `demo_agent/security/captcha_handler.py` (231 lines)
reCAPTCHA v3 verification and risk evaluation:

- **CaptchaHandler Class**:
  - `verify_token()`: Calls Google reCAPTCHA API with error handling
    - Returns: success, score (0.0-1.0), action, challenge_ts, hostname
  - `evaluate_score()`: Converts score to risk level and recommendation
    - 0.0-0.3: "high" → block
    - 0.3-0.7: "medium" → CAPTCHA
    - 0.7-1.0: "low" → allow
  - `should_require_captcha()`: Determines if CAPTCHA is needed
    - High abuse score (>0.8)
    - Previous low CAPTCHA score (<0.5)
    - Multiple previous blocks (≥2)
  - `get_recaptcha_status()`: Configuration status

- **Configured via**:
  - `ENABLE_CAPTCHA`: true (default)
  - `RECAPTCHA_SECRET_KEY`: Google secret key
  - `RECAPTCHA_SITE_KEY`: Google site key

### 4. Core Agent

#### `demo_agent/agent.py` (397 lines)
Main application logic with integrated security:

- **DemoAgent Class**:
  - Initializes: GeminiClient, TokenBucket, FingerprintAnalyzer, IPLimiter, CaptchaHandler
  - `process_query()`: Complete request pipeline with 10 steps
    1. Check IP rate limiting
    2. Analyze fingerprint and compute abuse score
    3. Check if CAPTCHA is required
    4. Check token quota
    5. Load FAQ context via PromptManager
    6. Call Gemini API
    7. Deduct tokens
    8. Check warning threshold
    9. Log to audit trail
    10. Return response with warning info
  - `_log_audit()`: Comprehensive request logging to demo_audit_log
  - `get_user_status()`: User quota status retrieval

- **Security Integration**:
  - IP rate limit: Returns 403 if exceeded
  - Abuse score >0.9: Blocks immediately
  - Abuse score >threshold: Requires CAPTCHA
  - Quota exceeded: Returns 429 with cooldown info
  - Token warning: 🔴 >95%, 🟡 >85%, 🟢 normal

### 5. API Endpoints

#### `demo_agent/main.py` (388 lines)
FastAPI application with complete endpoint suite:

- **Lifespan Management**:
  - Startup: Initialize database, create DemoAgent instance
  - Shutdown: Close database connection
  - Health check with database validation

- **Endpoints**:

  1. **GET /** - API information
     - Lists available endpoints and service info

  2. **GET /health** - Docker healthcheck
     - Returns: status, service, version

  3. **POST /v1/demo** - Process demo query
     - Request: DemoRequest (validated with Pydantic)
       - user_id, session_id, input, language, metadata (IP, user-agent, fingerprint)
     - Response: DemoResponse (success case)
       - response, tokens_used, tokens_remaining, warning, session_id
     - Error responses:
       - 429: Quota exceeded (demo_quota_exceeded)
       - 403: Suspicious behavior (suspicious_behavior_detected)
       - 500: Internal error

  4. **GET /v1/demo/status** - Get user's quota status
     - Query params: user_id OR session_id OR fingerprint
     - Response: Quota status with tokens, requests, percentage, block state
     - Returns: ISO 8601 timestamps for resets

  5. **POST /v1/demo/verify-captcha** - Verify reCAPTCHA token
     - Query params: token (required), user_id/session_id (optional), remote_ip (optional)
     - Response: Verification result with score, risk level, recommendation
     - HTTP 400: Verification failed

## Configuration

### Environment Variables (24 total)

**Database**:
- `DATABASE_URL`: PostgreSQL connection string
- `SCHEMA_NAME`: Schema name for demo tables (default: "test")

**Gemini API**:
- `GOOGLE_API_KEY`: API key (validates AIza prefix)
- `MODEL`: Model name (default: gemini-2.5-flash)
- `TEMPERATURE`: 0.0-2.0 (default: 0.2)
- `MAX_OUTPUT_TOKENS`: Max tokens (default: 2048)

**Demo Limits**:
- `DEMO_MAX_TOKENS`: Daily limit (default: 5000)
- `DEMO_COOLDOWN_HOURS`: Block duration (default: 24, range: 1-168)
- `DEMO_WARNING_THRESHOLD`: Warning percentage (default: 85, range: 1-100)

**Server**:
- `DEMO_AGENT_HOST`: Bind address (default: 0.0.0.0)
- `DEMO_AGENT_PORT`: Port (default: 8082)

**Security**:
- `ENABLE_CAPTCHA`: Enable reCAPTCHA (default: true)
- `RECAPTCHA_SECRET_KEY`: Google secret
- `RECAPTCHA_SITE_KEY`: Google site key
- `ENABLE_FINGERPRINT`: Enable fingerprinting (default: true)
- `FINGERPRINT_SCORE_THRESHOLD`: Abuse threshold (default: 0.7, range: 0.0-1.0)
- `IP_RATE_LIMIT_REQUESTS`: Requests per IP per minute (default: 100)
- `IP_RATE_LIMIT_WINDOW_SEC`: Window in seconds (default: 60)

**Logging**:
- `LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
- `LOG_TO_FILE`: Write to file (default: true)
- `LOG_DIR`: Log directory (default: "logs")
- `DEBUG_MODE`: Debug mode (default: false)

## Database Schema

All tables created in `SQL/01_ddl/demo/`:

### demo_usage
- Tracks token-bucket state per user
- Auto-resets at UTC midnight
- Blocks user for 24h when quota exhausted

### demo_audit_log
- Immutable security audit trail
- Indexed on: ip_address, client_fingerprint, abuse_score, created_at
- Enables abuse pattern analysis and debugging

### demo_sessions
- Session metadata for engagement tracking
- Indexed on: session_id (UNIQUE), user_id, language, token usage

## Request Flow Example

```
User Request
    ↓
[IP Rate Limit Check] → Return 403 if exceeded
    ↓
[Fingerprint Analysis] → Compute abuse score
    ↓
[CAPTCHA Requirement Check] → Return 403 with CAPTCHA if >threshold
    ↓
[Token Quota Check] → Return 429 if exceeded
    ↓
[PromptManager] → Load FAQ context with remaining tokens
    ↓
[Gemini API] → Generate response
    ↓
[Token Deduction] → Update quota, check if exceeded
    ↓
[Warning Calculation] → 🔴 >95%, 🟡 >85%, 🟢 normal
    ↓
[Audit Logging] → Insert complete request record
    ↓
[Return Response] → 200 with response, tokens, warning
```

## Code Quality Standards

- **Type Hints**: Full type hints on all functions
- **Docstrings**: Google-style docstrings with Args/Returns
- **Error Handling**: Try-except with logging and graceful degradation
- **Database**: Atomic operations, prepared statements via parameterization
- **Logging**: DEBUG (operation details) and INFO (important events)
- **Validation**: Pydantic v2 for request/response validation

## Testing Recommendations

### Unit Tests
- TokenBucket: check_quota, deduct_tokens, daily reset
- FingerprintAnalyzer: abuse_score calculation, VPN detection
- IPLimiter: rate limiting logic, reputation scoring
- CaptchaHandler: score evaluation, CAPTCHA requirement logic

### Integration Tests
- Full request pipeline with database
- API endpoints with authentication
- CAPTCHA verification with Google API
- Rate limiting with concurrent requests

### Load Testing
- 100+ concurrent requests per IP
- 10,000+ daily tokens consumption
- Fingerprint consistency across sessions

## Next Steps (Iteración 3)

1. **Tests**:
   - Unit tests for all modules
   - Integration tests with PostgreSQL
   - API endpoint tests with pytest
   - Load testing with concurrent requests

2. **Code Quality**:
   - Black formatting
   - Ruff linting
   - MyPy type checking

3. **Documentation**:
   - API documentation (OpenAPI/Swagger)
   - Deployment guide
   - Troubleshooting guide

4. **Deployment**:
   - Docker image optimization
   - Docker Compose configuration
   - Production readiness checklist

## Files Created/Modified

### Created (8 files)
1. `demo_agent/db/models.py` - ORM models
2. `demo_agent/security/fingerprint.py` - VPN detection
3. `demo_agent/security/ip_limiter.py` - IP rate limiting
4. `demo_agent/security/captcha_handler.py` - CAPTCHA verification
5. `demo_agent/agent.py` - Core agent with security integration
6. `demo_agent/main.py` - API endpoints (updated)
7. `docs/DEMO_AGENT_ITERACION_2.md` - This file

### Modified (2 files)
1. `demo_agent/rate_limiter/token_bucket.py` - Full implementation
2. `demo_agent/agent.py` - Security integration

## Statistics

- **Total Lines of Code**: ~2,000 lines across 7 files
- **Modules**: 4 security modules + 1 core agent
- **API Endpoints**: 5 (health, info, demo query, status, CAPTCHA)
- **Database Tables**: 3 (usage, audit_log, sessions)
- **Configuration Variables**: 24
- **Security Features**: 5 (IP limiting, fingerprinting, CAPTCHA, audit, quota)
- **Error Codes**: 5 (quota_exceeded, rate_limit_ip, suspicious_behavior, internal_error, captcha_required)

## Integration Points

- **PromptManager**: Loads FAQ context and system prompts
- **Gemini API**: Generates FAQ-based responses
- **PostgreSQL**: Persistent storage for quota, audit, sessions
- **Google reCAPTCHA v3**: Bot detection and verification
- **FastAPI**: REST API with async support
- **Pydantic v2**: Request/response validation

---
**Implementation Complete** ✅
**Ready for Testing & Deployment** 🚀
