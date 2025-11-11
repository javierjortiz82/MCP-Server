# Demo Agent - Executive Summary

## Architecture Overview

The demo_agent is a **FastAPI-based AI assistant service** that provides FAQ-style responses using Google Gemini API, with comprehensive rate limiting, authentication, and security controls.

### Core Components

| Module | Purpose | Status |
|--------|---------|--------|
| **main.py** | FastAPI app, endpoints, lifecycle | ✅ Complete |
| **agent.py** | Query processing, security orchestration | ✅ Complete |
| **config/settings.py** | Configuration with Pydantic validation | ✅ Complete |
| **db/connection.py** | PostgreSQL connection management | ⚠️ Needs pooling |
| **gemini_client.py** | Gemini API integration | ⚠️ Token counting inaccurate |
| **auth_endpoints.py** | Authentication (register, OTP, OAuth) | ✅ Complete |
| **services/** | User, OTP, Email services | ✅ Complete |
| **security/** | CAPTCHA, Fingerprinting, IP limiting | ⚠️ Some incomplete |
| **rate_limiter/token_bucket.py** | Daily quota management | ⚠️ Incomplete |
| **logger.py** | Logging setup | ✅ Complete |

---

## Request Flow

```
User Request
    ↓
[Authentication Check]
    ↓
[Security Checks: IP Limit → Fingerprint → CAPTCHA]
    ↓
[Rate Limiting: Token Bucket Check]
    ↓
[Gemini API Call]
    ↓
[Token Deduction]
    ↓
[Audit Logging]
    ↓
Response with quota status
```

---

## Security Layers

| Layer | Mechanism | Configurable |
|-------|-----------|-------------|
| **1. IP Rate Limiting** | 100 requests/IP/min | ✅ Yes |
| **2. Fingerprinting** | Device profiling, abuse score | ✅ Yes |
| **3. CAPTCHA** | Google reCAPTCHA v3 | ✅ Yes |
| **4. Token Bucket** | 5000 tokens/user/day | ✅ Yes |
| **5. Audit Logging** | Immutable request trail | ✅ Yes |

---

## Key Endpoints

### Authentication
- `POST /v1/auth/register` - Email/password registration
- `POST /v1/auth/register/oauth` - OAuth (Google, Apple)
- `POST /v1/auth/verify-otp` - OTP verification
- `POST /v1/auth/resend-otp` - Resend OTP

### Demo Service
- `POST /v1/demo` - Query with rate limiting
- `GET /v1/demo/status` - Quota status
- `POST /v1/demo/verify-captcha` - CAPTCHA verification

### System
- `GET /health` - Health check
- `GET /` - API info

---

## Configuration

Key environment variables:
- `DATABASE_URL` - PostgreSQL connection
- `SCHEMA_NAME` - DB schema name
- `GOOGLE_API_KEY` - Gemini API key (starts with "AIza")
- `RECAPTCHA_SECRET_KEY` - reCAPTCHA secret
- `RECAPTCHA_SITE_KEY` - reCAPTCHA site key
- `DEMO_MAX_TOKENS` - Daily quota (default: 5000)
- `DEMO_COOLDOWN_HOURS` - Block duration (default: 24)
- `ENABLE_CAPTCHA` - Enable reCAPTCHA (default: true)
- `ENABLE_FINGERPRINT` - Enable fingerprinting (default: true)

---

## Critical Issues (Must Fix Before Production)

### 🔴 Severity: CRITICAL

1. **Token Counting Inaccurate** (gemini_client.py:90-94)
   - Uses word count instead of actual token counting
   - Could use 2x more tokens than expected
   - Fix: Implement actual Gemini token counting API

2. **User Lookup Bug** (main.py:392)
   - Looks up by email instead of user_id
   - Comment: "Better: lookup by user_id"
   - Fix: Query directly by user_id parameter

3. **Database Not Async-Safe** (db/connection.py)
   - Synchronous psycopg2 in async context
   - Blocking I/O in event loop
   - Fix: Switch to asyncpg or add connection pool

4. **OTP Expiration Too Long** (services/otp_service.py:51)
   - 24 hours enables brute force attacks
   - Industry standard: 5-15 minutes
   - Fix: Reduce to 5-15 minute window

5. **Token Refund Missing** (agent.py:266)
   - No refund if Gemini API fails
   - Users lose quota on failed requests
   - Fix: Refund tokens on API errors

### 🟡 Severity: HIGH

6. **OAuth Tokens Not Validated** (auth_endpoints.py:156)
   - Trusts client-provided OAuth data
   - Account takeover possible
   - Fix: Validate with OAuth provider

7. **Information Disclosure** (services/user_service.py:76)
   - Error messages reveal if email exists
   - Enables email enumeration
   - Fix: Use generic error messages

8. **Missing CAPTCHA on Registration** (auth_endpoints.py:29)
   - No bot protection during signup
   - Enables mass account creation
   - Fix: Add CAPTCHA to registration

9. **Rate Limit Timing Leaks** (auth_endpoints.py:380)
   - Returns exact cooldown_seconds
   - Enables timing attacks
   - Fix: Use vague messages ("Try again later")

---

## Performance Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| No connection pooling | Bottleneck at high concurrency | Use psycopg2.pool or asyncpg |
| Sync DB in async app | Blocking I/O, reduced concurrency | Switch to asyncpg driver |
| No query caching | CPU overhead on every request | Use prepared statements |
| No retry logic | Cascading failures on API errors | Add exponential backoff |
| No FAQ caching | Redundant PromptManager calls | Cache in memory or Redis |

---

## Well-Implemented Areas

✅ **Password Security**: BCrypt 12 rounds, strong validation
✅ **OTP Security**: SHA-256, constant-time comparison, rate limiting
✅ **Audit Logging**: Comprehensive, immutable trail with indexes
✅ **Config Management**: Pydantic v2 with validators
✅ **Error Handling**: Try/catch everywhere, graceful degradation
✅ **Logging**: Rotating file handler, console output

---

## Incomplete Modules

The following files are truncated in the codebase analysis:
- `security/fingerprint.py` - Missing `compute_abuse_score()` implementation
- `security/ip_limiter.py` - Missing rest of `get_ip_stats()`
- `rate_limiter/token_bucket.py` - Missing `deduct_tokens()` and `get_quota_status()`
- `services/user_service.py` - Missing several methods
- `services/otp_service.py` - Missing `create_otp()` and `verify_otp()`

**Action**: Complete implementations and add unit tests.

---

## Recommendations (Priority)

### P0 - Fix Before Production
1. Fix user_id lookup (main.py:392)
2. Implement actual Gemini token counting
3. Add token refund on API errors
4. Fix database connection (async-safe)
5. Reduce OTP expiration to 5 minutes
6. Validate OAuth tokens with provider

### P1 - Fix Before High Load
1. Implement connection pooling
2. Add connection pool monitoring
3. Implement retry logic with backoff
4. Add FAQ caching
5. Add query result caching

### P2 - Nice to Have
1. Structured logging (JSON format)
2. Request correlation IDs
3. Performance metrics (latency, throughput)
4. Geolocation-based abuse detection
5. Session token authentication

---

## Testing Status

**Test files**: 11 test modules found
- E2E tests (test_e2e.py, test_e2e_simple.py)
- Unit tests (test_token_bucket.py, test_fingerprint.py, test_ip_limiter.py)
- CAPTCHA tests (test_captcha_handler.py, test_recaptcha_unit.py, test_recaptcha_e2e.py)
- Integration tests (test_costa_rica_provinces_e2e.py, test_real_user_e2e.py, test_demo_endpoint.py)

**Coverage**: Appears good, but verify all critical paths tested.

---

## Database Requirements

### Required Tables
- `demo_users` - User accounts
- `demo_otp_codes` - OTP codes
- `demo_usage` - Token quota tracking
- `demo_audit_log` - Audit trail (immutable)
- `demo_sessions` - Session metadata

### Indexes Needed
- `demo_usage(user_key)` - Token lookups
- `demo_audit_log(created_at)` - Range queries
- `demo_audit_log(ip_address)` - IP reputation
- `demo_audit_log(user_key)` - User forensics

---

## Deployment Checklist

Before production:
- [ ] Fix all CRITICAL issues
- [ ] Run security audit (OWASP Top 10)
- [ ] Run load tests (target: 1000 req/s)
- [ ] Verify database indexes
- [ ] Test failover/recovery
- [ ] Document API endpoints
- [ ] Set up monitoring (errors, latency, quota)
- [ ] Configure alerting thresholds
- [ ] Review logs for sensitive data

---

## Full Analysis

For detailed module-by-module analysis, see:
`/home/javort/alfredo/MCP-Server/docs/DEMO_AGENT_ARCHITECTURE_ANALYSIS.md`
