# Email Service Observability Implementation - OPCIÓN 6

**Status:** Framework Created, Ready for Integration
**Date:** 2025-11-03
**Files Created:** 5 (observability module)
**Integration Tasks:** 4 components

---

## ✅ Completed: Observability Framework

### Files Created

```
email_service/observability/
├── __init__.py              ✅ Module exports
├── correlation.py           ✅ Correlation ID management (UUID4)
├── context.py              ✅ Request context (async-safe)
├── metrics.py              ✅ Metrics collection (latency/counters/gauges)
└── structured_logger.py    ✅ Structured JSON logging with context
```

**All files follow the same pattern as demo_agent OPCIÓN 5.**

---

## 🔧 Integration Tasks Needed

### 1. EmailWorker (processor.py)

**Add to imports:**
```python
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger
from email_service.observability.context import create_request_context, clear_request_context
from email_service.observability.correlation import CorrelationID
```

**In `__init__`:**
```python
def __init__(self):
    self.config = EmailConfig()

    # NEW: Setup observability
    setup_logging(
        log_level=self.config.LOG_LEVEL,
        file_level="DEBUG",
        console_level=self.config.LOG_LEVEL,
        enable_file=self.config.LOG_TO_FILE,
    )

    self.logger = get_structured_logger(__name__)
    self.metrics = get_metrics_collector()

    # ... rest of initialization ...
```

**In `run()` method:**
```python
async def run(self):
    logger.info("Starting email worker loop...")

    cycle_count = 0
    while self.running:
        cycle_count += 1
        try:
            # NEW: Record batch processing time
            async with self.metrics.record_latency_async("batch_processing"):
                await self._process_batch()

            self.metrics.set_gauge("worker_cycles", cycle_count)
        except Exception as e:
            logger.error(f"Cycle #{cycle_count}: Error", exc_info=True)
            self.metrics.increment_counter("worker_cycles_failed")

        await asyncio.sleep(self.config.EMAIL_WORKER_POLL_INTERVAL)
```

**In `_process_email()` method:**
```python
async def _process_email(self, email: EmailRecord):
    # NEW: Create request context for this email
    ctx = create_request_context(
        email_id=email.id,
        recipient=email.recipient_email,
        operation="send_email"
    )

    try:
        # NEW: Log with context
        self.logger.info(
            "Processing email",
            email_id=email.id,
            recipient=email.recipient_email,
            email_type=email.type.value
        )

        # ... existing code ...

        # NEW: Latency tracking
        async with self.metrics.record_latency_async(
            "email_send",
            tags={"recipient": email.recipient_email}
        ):
            # Send email via SMTP
            self.smtp_client.send_email(...)

        self.logger.info("Email sent successfully", email_id=email.id)
        self.metrics.increment_counter("emails_sent")

    except Exception as e:
        self.logger.exception("Email sending failed", email_id=email.id)
        self.metrics.increment_counter("emails_failed")
        self._handle_send_failure(email, str(e))
    finally:
        clear_request_context()
```

**Key Metrics to Add:**
- `batch_processing` - Latency for processing email batches
- `email_send` - Latency for sending individual emails
- `template_render` - Latency for template rendering (in _prepare_email_content)
- `emails_sent` - Counter for successful sends
- `emails_failed` - Counter for failed sends
- `emails_retried` - Counter for retries
- `worker_cycles` - Gauge for cycle count
- `queue_size` - Gauge for pending emails in queue

---

### 2. SMTPClient (clients/smtp.py)

**Add to imports:**
```python
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger
```

**In `__init__`:**
```python
def __init__(self, smtp_config: SMTPConfig | None = None):
    self.logger = get_structured_logger(__name__)
    self.metrics = get_metrics_collector()

    # ... existing initialization ...
```

**In `send_email()` method:**
```python
def send_email(self, recipient_email, recipient_name, subject, body_html, body_text=None):
    try:
        self.logger.debug(
            "Building MIME message",
            recipient=recipient_email,
            subject=subject
        )

        # MIME message construction...
        msg = MIMEMultipart("alternative")
        # ... existing code ...

        # NEW: Latency tracking for SMTP connection and send
        with self.metrics.record_latency("smtp_send", tags={"recipient": recipient_email}):
            with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout) as server:
                if self.config.use_tls:
                    server.starttls()
                    self.logger.debug("TLS connection established")

                server.login(self.config.username, self.config.password)
                server.send_message(msg)

        self.logger.info(
            "Email sent via SMTP",
            recipient=recipient_email,
            subject=subject
        )
        self.metrics.increment_counter("smtp_sends_successful")

    except Exception as e:
        self.logger.exception("SMTP send failed", recipient=recipient_email)
        self.metrics.increment_counter("smtp_sends_failed")
        raise SMTPClientError(f"Failed to send email: {e}") from e
```

**Key Metrics to Add:**
- `smtp_send` - SMTP operation latency
- `smtp_sends_successful` - Counter for successful SMTP sends
- `smtp_sends_failed` - Counter for failed SMTP sends

---

### 3. EmailQueueManager (database/queue.py)

