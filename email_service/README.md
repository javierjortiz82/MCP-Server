# 📧 Email Service - Queue-Based Email Notification System

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-14+-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Robust, production-ready email notification system for booking management with PostgreSQL queue, automatic retries, and beautiful HTML templates.**

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Email Templates](#-email-templates)
- [Database Schema](#-database-schema)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Monitoring](#-monitoring)
- [Troubleshooting](#-troubleshooting)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

The **Email Service** is an asynchronous email notification system designed for the Lab01-MCP booking platform. It provides reliable email delivery with automatic retry logic, status tracking, and professional HTML templates.

### Use Cases

- 📩 **Booking Confirmations** - Instant confirmation emails when appointments are created
- 🚫 **Cancellation Notices** - Automated notifications for cancelled bookings
- 🔄 **Reschedule Alerts** - Updates when appointments are rescheduled
- ⏰ **Smart Reminders** - Automatic reminders 24h and 1h before appointments
- 📊 **Delivery Tracking** - Complete audit trail of all email communications

---

## ✨ Features

### Core Features

- ✅ **Queue-Based Architecture** - PostgreSQL-backed queue with FIFO + priority support
- ✅ **Automatic Retry Logic** - Exponential backoff (5min → 10min → 20min)
- ✅ **Beautiful HTML Templates** - Responsive Jinja2 templates for all email types
- ✅ **SMTP Provider Agnostic** - Works with Gmail, SendGrid, AWS SES, or any SMTP server
- ✅ **Status Tracking** - Complete lifecycle: `pending → processing → sent/failed`
- ✅ **Docker Ready** - Containerized worker service with health checks
- ✅ **Production Hardened** - Connection pooling, graceful shutdown, comprehensive logging

### Advanced Features

- 🔄 **Retry with Exponential Backoff** - Configurable retry strategy
- 📅 **Scheduled Emails** - Send emails at specific times (reminders)
- 🎨 **Template Engine** - Jinja2 with custom filters and fallbacks
- 🔒 **Type Safety** - Pydantic v2 models with validation
- 📊 **Metrics Ready** - Success rate, delivery time, retry statistics
- 🌍 **Multi-language Ready** - Template-based localization support

---

## 🏗️ Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Application Layer"
        A[Booking System] -->|enqueue_email| B[EmailQueueManager]
    end

    subgraph "Database Layer"
        B -->|INSERT| C[(PostgreSQL Queue<br/>test.email_queue)]
        C -->|Poll every 10s| D[Email Worker]
    end

    subgraph "Processing Layer"
        D -->|1. Get pending| C
        D -->|2. Render template| E[TemplateRenderer]
        E -->|Jinja2| F[HTML Templates]
        D -->|3. Send email| G[SMTPClient]
    end

    subgraph "Delivery Layer"
        G -->|SMTP/TLS| H{SMTP Provider}
        H -->|Gmail| I[Gmail SMTP]
        H -->|SendGrid| J[SendGrid API]
        H -->|AWS| K[AWS SES]
    end

    subgraph "Customer"
        I --> L[📧 Customer Email]
        J --> L
        K --> L
    end

    D -->|4. Update status| C
    D -.->|Retry on fail| C

    style A fill:#667eea,stroke:#764ba2,stroke-width:2px,color:#fff
    style C fill:#f093fb,stroke:#f5576c,stroke-width:2px,color:#fff
    style D fill:#4facfe,stroke:#00f2fe,stroke-width:2px,color:#fff
    style G fill:#43e97b,stroke:#38f9d7,stroke-width:2px,color:#fff
    style L fill:#fa709a,stroke:#fee140,stroke-width:2px,color:#fff
```

### Email Lifecycle Flow

```mermaid
stateDiagram-v2
    [*] --> Pending: Booking event occurs
    Pending --> Scheduled: scheduled_for > now
    Pending --> Processing: Worker picks up email
    Scheduled --> Processing: scheduled_for <= now

    Processing --> Sent: SMTP success
    Processing --> Retry1: SMTP failed (attempt 1)

    Retry1 --> Processing: Wait 5 minutes
    Retry1 --> Retry2: SMTP failed (attempt 2)

    Retry2 --> Processing: Wait 10 minutes
    Retry2 --> Retry3: SMTP failed (attempt 3)

    Retry3 --> Processing: Wait 20 minutes
    Retry3 --> Failed: Max retries exceeded

    Sent --> [*]: Email delivered ✅
    Failed --> [*]: Permanent failure ❌

    note right of Processing
        Status updates are atomic
        Uses database locks
    end note

    note right of Retry1
        Exponential backoff:
        backoff * 2^retry_count
    end note
```

### Component Interaction Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant BookingAPI as Booking API
    participant Queue as Queue Manager
    participant DB as PostgreSQL
    participant Worker as Email Worker
    participant Template as Template Renderer
    participant SMTP as SMTP Client
    participant Provider as SMTP Provider

    Customer->>BookingAPI: Create booking
    BookingAPI->>Queue: enqueue_email(type, context)
    Queue->>DB: INSERT INTO email_queue
    DB-->>Queue: email_id
    Queue-->>BookingAPI: email_id
    BookingAPI-->>Customer: Booking confirmed

    Note over Worker: Polls every 10 seconds

    Worker->>DB: SELECT pending emails
    DB-->>Worker: batch of 50 emails

    loop For each email
        Worker->>DB: UPDATE status='processing'
        Worker->>Template: render_html(type, context)
        Template-->>Worker: HTML content
        Worker->>SMTP: send_email(recipient, html)
        SMTP->>Provider: SMTP: MAIL FROM, RCPT TO, DATA

        alt Success
            Provider-->>SMTP: 250 OK
            SMTP-->>Worker: Success
            Worker->>DB: UPDATE status='sent'
        else Failure
            Provider-->>SMTP: 5xx Error
            SMTP-->>Worker: Error
            Worker->>DB: retry_email(error, backoff)
        end
    end

    Note over Provider,Customer: Email delivered
    Provider->>Customer: 📧 Email received
```

### Database Entity Relationship

```mermaid
erDiagram
    EMAIL_QUEUE ||--o{ APPOINTMENTS : references

    EMAIL_QUEUE {
        int id PK
        varchar type
        varchar recipient_email
        varchar recipient_name
        varchar subject
        text body_html
        text body_text
        varchar status
        int retry_count
        int max_retries
        text last_error
        timestamp next_retry_at
        timestamp scheduled_for
        timestamp sent_at
        int priority
        int booking_id FK
        jsonb template_context
        timestamp created_at
        timestamp updated_at
    }

    APPOINTMENTS {
        int id PK
        varchar customer_name
        varchar customer_email
        varchar customer_phone
        varchar service_type
        date booking_date
        time booking_time
        int duration_minutes
        varchar status
        timestamp created_at
    }
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (optional, recommended)
- SMTP credentials (Gmail, SendGrid, or AWS SES)

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/lab01-mcp.git
cd lab01-mcp/email_service

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp ../.env.example ../.env
# Edit .env with your SMTP credentials

# 4. Initialize database
python3 ../SQL/src/init_email_queue.py

# 5. Start email worker
python -m email_service.worker
```

### Docker Deployment (Recommended)

```bash
# Start all services (PostgreSQL + Email Worker)
cd ../DockerConfig
docker-compose up -d email-worker

# View logs
docker logs -f mcp-email-worker
```

---

## 📦 Installation

### Method 1: pip install (Standalone)

```bash
cd email_service
pip install -r requirements.txt
```

**Dependencies:**
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Settings management
- `Jinja2>=3.1.2` - Template engine
- `python-dotenv>=1.0.0` - Environment variables
- `email-validator>=2.1.0` - Email validation

### Method 2: Docker (Production)

```bash
cd email_service
docker build -t lab01-email-service:latest .
docker run --env-file ../.env lab01-email-service:latest
```

### Method 3: Docker Compose (Full Stack)

```bash
cd ../DockerConfig
docker-compose up -d email-worker
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# ============================================================================
# SMTP SERVER CONFIGURATION
# ============================================================================
SMTP_HOST=smtp.gmail.com              # Gmail, SendGrid, AWS SES
SMTP_PORT=587                         # 587 for TLS, 465 for SSL
SMTP_USER=your.email@gmail.com        # SMTP username
SMTP_PASSWORD=your-app-password       # SMTP password (NOT Gmail password!)
SMTP_FROM_EMAIL=noreply@lab01.com     # "From" email address
SMTP_FROM_NAME=Lab01 Bookings         # "From" display name
SMTP_USE_TLS=true                     # Use TLS encryption
SMTP_TIMEOUT=30                       # Connection timeout (seconds)

# ============================================================================
# EMAIL WORKER CONFIGURATION
# ============================================================================
EMAIL_WORKER_POLL_INTERVAL=10         # Seconds between queue polls
EMAIL_WORKER_BATCH_SIZE=50            # Max emails per batch
EMAIL_RETRY_MAX_ATTEMPTS=3            # Max retry attempts
EMAIL_RETRY_BACKOFF_SECONDS=300       # Initial backoff (5 minutes)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL=postgresql://mcp_user:password@localhost:5434/mcp_db
SCHEMA_NAME=test                      # PostgreSQL schema

# ============================================================================
# REMINDERS CONFIGURATION
# ============================================================================
REMINDER_24H_ENABLED=true             # Send 24-hour reminders
REMINDER_1H_ENABLED=true              # Send 1-hour reminders

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE=true                      # Write logs to file
LOG_DIR=./logs                        # Log directory path
```

### Gmail SMTP Setup (Recommended for Development)

1. **Enable 2-Step Verification** in your Google Account
2. **Generate App Password:**
   - Visit: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Copy the 16-character password
3. **Configure `.env`:**
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.email@gmail.com
   SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # 16-char app password
   ```

**Gmail Limits:**
- Free: 500 emails/day
- Google Workspace: 2,000 emails/day

### Alternative SMTP Providers

#### SendGrid (100 emails/day free)
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### AWS SES ($0.10 per 1,000 emails)
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-aws-access-key-id
SMTP_PASSWORD=your-aws-secret-access-key
```

---

## 💻 Usage

### Enqueue Email (Python API)

```python
from email_service.queue_manager import EmailQueueManager
from email_service.models import EmailType

# Initialize queue manager
queue = EmailQueueManager()

# Enqueue booking confirmation email
email_id = queue.enqueue_email(
    email_type=EmailType.BOOKING_CREATED,
    recipient_email="customer@example.com",
    recipient_name="Juan Pérez",
    subject="Confirmación de Cita - Consulta General",
    body_html="<h1>Cita confirmada</h1>",  # Or leave empty for template rendering
    template_context={
        "customer_name": "Juan Pérez",
        "service_type": "Consulta General",
        "booking_date": "2025-10-15",
        "booking_time": "14:00",
        "duration_minutes": 60,
        "booking_id": 1234,
        "google_calendar_link": "https://calendar.google.com/...",
    },
    booking_id=1234,
    priority=5  # 1=highest, 10=lowest
)

print(f"✅ Email queued: {email_id}")
```

### Email Types

```python
from email_service.models import EmailType

# Available email types
EmailType.BOOKING_CREATED       # Booking confirmation
EmailType.BOOKING_CANCELLED     # Cancellation notice
EmailType.BOOKING_RESCHEDULED   # Rescheduled notification
EmailType.REMINDER_24H          # 24-hour reminder
EmailType.REMINDER_1H           # 1-hour reminder
EmailType.REMINDER_CUSTOM       # Custom reminders
```

### Run Email Worker

```bash
# Method 1: Direct Python execution
python -m email_service.worker

# Method 2: Docker container
docker-compose up email-worker

# Method 3: Background daemon
nohup python -m email_service.worker > worker.log 2>&1 &
```

### Test Email Delivery

```python
from email_service.smtp_client import SMTPClient

# Test SMTP connection
client = SMTPClient()
success = client.send_test_email("test@example.com")

if success:
    print("✅ Test email sent successfully!")
else:
    print("❌ Email sending failed - check SMTP configuration")
```

### Query Email Status

```sql
-- View recent emails
SELECT
    id,
    type,
    recipient_email,
    status,
    retry_count,
    created_at,
    sent_at
FROM test.email_queue
ORDER BY created_at DESC
LIMIT 10;

-- Get email statistics
SELECT
    status,
    COUNT(*) as count,
    ROUND(AVG(retry_count), 2) as avg_retries
FROM test.email_queue
GROUP BY status;

-- Find failed emails
SELECT
    id,
    recipient_email,
    last_error,
    retry_count
FROM test.email_queue
WHERE status = 'failed'
ORDER BY created_at DESC;
```

---

## 🎨 Email Templates

### Template Structure

All email templates are located in `email_service/templates/` and use Jinja2 syntax.

**Available Templates:**
- `booking_created.html` - Booking confirmation
- `booking_cancelled.html` - Cancellation notice
- `booking_rescheduled.html` - Rescheduled notification
- `reminder_24h.html` - 24-hour reminder
- `reminder_1h.html` - 1-hour reminder

### Template Context Variables

Each template receives a context dictionary with the following variables:

```python
{
    # Common fields (all templates)
    "customer_name": str,
    "booking_id": int,
    "service_type": str,
    "booking_date": str,  # YYYY-MM-DD
    "booking_time": str,  # HH:MM
    "duration_minutes": int,
    "google_calendar_link": str | None,

    # booking_cancelled specific
    "cancellation_reason": str | None,

    # booking_rescheduled specific
    "old_date": str,
    "old_time": str,
    "new_date": str,
    "new_time": str,

    # reminders specific
    "hours_until": int,  # 24 or 1
}
```

### Template Design Features

- ✅ **Responsive Design** - Works on mobile, tablet, and desktop
- ✅ **Inline CSS** - Maximum email client compatibility
- ✅ **Professional Gradients** - Modern, attractive design
- ✅ **CTA Buttons** - Google Calendar integration
- ✅ **Cross-Client Compatible** - Gmail, Outlook, Apple Mail, etc.
- ✅ **Accessibility** - Semantic HTML, alt text, proper headings

### Custom Template Example

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ subject }}</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ subject }}</h1>
        </div>
        <p>Hola {{ customer_name }},</p>
        <p>Tu cita para <strong>{{ service_type }}</strong> está confirmada.</p>
        <p><strong>Fecha:</strong> {{ booking_date }}</p>
        <p><strong>Hora:</strong> {{ booking_time }}</p>
    </div>
