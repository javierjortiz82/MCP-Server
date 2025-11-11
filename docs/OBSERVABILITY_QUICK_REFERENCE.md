# Observability Quick Reference

**TL;DR** — Copy-paste examples for common observability tasks in Lab01 MCP platform

---

## Setup (In Your Component)

```python
# 1. Import observability
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger
from email_service.observability.context import (
    create_request_context, clear_request_context
)

# 2. Initialize in __init__
def __init__(self):
    self.metrics = get_metrics_collector()
    self.logger = get_structured_logger("my_component")
```

---

## Common Tasks

### Log a message

```python
# Info level
self.logger.info("User registered", user_id=123, email="user@example.com")

# Warning level
self.logger.warning("Slow query detected", duration_ms=450, query_type="search")

# Error level (without exception)
self.logger.error("Payment failed", reason="invalid_card", amount=99.99)

# Exception logging
try:
    risky_operation()
except Exception as e:
    self.logger.exception("Operation failed")  # Auto-includes exception details
```

### Count events

```python
# Success
self.metrics.increment_counter("emails_sent", 1)

# Failure
self.metrics.increment_counter("emails_failed", 1)

# Errors by type
self.metrics.increment_counter("error_SMTPException", 1)
self.metrics.increment_counter("error_TimeoutError", 1)

# Multiple at once
self.metrics.increment_counter("requests_processed", len(batch))
```

### Track current state

```python
# Queue size
self.metrics.set_gauge("queue_size", 150)

# Active connections
self.metrics.set_gauge("active_users", 42)

# Memory usage
self.metrics.set_gauge("memory_used_mb", 512)
```

### Measure operation duration

```python
# Synchronous
with self.metrics.record_latency("database_query_latency"):
    result = db.query("SELECT * FROM users")

# Asynchronous
async with self.metrics.record_latency_async("api_call_latency"):
    response = await external_api.call()

# With tags for better analysis
with self.metrics.record_latency("tool_execution_latency", tags={"tool": "search"}):
    execute_tool("search", params)
```

### Track a request

```python
# At entry point (e.g., API endpoint, message handler)
ctx = create_request_context(
    email_id="email_123",
    recipient="user@example.com",
    operation="send_verification_email"
)

try:
    # Do work...
    self.logger.info("Request processing started")
    result = process_request()
    self.metrics.increment_counter("requests_processed", 1)
    return result
finally:
    clear_request_context()  # Clean up
```

---

## Metrics Summary

### Get current metrics

```python
summary = self.metrics.get_summary()

# Contains:
# {
#   "counters": {"emails_sent": 1000, ...},
#   "gauges": {"queue_size": 150, ...},
#   "latency": {"db_query": {p95: 45, p99: 120}, ...}
# }

# Use for monitoring/logging
print(f"Emails sent: {summary['counters'].get('emails_sent', 0)}")
```

### Export metrics

```python
import json

summary = self.metrics.get_summary()
metrics_json = json.dumps(summary, indent=2)

# Log it
self.logger.info("Metrics snapshot", metrics=metrics_json)

# Export to file
with open("metrics.json", "w") as f:
    json.dump(summary, f, indent=2)
```

---

## Error Handling Pattern

```python
def process_data(data):
    try:
        if self.metrics:
            self.metrics.increment_counter(f"process_{data.type}_attempts", 1)

        result = do_processing(data)

        if self.metrics:
            self.metrics.increment_counter(f"process_{data.type}_successful", 1)

        return result

    except ValueError as e:
        if self.metrics:
            self.metrics.increment_counter("error_ValueError", 1)
        if self.logger:
            self.logger.exception("Validation failed")
        raise

    except Exception as e:
        if self.metrics:
            self.metrics.increment_counter(f"error_{type(e).__name__}", 1)
        if self.logger:
            self.logger.exception("Processing failed")
        raise
```

---

## Async Operations Pattern

```python
async def handle_query(query: str):
    ctx = create_request_context(
        email_id=None,
        recipient=None,
        operation="handle_query"
    )

    try:
        if self.metrics:
            async with self.metrics.record_latency_async("query_processing"):
                # Sub-operation 1
                if self.metrics:
                    async with self.metrics.record_latency_async("step1_latency"):
                        result1 = await step1(query)

                # Sub-operation 2
                if self.metrics:
                    async with self.metrics.record_latency_async("step2_latency"):
                        result2 = await step2(result1)

                return result2
        else:
            return await step2(await step1(query))

    except Exception as e:
        if self.metrics:
            self.metrics.increment_counter(f"error_{type(e).__name__}", 1)
        if self.logger:
            self.logger.exception("Query processing failed")
        raise

    finally:
        clear_request_context()
```

---

## Graceful Degradation

Always protect observability code with checks:

