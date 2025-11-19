# Session Expiration System Implementation Guide

## Overview

A comprehensive session expiration mechanism has been implemented following OWASP & NIST standards. Sessions automatically expire based on three configurable timeout criteria, ensuring users must re-authenticate when sessions are no longer valid.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Session Management Configuration - SECURITY CRITICAL
# Follow OWASP & NIST guidelines:
# https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

# Session Time-To-Live (TTL) in minutes
# Total maximum session duration regardless of activity
# Range: 5-1440 minutes
# RECOMMENDED: 30-60 minutes for sensitive apps, 480-720 for less sensitive
# Default: 30 minutes
SESSION_TTL_MINUTES=30

# Session Idle Timeout in minutes
# Inactivity period before automatic re-authentication required
# If user is inactive for this duration, session expires
# Range: 1-720 minutes
# RECOMMENDED: 15-30 minutes (typical web apps use 15-20 minutes)
# Default: 15 minutes
SESSION_IDLE_TIMEOUT_MINUTES=15

# Session Absolute Timeout in minutes
# Maximum lifetime of a session regardless of activity
# Even with continuous activity, session expires after this duration
# Range: 60-1440 minutes
# RECOMMENDED: 480-720 minutes (8-12 hours per OWASP)
# Default: 480 minutes (8 hours)
SESSION_ABSOLUTE_TIMEOUT_MINUTES=480
```

### Settings File

Configuration is automatically loaded in `demo_agent/config/settings.py`:

```python
SESSION_TTL_MINUTES: int = Field(
    default=30,
    ge=5,
    le=1440,
    description="Session time-to-live in minutes (5-1440 recommended, 30 default)",
)
SESSION_IDLE_TIMEOUT_MINUTES: int = Field(
    default=15,
    ge=1,
    le=720,
    description="Inactivity timeout in minutes before requiring re-authentication",
)
SESSION_ABSOLUTE_TIMEOUT_MINUTES: int = Field(
    default=480,
    ge=60,
    le=1440,
    description="Absolute session lifetime in minutes regardless of activity (8 hours default)",
)
```

## System Architecture

### 1. DemoSession Model (`demo_agent/db/models.py`)

Enhanced with session expiration logic:

```python
class DemoSession(Base):
    """Session metadata and engagement tracking."""

    def is_expired(self, ttl_minutes, idle_timeout_minutes, absolute_timeout_minutes) -> bool:
        """Check if session has expired based on multiple timeout criteria."""

    def get_expiration_reason(self, ttl_minutes, idle_timeout_minutes, absolute_timeout_minutes) -> str:
        """Get human-readable reason for expiration (idle_timeout, ttl, absolute_timeout)."""

    def update_activity(self) -> None:
        """Update session's last activity timestamp to current time."""
```

### 2. SessionService (`demo_agent/services/session_service.py`)

Core service for session management:

```python
class SessionService:
    @staticmethod
    def is_session_expired(session: DemoSession) -> bool:
        """Check if session has expired."""

    @staticmethod
    def get_expiration_reason(session: DemoSession) -> Optional[str]:
        """Get expiration reason."""

    @staticmethod
    def update_session_activity(db: DbSession, session: DemoSession, tokens_used: int = 0) -> DemoSession:
        """Update session activity and token tracking."""

    @staticmethod
    def invalidate_session(db: DbSession, session: DemoSession) -> bool:
        """Invalidate/delete an expired session."""

    @staticmethod
    def cleanup_expired_sessions(db: DbSession) -> int:
        """Delete all expired sessions from database."""
```

### 3. SessionExpiryMiddleware (`demo_agent/security/session_expiry_middleware.py`)

Middleware that validates session expiration on each request:

- Checks if request is to a public/protected route
- Retrieves session from database
- Validates expiration
- Updates activity timestamp
- Invalidates expired sessions
- Returns 401 Unauthorized with expiration reason

### 4. CleanupTask (`demo_agent/tasks/cleanup_task.py`)

Background task for periodic cleanup of expired records:

```python
class CleanupTask:
    def cleanup_expired_otp_codes(self) -> int:
        """Delete OTP codes that have expired."""

    def cleanup_expired_sessions(self) -> int:
        """Delete sessions that have exceeded their timeout."""

    def cleanup_all(self) -> dict:
        """Run all cleanup tasks."""
```

## Three-Tier Expiration Logic

The system implements three independent expiration criteria:

### 1. **Idle Timeout** (Default: 15 minutes)
- Session expires if user is **inactive** for this duration
- Each request resets the idle counter
- **Purpose**: Prevent session hijacking on shared/public computers
- **Example**: If user opens the app but doesn't interact, session expires after 15 minutes

### 2. **TTL (Time-To-Live)** (Default: 30 minutes)
- Session expires after **total duration** from creation
- Activity resets this counter
- **Purpose**: Limit maximum time a session can be used
- **Example**: Even if user is constantly active, session expires after 30 minutes

### 3. **Absolute Timeout** (Default: 8 hours)
- Session **NEVER** lasts longer than this duration
- Cannot be reset by activity
- **Purpose**: Force re-authentication even for long active sessions
- **Example**: User cannot have session longer than 8 hours, no matter what

## Integration Steps

### Step 1: Add Middleware to FastAPI App

```python
from fastapi import FastAPI
from demo_agent.security.session_expiry_middleware import SessionExpiryMiddleware