</body>
</html>
```

---

## 🗄️ Database Schema

### Table: `test.email_queue`

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `type` | VARCHAR(50) | Email type (enum) |
| `recipient_email` | VARCHAR(255) | Customer email |
| `recipient_name` | VARCHAR(255) | Customer name |
| `subject` | VARCHAR(500) | Email subject |
| `body_html` | TEXT | HTML email body |
| `body_text` | TEXT | Plain text fallback |
| `status` | VARCHAR(20) | Email status |
| `retry_count` | INTEGER | Retry attempts |
| `max_retries` | INTEGER | Max retries (default: 3) |
| `last_error` | TEXT | Last error message |
| `next_retry_at` | TIMESTAMP | Next retry time |
| `scheduled_for` | TIMESTAMP | Scheduled send time |
| `sent_at` | TIMESTAMP | Delivery timestamp |
| `priority` | INTEGER | Priority (1-10) |
| `booking_id` | INTEGER | FK to appointments |
| `template_context` | JSONB | Template variables |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update |

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Waiting to be processed |
| `scheduled` | Waiting for `scheduled_for` time |
| `processing` | Currently being sent |
| `sent` | Successfully delivered |
| `failed` | Max retries exceeded |

### Indexes

```sql
-- Worker poll query (most important)
CREATE INDEX idx_email_queue_worker_poll
    ON test.email_queue(status, scheduled_for, priority)
    WHERE status IN ('pending', 'scheduled');