```python
# ✅ CORRECT - Works even if observability unavailable
if self.metrics:
    self.metrics.increment_counter("operation", 1)

if self.logger:
    self.logger.info("Message")

# ❌ WRONG - Crashes if framework unavailable
self.metrics.increment_counter("operation", 1)  # AttributeError
self.logger.info("Message")  # AttributeError
```

---

## Testing

### Reset metrics for tests

```python
from email_service.observability.metrics import reset_metrics_collector

def test_my_feature():
    reset_metrics_collector()
    metrics = get_metrics_collector()

    # Run operation
    my_function()

    # Verify metrics
    summary = metrics.get_summary()
    assert summary["counters"].get("success", 0) >= 1
```

### Mock observability if needed

```python
from unittest.mock import MagicMock

def test_with_mocked_observability():
    # Replace with mock
    metrics = MagicMock()
    logger = MagicMock()

    component = MyComponent()
    component.metrics = metrics
    component.logger = logger

    # Test operation
    component.do_something()

    # Verify calls
    metrics.increment_counter.assert_called_with("operation", 1)
```

---

## What Gets Logged Automatically

Every log message automatically includes:

```json
{
  "timestamp": "2025-11-03T15:30:45.123Z",  // ISO format
  "level": "INFO",                           // Log level
  "logger": "my_component",                  // Component name
  "correlation_id": "a1b2c3d4",             // Request trace ID
  "hostname": "server-01",                   // Server name
  "service": "agent_orchestrator",           // Service name
  "message": "Your message",                 // Your message
  "user_id": 123,                            // Your custom fields
  "email": "user@example.com"                // Your custom fields
}
```

---

## Metrics Naming Convention

Use this naming pattern:

```
{component}_{operation}_{aspect}

Examples:
- email_send_attempts       (emails being sent - attempted)
- email_send_successful     (emails successfully sent)
- db_query_latency         (database query duration)
- agent_response_latency   (agent generating response)
- mcp_tool_call_latency    (MCP tool execution)
```

---

## Per-Service Quick References

### Email Service
```python
# Metrics
metrics.increment_counter("email_send_attempts", 1)
metrics.increment_counter("smtp_send_successful", 1)
metrics.set_gauge("email_queue_size", current_size)

# Logging
logger.info("Email queued", email_id="abc123", recipient="user@example.com")
```

### Agent Services
```python
# Metrics
metrics.increment_counter("agent_queries_received", 1)
metrics.increment_counter("router_intent_sales", 1)
metrics.set_gauge("agent_history_size", len(history))

# Logging
logger.info("Query classified", intent="sales", confidence=0.95)
```

### Client MCP
```python
# Metrics
metrics.increment_counter("mcp_tool_call_attempt_search", 1)
with metrics.record_latency("tool_execution_latency", tags={"tool": "search"}):
    execute_tool()

# Logging
logger.info("Tool executed", tool="search", result_count=5)
```

### MCP Server
```python
# Metrics
metrics.increment_counter("db_query_fetchall_attempts", 1)
metrics.set_gauge("db_result_count", len(results))
with metrics.record_latency("search_vector_search_latency"):
    search()

# Logging
logger.info("Vector search completed", results=5, query="laptop")
```

---

## Monitor Command Examples

```bash
# Watch metrics in real-time (example scripts)
watch -n 1 'python -c "from email_service.observability.metrics import get_metrics_collector; import json; print(json.dumps(get_metrics_collector().get_summary(), indent=2))"'

# Export metrics to file
python -c "
from email_service.observability.metrics import get_metrics_collector
import json
with open('metrics.json', 'w') as f:
    json.dump(get_metrics_collector().get_summary(), f, indent=2)
"

# Check specific metric
python -c "
from email_service.observability.metrics import get_metrics_collector
summary = get_metrics_collector().get_summary()
print(f\"Emails sent: {summary['counters'].get('email_send_successful', 0)}\")
"
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Module not found" | Add `/path/to/MCP-Server` to `PYTHONPATH` |
| Metrics always zero | Check if code is actually running |
| Context lost in async | Framework handles this automatically |
| Logs not appearing | Check logging level configuration |
| High latency readings | Normal for large operations, check p95/p99 |

---

## Framework Locations

```
email_service/observability/           # Core framework
├── __init__.py                        # Exports
├── structured_logger.py               # Logging
├── metrics.py                         # Metrics
├── context.py                         # Request context
└── correlation.py                     # Correlation IDs

# Usage in:
- agent/src/gemini_agent/*.py
- agent/src/multi_agent/*.py
- client_mcp/core/*.py
- client_mcp/strategies/*.py
- mcp_server/*.py
```

---

## See Also

- [Full Implementation Guide](./OBSERVABILITY_IMPLEMENTATION_GUIDE.md)
- [Audit Report](./OBSERVABILITY_AUDIT_REPORT.md)
- [Integration Tests](../tests/test_platform_observability_integration.py)
- [Framework Source](../email_service/observability/)
