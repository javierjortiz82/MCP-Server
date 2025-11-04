# Demo Agent

Demo agent with token-bucket rate limiting, FAQ-based responses, and security-hardened access control.

## Overview

The Demo Agent provides a limited-scope AI assistant powered by Google Gemini API that:
- **Limits responses to FAQ content only** (prevents hallucinations)
- **Tracks token consumption** per user (5,000 tokens/day default)
- **Implements rate-limiting** via token-bucket algorithm (PostgreSQL-backed)
- **Detects and blocks abuse** via IP reputation, fingerprinting, and CAPTCHA
- **Caches FAQs** from Jinja2 templates for efficient delivery

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 13+
- Google Gemini API key

### Local Development

```bash
# 1. Navigate to demo_agent directory
cd demo_agent

# 2. Create .env file from template
cp .env.example .env
# Edit .env with your configuration

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python -m demo_agent.main

# 5. Test endpoint
curl -X POST http://localhost:8082/v1/demo \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "input": "¿Cuánto cuesta un laptop?",
    "language": "es",
    "metadata": {
      "ip": "127.0.0.1",
      "user_agent": "curl/7.64.1"
    }
  }'
```

### Docker Deployment

```bash
# 1. Start all services (with demo_agent)
cd DockerConfig
docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d

# 2. Check logs
docker logs -f demo-agent

# 3. Test health check
curl http://localhost:8082/health

# 4. Test demo endpoint
curl -X POST http://localhost:8082/v1/demo \
  -H "Content-Type: application/json" \
  -d '{...}'
```

## Configuration

All settings configured via environment variables (see `.env.example`):

### Demo Limits
- `DEMO_MAX_TOKENS`: Maximum tokens per user per day (default: 5000)
- `DEMO_COOLDOWN_HOURS`: Hours to block user after quota exhaustion (default: 24)
- `DEMO_WARNING_THRESHOLD`: Percentage to show warning (default: 85%)

### Security
- `ENABLE_CAPTCHA`: Enable reCAPTCHA v3 (default: true)
- `ENABLE_FINGERPRINT`: Enable client fingerprinting (default: true)
- `FINGERPRINT_SCORE_THRESHOLD`: Abuse detection threshold (default: 0.7)
- `IP_RATE_LIMIT_REQUESTS`: Requests per IP per minute (default: 100)

### Gemini API
- `GOOGLE_API_KEY`: Google Gemini API key (required)
- `MODEL`: Model to use (default: gemini-2.5-flash)
- `TEMPERATURE`: Model temperature (default: 0.2)

## Architecture

### Token-Bucket Rate Limiting

Uses PostgreSQL-backed token bucket algorithm:

1. **Per-User Tracking**: `demo_usage` table stores user quota state
2. **Daily Reset**: Automatic reset at UTC midnight
3. **Token Deduction**: Each request deducts consumed tokens
4. **Block State**: Blocks user for 24h when quota exceeded

### Audit Logging

Complete audit trail in `demo_audit_log` table:
- IP address, fingerprint, user agent
- Tokens consumed, response length
- Block reason and action taken
- Abuse score (0.0-1.0)

### FAQ Content

FAQs loaded from `prompts/data/demo_faqs.yaml`:
- Organized by category (Products, Shipping, Payment, Support)
- Single source of truth for demo responses
- Auto-cached for performance

## API Endpoints

### POST /v1/demo
Demo query endpoint with token tracking.

**Request:**
```json
{
  "user_id": "user_123",              // Optional: authenticated user
  "session_id": "sess_abc",           // Optional: anonymous session
  "input": "¿Cuánto cuesta un laptop?",
  "language": "es",                   // Optional: es|en (default: es)
  "metadata": {
    "ip": "203.0.113.42",             // Required: client IP
    "user_agent": "Mozilla/5.0...",   // Optional
    "fingerprint": "hash123"          // Optional: client fingerprint
  }
}
```

**Success Response (200):**
```json
{
  "success": true,
  "response": "Los laptops varían entre $500 y $3000...",
  "tokens_used": 250,
  "tokens_remaining": 4750,
  "warning": {
    "is_warning": false,
    "message": null,
    "percentage_used": 5
  },
  "session_id": "sess_abc",
  "created_at": "2025-10-31T12:30:45Z"
}
```

**Quota Exceeded (429):**
```json
{
  "success": false,
  "error": "demo_quota_exceeded",
  "message": "Demo bloqueada. Límite de 5,000 tokens alcanzado. Reintenta en 18 horas.",
  "retry_after_seconds": 64800,
  "blocked_until": "2025-11-01T12:30:45Z"
}
```

**Suspicious Behavior (403):**
```json
{
  "success": false,
  "error": "suspicious_behavior_detected",
  "message": "Actividad sospechosa detectada. Completa CAPTCHA para continuar.",
  "action_required": "captcha",
  "captcha_token_required": true,
  "abuse_score": 0.78
}
```

### GET /v1/demo/status
Get current user's quota status.