-- Retry query
CREATE INDEX idx_email_queue_retry
    ON test.email_queue(status, next_retry_at)
    WHERE status = 'processing' AND next_retry_at IS NOT NULL;

-- Recipient lookup
CREATE INDEX idx_email_queue_recipient
    ON test.email_queue(recipient_email, created_at DESC);

-- Booking lookup
CREATE INDEX idx_email_queue_booking
    ON test.email_queue(booking_id)
    WHERE booking_id IS NOT NULL;

-- Analytics
CREATE INDEX idx_email_queue_type_status
    ON test.email_queue(type, status);

-- Sent emails reporting
CREATE INDEX idx_email_queue_sent
    ON test.email_queue(sent_at DESC)
    WHERE status = 'sent';
```

### SQL Functions

#### 1. `enqueue_email()`
```sql
SELECT test.enqueue_email(
    'booking_created',              -- type
    'customer@example.com',         -- recipient_email
    'Juan Pérez',                   -- recipient_name
    'Confirmación de Cita',         -- subject
    '<h1>Confirmado</h1>',          -- body_html
    NULL,                           -- body_text
    1234,                           -- booking_id
    '{"customer_name": "Juan"}'::jsonb,  -- template_context
    CURRENT_TIMESTAMP,              -- scheduled_for
    5                               -- priority
);
```

#### 2. `get_pending_emails()`
```sql
-- Get next 50 pending emails (with row-level locking)
SELECT * FROM test.get_pending_emails(50);
```

#### 3. `update_email_status()`
```sql
-- Mark email as sent
SELECT test.update_email_status(
    1234,                -- email_id
    'sent',              -- status
    NULL,                -- error
    CURRENT_TIMESTAMP    -- sent_at
);
```

#### 4. `retry_email()`
```sql
-- Schedule retry with exponential backoff
SELECT test.retry_email(
    1234,                              -- email_id
    'SMTP connection timeout',         -- error
    300                                -- backoff_seconds (5 min)
);
```

#### 5. `cleanup_old_emails()`
```sql
-- Delete emails older than 90 days
SELECT test.cleanup_old_emails(90);
```

---

## 🐳 Deployment

### Docker Deployment

#### Option 1: Docker Compose (Recommended)

```yaml
# docker-compose.yml
services:
  email-worker:
    build:
      context: ../email_service
      dockerfile: Dockerfile
    container_name: mcp-email-worker
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://mcp_user:password@postgres:5432/mcp_db
      SCHEMA_NAME: test
      SMTP_HOST: ${SMTP_HOST}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
    volumes:
      - ../email_service:/app
      - email_logs:/app/logs
    depends_on:
      - postgres