**Add to imports:**
```python
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger
```

**In `__init__`:**
```python
def __init__(self, config: EmailConfig):
    self.logger = get_structured_logger(__name__)
    self.metrics = get_metrics_collector()
    # ... existing code ...
```

**In `get_pending_emails()` method:**
```python
def get_pending_emails(self, limit: int = 10):
    try:
        with self.metrics.record_latency("queue_query", tags={"operation": "fetch_pending"}):
            pending = self._db_query(f"SELECT * FROM email_queue WHERE status='pending' LIMIT {limit}")

        self.metrics.set_gauge("queue_size_pending", len(pending))
        self.logger.debug("Fetched pending emails", count=len(pending))
        self.metrics.increment_counter("queue_fetches")

        return pending
    except Exception as e:
        self.logger.exception("Error fetching pending emails")
        self.metrics.increment_counter("queue_fetch_errors")
        return []
```

**Key Metrics to Add:**
- `queue_query` - Database query latency
- `queue_size_pending` - Gauge for pending emails
- `queue_fetches` - Counter for queue queries
- `queue_updates` - Counter for status updates

---

### 4. TemplateRenderer (templates/renderer.py)

**Add to imports:**
```python
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger
```

**In `__init__`:**
```python
def __init__(self):
    self.logger = get_structured_logger(__name__)
    self.metrics = get_metrics_collector()
    # ... existing code ...
```

**In `render_html()` method:**
```python
def render_html(self, email_type: EmailType, context: dict):
    try:
        with self.metrics.record_latency("template_render", tags={"type": email_type.value, "format": "html"}):
            template = self.env.get_template(f"{email_type.value}.html")
            html = template.render(**context)

        self.logger.debug(
            "Template rendered",
            email_type=email_type.value,
            format="html",
            size_bytes=len(html)
        )
        self.metrics.increment_counter("templates_rendered_html")

        return html
    except Exception as e:
        self.logger.exception("Template rendering failed", email_type=email_type.value)
        self.metrics.increment_counter("template_render_errors")
        raise
```

**Key Metrics to Add:**
- `template_render` - Template rendering latency
- `templates_rendered_html` - Counter for HTML templates
- `templates_rendered_text` - Counter for text templates
- `template_render_errors` - Counter for rendering errors

---

## 📊 Expected Metrics Summary

### Latency Metrics
- `batch_processing` - Email batch processing
- `email_send` - Individual email send
- `smtp_send` - SMTP operation
- `queue_query` - Database operations
- `template_render` - Template rendering

### Event Counters
- `emails_sent` - Total emails sent
- `emails_failed` - Total failures
- `emails_retried` - Total retries
- `smtp_sends_successful` - SMTP successes
- `smtp_sends_failed` - SMTP failures
- `queue_fetches` - Queue queries
- `queue_updates` - Status updates
- `templates_rendered_html` - HTML templates
- `templates_rendered_text` - Text templates
- `template_render_errors` - Rendering errors
- `worker_cycles_failed` - Failed cycles

### Gauge Metrics
- `worker_cycles` - Total cycles run
- `queue_size_pending` - Pending emails
- `queue_size_processing` - Processing emails

---

## 🧪 Integration Tests

Create `email_service/tests/test_observability_integration.py`:

```python
@pytest.mark.asyncio
async def test_email_observability_integration():
    """Test end-to-end email processing with observability."""
    reset_metrics_collector()

    worker = EmailWorker()
    metrics = get_metrics_collector()

    # Simulate email sending
    # ... test code ...

    # Verify metrics
    summary = metrics.get_summary()
    assert summary["counters"]["emails_sent"] > 0
    assert summary["latency"]["count"] > 0
    assert "email_send" in str(summary)

@pytest.mark.asyncio
async def test_correlation_id_propagation():
    """Test correlation ID flows through email processing."""
    correlation_id = CorrelationID.get_or_generate()

    # Process email
    ctx = create_request_context(
        email_id=123,
        recipient="test@example.com"
    )

    # Verify context
    assert get_request_context() == ctx
    assert CorrelationID.get() == correlation_id
```

---

## ✨ Next Steps

1. ✅ **Framework Created** - 5 observability modules
2. ⏳ **Integrate in Components** - EmailWorker, SMTPClient, QueueManager, TemplateRenderer
3. ⏳ **Create Integration Tests** - 15-20 tests
4. ⏳ **Create Documentation** - Usage guide
5. ⏳ **Commit Changes** - Full OPCIÓN 6

---

## 📋 Implementation Checklist

- [ ] EmailWorker observability integration
- [ ] SMTPClient observability integration
- [ ] EmailQueueManager observability integration
- [ ] TemplateRenderer observability integration
- [ ] Integration tests (15-20)
- [ ] Documentation
- [ ] Commit to git
- [ ] Move to OPCIÓN 7 (Agent Service)

---

**Status:** Framework Complete - Ready for Integration
**Estimated Time:** 2-3 hours for full OPCIÓN 6 completion
**Owner:** Lab01-MCP Team
**Date:** 2025-11-03