app = FastAPI()

# Add after Clerk middleware but before route handlers
app.add_middleware(SessionExpiryMiddleware)
```

### Step 2: Use in Route Handlers

```python
from fastapi import Request
from demo_agent.security.session_expiry_middleware import get_session_from_request
from demo_agent.services.session_service import SessionService

@app.post("/v1/demo")
async def demo_query(request_data: DemoRequest, request: Request):
    # Get validated session from middleware
    session = get_session_from_request(request)

    if session:
        # Update activity on each request
        SessionService.update_session_activity(db, session, tokens_used=request_tokens)

        # Get session statistics
        stats = SessionService.get_session_stats(session)
        print(f"Session duration: {stats['duration_seconds']} seconds")
```

### Step 3: Schedule Cleanup Tasks

#### Using APScheduler (Recommended):

```python
from apscheduler.schedulers.background import BackgroundScheduler
from demo_agent.tasks.cleanup_task import run_cleanup_tasks

def start_cleanup_scheduler(app):
    scheduler = BackgroundScheduler()

    # Run cleanup hourly
    scheduler.add_job(
        run_cleanup_tasks,
        'interval',
        hours=1,
        id='cleanup_task',
        name='Cleanup expired OTP codes and sessions'
    )

    scheduler.start()

    # Shutdown scheduler when app stops
    @app.on_event("shutdown")
    def shutdown_scheduler():
        scheduler.shutdown()

# In main app startup:
app = FastAPI()
start_cleanup_scheduler(app)
```

#### Using Celery:

```python
from celery import Celery
from demo_agent.tasks.cleanup_task import run_cleanup_tasks

celery_app = Celery('demo_agent')

@celery_app.task
def cleanup_task():
    return run_cleanup_tasks()

# Schedule with celery-beat
celery_app.conf.beat_schedule = {
    'cleanup-hourly': {
        'task': 'demo_agent.celery_tasks.cleanup_task',
        'schedule': 3600,  # Every hour (3600 seconds)
    },
}
```

#### Using Cron (Simple):

```bash
# Run cleanup every hour
0 * * * * cd /path/to/app && python -m demo_agent.tasks.cleanup_task
```

## Testing

### Unit Tests

Run session expiration tests:

```bash
# Test session model methods
pytest demo_agent/tests/test_models.py -v -k "session"

# Test session service
pytest demo_agent/tests/test_services.py -v -k "session"
```

### End-to-End Test

Complete E2E test of session lifecycle:

```bash
pytest demo_agent/tests/test_session_expiration_e2e.py -v

# Or run specific test:
pytest demo_agent/tests/test_session_expiration_e2e.py::TestSessionExpirationE2E::test_e2e_session_lifecycle -v -s
```

### Manual Testing

1. **Create Session** (User registers/authenticates):
   ```bash
   curl -X POST http://localhost:8082/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com"}'
   ```

2. **Verify Session Valid**:
   ```bash
   curl -X POST http://localhost:8082/v1/demo \
     -H "X-Session-ID: sess_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"input": "Test query"}'
   # Should return 200 OK with response
   ```

3. **Simulate Idle Timeout** (Wait or manually modify database):
   ```sql
   UPDATE test.demo_sessions
   SET last_activity_at = NOW() - INTERVAL '16 minutes'
   WHERE session_id = 'sess_xxxxx';
   ```

4. **Verify Session Expired**:
   ```bash
   curl -X POST http://localhost:8082/v1/demo \
     -H "X-Session-ID: sess_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"input": "Test query"}'
   # Should return 401 Unauthorized with:
   # {"error": "SessionExpired", "reason": "idle_timeout", ...}
   ```

5. **Re-authenticate with OTP**:
   ```bash
   # User must log in again
   curl -X POST http://localhost:8082/v1/auth/verify-otp \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "otp_code": "123456"}'
   ```

## Database Schema

The system uses existing `demo_sessions` table:

```sql
CREATE TABLE test.demo_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255),
    session_id VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    language VARCHAR(10) DEFAULT 'es',
    total_tokens_used INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX user_id_idx (user_id),
    INDEX session_id_idx (session_id),
    INDEX created_at_idx (created_at)
);
```

### Important Fields:

- **created_at**: Used for TTL and absolute timeout calculation
- **last_activity_at**: Used for idle timeout calculation
- **session_id**: Unique identifier for session validation

## Error Responses

When session has expired, the API returns 401 Unauthorized:

```json
{
    "success": false,
    "error": "SessionExpired",
    "message": "Session expired (idle_timeout). Please log in again.",
    "reason": "idle_timeout",
    "action": "login",
    "hint": "Your session has expired. Please log in again with OTP verification."
}
```

Possible `reason` values:

- `idle_timeout`: User inactive for configured duration
- `ttl`: Total session duration exceeded
- `absolute_timeout`: Absolute maximum lifetime exceeded
- `session_not_found`: Session doesn't exist in database

## Monitoring & Debugging

### Check Session Status

```python
from demo_agent.services.session_service import SessionService