```

```bash
docker-compose up -d email-worker
```

#### Option 2: Standalone Docker

```bash
# Build image
docker build -t lab01-email-service:latest .

# Run container
docker run -d \
  --name email-worker \
  --env-file .env \
  --restart unless-stopped \
  lab01-email-service:latest
```

### Production Deployment Checklist

- [ ] **SMTP Configuration**
  - [ ] Valid SMTP credentials configured
  - [ ] Test email sent successfully
  - [ ] Daily sending limits verified

- [ ] **Database Setup**
  - [ ] `email_queue` table created
  - [ ] All indexes created
  - [ ] SQL functions deployed
  - [ ] Permissions granted to `mcp_user`

- [ ] **Worker Configuration**
  - [ ] Poll interval optimized (default: 10s)
  - [ ] Batch size tuned (default: 50)
  - [ ] Retry limits configured (default: 3)
  - [ ] Logging enabled

- [ ] **Monitoring**
  - [ ] Log aggregation configured
  - [ ] Email delivery metrics tracked
  - [ ] Alerts for failed emails
  - [ ] Health check endpoint enabled

- [ ] **Security**
  - [ ] SMTP credentials encrypted
  - [ ] TLS encryption enabled
  - [ ] Non-root Docker user
  - [ ] Network isolation configured

---

## 📚 API Reference

### EmailQueueManager

```python
class EmailQueueManager:
    """Manages email queue operations with PostgreSQL."""

    def enqueue_email(
        self,
        email_type: EmailType,
        recipient_email: str,
        recipient_name: str | None,
        subject: str,
        body_html: str,
        body_text: str | None = None,
        booking_id: int | None = None,
        template_context: dict[str, Any] | None = None,
        scheduled_for: datetime | None = None,
        priority: int = 5,
    ) -> int:
        """Enqueue a new email for delivery.

        Returns:
            email_id: ID of created email record
        """

    def get_pending_emails(self, limit: int = 50) -> list[EmailRecord]:
        """Get pending emails ready for delivery."""

    def update_email_status(
        self,
        email_id: int,
        status: EmailStatus,
        error: str | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        """Update email delivery status."""

    def retry_email(
        self,
        email_id: int,
        error: str,
        backoff_seconds: int = 300
    ) -> None:
        """Retry failed email with exponential backoff."""
```

### SMTPClient

```python
class SMTPClient:
    """SMTP email delivery client."""

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> None:
        """Send an email via SMTP."""

    def validate_connection(self) -> bool:
        """Test SMTP connection and authentication."""

    def send_test_email(self, test_recipient: str) -> bool:
        """Send a test email to verify configuration."""
```

### TemplateRenderer

```python
class TemplateRenderer:
    """Jinja2 template renderer for emails."""

    def render_html(
        self,
        email_type: EmailType,
        context: dict[str, Any]
    ) -> str:
        """Render HTML email template."""

    def render_text(
        self,
        email_type: EmailType,
        context: dict[str, Any]
    ) -> str:
        """Render plain text email template."""

    def template_exists(
        self,
        email_type: EmailType,
        format_type: str = "html"
    ) -> bool:
        """Check if template file exists."""
```

---

## 📊 Monitoring

### Log Files

```bash
# View worker logs
tail -f email_service/logs/email_worker.log

# Docker logs
docker logs -f mcp-email-worker

# Follow logs with grep
docker logs -f mcp-email-worker | grep "ERROR"
```

### Email Queue Metrics

```sql
-- Success rate by email type
SELECT
    type,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as success_rate
FROM test.email_queue
GROUP BY type;

-- Average delivery time
SELECT
    AVG(EXTRACT(EPOCH FROM (sent_at - created_at))) / 60 as avg_minutes
FROM test.email_queue
WHERE status = 'sent';

-- Emails pending for too long (> 1 hour)
SELECT
    id,
    recipient_email,
    status,
    retry_count,
    created_at
FROM test.email_queue
WHERE status IN ('pending', 'processing')
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '1 hour';
```

### Worker Health Check

```bash
# Check if worker is running
docker ps | grep email-worker

# Check worker process
ps aux | grep "email_service.worker"

# Check last processed email
docker exec mcp-postgres psql -U mcp_user -d mcp_db \
  -c "SELECT MAX(sent_at) FROM test.email_queue WHERE status = 'sent';"
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Emails Not Being Sent

**Symptoms:**
- Emails stuck in `pending` status
- Worker logs show no activity

**Solutions:**
```bash
# Check worker is running
docker ps | grep email-worker

# Restart worker
docker-compose restart email-worker

# Check database connection
docker exec mcp-postgres psql -U mcp_user -d mcp_db \
  -c "SELECT COUNT(*) FROM test.email_queue WHERE status = 'pending';"
```

#### 2. SMTP Authentication Failed

**Symptoms:**
- Error: "535-5.7.8 Username and Password not accepted"
- Emails marked as `failed`

**Solutions:**
```bash
# Verify SMTP credentials
echo $SMTP_USER
echo $SMTP_PASSWORD

# For Gmail: ensure App Password (not account password)
# Visit: https://myaccount.google.com/apppasswords

# Test SMTP connection
python -c "
from email_service.smtp_client import SMTPClient
client = SMTPClient()
print(client.validate_connection())
"
```

#### 3. Template Rendering Errors

**Symptoms:**
- Error: "TemplateNotFound"
- Empty email body

**Solutions:**
```bash
# Check template directory exists
ls -la email_service/templates/

# Verify template files
ls email_service/templates/*.html

# Test template rendering
python -c "
from email_service.template_renderer import TemplateRenderer
from email_service.models import EmailType
renderer = TemplateRenderer()
print(renderer.template_exists(EmailType.BOOKING_CREATED, 'html'))
"
```

#### 4. High Retry Rate

**Symptoms:**
- Many emails in `processing` status
- High `retry_count` values

**Solutions:**
```sql
-- Identify problematic emails
SELECT
    id,
    recipient_email,
    retry_count,
    last_error
FROM test.email_queue
WHERE retry_count > 1
ORDER BY retry_count DESC;

-- Check for common errors
SELECT
    last_error,
    COUNT(*) as count
FROM test.email_queue
WHERE status = 'failed'
GROUP BY last_error
ORDER BY count DESC;
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# Set in .env
LOG_LEVEL=DEBUG

# Restart worker
docker-compose restart email-worker

# Watch debug logs
docker logs -f mcp-email-worker
```

---

## 🛠️ Development

### Local Development Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install dev dependencies
pip install pytest pytest-asyncio pytest-cov black ruff mypy

# 4. Run tests
pytest tests/ -v --cov=email_service

# 5. Format code
black .
ruff check . --fix

# 6. Type checking
mypy email_service/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=email_service --cov-report=html

# Run specific test file
pytest tests/test_queue_manager.py -v

# Run with debug output
pytest -v -s
```

### Code Quality Checks

```bash
# Format code with Black
black email_service/

# Lint with Ruff
ruff check email_service/

# Type check with mypy
mypy email_service/ --strict

# All quality checks
black . && ruff check . --fix && mypy email_service/
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Contribution Workflow

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Run tests:** `pytest`
5. **Format code:** `black . && ruff check . --fix`
6. **Commit changes:** `git commit -m "feat: add your feature"`
7. **Push to branch:** `git push origin feature/your-feature-name`
8. **Open a Pull Request**

### Code Style

- Follow **PEP 8** guidelines
- Use **type hints** for all functions
- Write **docstrings** for all public methods (Google style)
- Maximum line length: **100 characters**
- Use **Pydantic v2** for data validation
- Keep functions **small and focused** (max 50 lines)

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for attachment files
fix: resolve SMTP timeout on large emails
docs: update API reference for EmailQueueManager
refactor: simplify retry logic in worker
test: add integration tests for SMTP client
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](../LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Lab01-MCP Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 👥 Authors & Acknowledgments

### Development Team

- **Lab01-MCP Team** - *Initial work* - [GitHub](https://github.com/your-org/lab01-mcp)

### Built With

- [Python 3.11+](https://www.python.org/) - Programming language
- [PostgreSQL 14+](https://www.postgresql.org/) - Database
- [Pydantic v2](https://docs.pydantic.dev/) - Data validation
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [psycopg2](https://www.psycopg.org/) - PostgreSQL adapter
- [Docker](https://www.docker.com/) - Containerization

### Special Thanks

- Anthropic Claude for AI assistance
- PostgreSQL community for excellent database
- Python community for amazing libraries

---

## 📞 Support

### Getting Help

- 📖 **Documentation:** [Lab01-MCP Docs](https://github.com/your-org/lab01-mcp/docs)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/your-org/lab01-mcp/discussions)
- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/your-org/lab01-mcp/issues)
- 📧 **Email:** support@lab01.com

### Useful Links

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/templates/)
- [Gmail SMTP Setup Guide](https://support.google.com/mail/answer/7126229)
- [SendGrid API Documentation](https://docs.sendgrid.com/)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ by the Lab01-MCP Team

</div>