**Response:**
```json
{
  "tokens_used": 1250,
  "tokens_remaining": 3750,
  "percentage_used": 25,
  "requests_count": 5,
  "is_blocked": false,
  "blocked_until": null,
  "last_reset": "2025-10-31T00:00:00Z",
  "next_reset": "2025-11-01T00:00:00Z"
}
```

### GET /health
Health check endpoint (for Docker healthchecks).

**Response:**
```json
{
  "status": "ok",
  "service": "demo_agent",
  "version": "1.0.0"
}
```

## Database Schema

### demo_usage
Token-bucket state per user:
- `user_key`: Unique identifier (user_id | session_id | fingerprint)
- `tokens_consumed`: Cumulative tokens used today
- `requests_count`: Number of requests today
- `is_blocked`: Whether user is blocked
- `blocked_until`: When block expires
- `last_reset`: When daily quota was reset

### demo_audit_log
Immutable audit trail:
- `user_key`: User identifier
- `ip_address`: Client IP
- `client_fingerprint`: Device fingerprint
- `tokens_used`: Tokens in this request
- `abuse_score`: Suspicious behavior score (0.0-1.0)
- `block_reason`: Why request was rejected (if applicable)
- `action_taken`: System action (allowed, blocked, captcha_required, etc.)

### demo_sessions
Session metadata:
- `user_id`: Authenticated user
- `session_id`: Session token
- `language`: Language preference
- `total_tokens_used`: Cumulative for session
- `total_requests`: Request count
- `last_activity_at`: Last interaction timestamp

## Integration with Lab01-MCP

### PromptManager
Demo Agent uses `PromptManager.get_demo_prompt()` to load FAQs and generate system prompts:

```python
from agent.src.multi_agent.prompt_manager import PromptManager

manager = PromptManager()
prompt = manager.get_demo_prompt(
    remaining_tokens=4750,
    user_lang="es"
)
```

### Database Schema
Shares PostgreSQL schema with other Lab01-MCP services:
- Same connection pool
- Automatic migrations via SQL scripts
- Transactional consistency

### Logging
Consistent with `email_service` and `mcp_server`:
- Rotating file handlers
- Structured logging
- Configurable levels (DEBUG, INFO, WARNING, ERROR)

## Development

### Code Quality

```bash
# Format with black
black demo_agent/

# Lint with ruff
ruff check demo_agent/

# Type check with mypy
mypy demo_agent/

# Run tests
pytest tests/
```

### Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires PostgreSQL)
pytest tests/integration/

# Coverage report
pytest --cov=demo_agent tests/
```

## Security Considerations

### Token-Bucket Algorithm
- **Atomic Operations**: PostgreSQL `UPDATE` queries are atomic
- **No Race Conditions**: Single authoritative DB
- **TTL Management**: Blocks expire automatically

### Abuse Detection
1. **IP Rate Limiting**: Track requests per IP per minute
2. **Fingerprinting**: Detect VPN/proxy rotation
3. **Pattern Analysis**: Flag rapid quota consumption
4. **CAPTCHA**: Trigger on suspicious behavior
5. **Audit Trail**: All actions logged for review

### Defense in Depth
- Input sanitization (max length, type validation)
- Request validation (Pydantic)
- Rate limiting (IP + user + token-bucket)
- Fingerprinting (client detection)
- CAPTCHA (human verification)

## Monitoring & Observability

### Logs Location
- Local: `logs/demo_agent.log`
- Docker: `docker logs demo-agent`

### Key Metrics
- `tokens_used` per user per day
- `abuse_score` distribution
- `requests_per_ip` patterns
- `response_time` latency
- `error_rate` tracking

### Alerts (recommended)
- 90% quota used: notify user
- Block triggered: log for review
- High abuse_score: manual review
- Error rate > 5%: alert ops

## Troubleshooting

### "GOOGLE_API_KEY must start with 'AIza'"
Invalid API key format. Check `.env` file.

### "Demo quota exceeded"
Normal behavior. User has used 5,000 tokens. Unblocks in 24h.

### "PostgreSQL connection failed"
Check:
1. `DATABASE_URL` in `.env`
2. PostgreSQL is running: `docker ps | grep postgres`
3. Credentials are correct
4. Network connectivity

### "CAPTCHA required"
Suspicious behavior detected. User must complete reCAPTCHA v3.

## Performance

- **Response Time**: ~500ms-2s (Gemini API latency)
- **Token Counting**: <10ms (local)
- **Rate Limiting**: <5ms (PostgreSQL query)
- **FAQ Loading**: Cached for 60 minutes

## Future Enhancements

- [ ] Redis caching for rate-limiting (performance optimization)
- [ ] Advanced analytics dashboard
- [ ] A/B testing support
- [ ] Multi-language FAQ management UI
- [ ] GraphQL API endpoint
- [ ] Webhook notifications for quota alerts

## Contributing

See `CONTRIBUTING.md` for code review checklist and best practices.

## License

MIT License - See LICENSE file for details.

## Authors

Lab01-MCP Team - October 2025