# Get session details
stats = SessionService.get_session_stats(session)
print(f"""
Session ID: {stats['session_id']}
Expired: {stats['is_expired']}
Expiration Reason: {stats['expiration_reason']}
Duration: {stats['duration_seconds']} seconds
Requests: {stats['total_requests']}
Tokens Used: {stats['total_tokens_used']}
Avg Tokens/Request: {stats['avg_tokens_per_request']}
Created: {stats['created_at']}
Last Activity: {stats['last_activity_at']}
""")
```

### View Cleanup Task Logs

```bash
# Check logs for cleanup task execution
tail -f demo_agent/logs/app.log | grep "Cleanup"

# Expected output:
# INFO - Cleanup: Deleted 5 expired OTP codes
# INFO - Cleanup: Deleted 3 expired sessions
```

### Query Expired Sessions

```sql
-- Find expired sessions (idle timeout example)
SELECT
    session_id,
    user_id,
    last_activity_at,
    NOW() - last_activity_at AS inactive_duration
FROM test.demo_sessions
WHERE NOW() - last_activity_at > INTERVAL '15 minutes'
ORDER BY last_activity_at DESC;

-- Find old sessions (TTL example)
SELECT
    session_id,
    user_id,
    created_at,
    NOW() - created_at AS session_age
FROM test.demo_sessions
WHERE NOW() - created_at > INTERVAL '30 minutes'
ORDER BY created_at DESC;
```

## Security Considerations

### ✅ Implemented

- **Three-tier expiration logic** (OWASP standard)
- **Automatic activity tracking** per request
- **Periodic cleanup** of expired records
- **401 Unauthorized** response for expired sessions
- **Detailed expiration reasons** for debugging
- **Database constraints** on timeout values

### ⚠️ Additional Recommendations

1. **HTTPS Only**: Ensure all session tokens transmitted over HTTPS
2. **Secure Cookies**: Use HTTPOnly, Secure, SameSite flags
3. **CSRF Protection**: Implement CSRF tokens for state-changing operations
4. **Rate Limiting**: Combine with rate limiting on re-authentication endpoints
5. **Logging**: Monitor all session expirations for security events
6. **Encryption**: Consider encrypting sensitive data in session records

## Troubleshooting

### Sessions expiring too quickly

**Problem**: Users report sessions expiring faster than configured.

**Solution**:
1. Check `SESSION_IDLE_TIMEOUT_MINUTES` value in `.env`
2. Verify `last_activity_at` is being updated on each request
3. Check if middleware is properly configured
4. Review logs for cleanup task errors

### Sessions not expiring

**Problem**: Old sessions not being invalidated.

**Solution**:
1. Verify cleanup task is running: `grep "Cleanup" app.log`
2. Check database for old sessions: `SELECT COUNT(*) FROM demo_sessions WHERE created_at < NOW() - INTERVAL '24 hours'`
3. Verify APScheduler/Celery is configured correctly
4. Check middleware is added to FastAPI app

### Re-authentication issues

**Problem**: Users see "session not found" after first login.

**Solution**:
1. Verify session is being created in database
2. Check X-Session-ID header is being sent with requests
3. Verify session_id matches between client and database
4. Check for SQL errors in logs

## Files Modified/Created

### Created:
- `demo_agent/services/session_service.py` - Session management service
- `demo_agent/security/session_expiry_middleware.py` - Expiration middleware
- `demo_agent/tasks/cleanup_task.py` - Cleanup background task
- `demo_agent/tests/test_session_expiration_e2e.py` - E2E tests
- `docs/SESSION_EXPIRATION_IMPLEMENTATION.md` - This guide

### Modified:
- `demo_agent/config/settings.py` - Added SESSION_*_MINUTES configuration
- `demo_agent/db/models.py` - Enhanced DemoSession with expiration methods
- `demo_agent/.env` - Added session configuration values
- `demo_agent/.env.example` - Added session configuration template

## Support & Maintenance

For issues or questions:
1. Check logs in `demo_agent/logs/`
2. Review test file: `demo_agent/tests/test_session_expiration_e2e.py`
3. Run diagnostic query to inspect sessions
4. Contact development team with session_id and error details

## References

- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [NIST SP 800-63B - Authentication](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/advanced/middleware/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)

## Changelog

### v1.0.0 (2025-11-18)

- ✅ Implemented three-tier session expiration logic
- ✅ Created SessionService for centralized session management
- ✅ Added SessionExpiryMiddleware for automatic validation
- ✅ Implemented automatic cleanup task
- ✅ Added comprehensive E2E tests
- ✅ Documentation with integration examples