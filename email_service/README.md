# 📧 Email Service

> **Production-ready asynchronous email queue system** for booking confirmations, reminders, and notifications

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-1f6feb?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/latest/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-13+-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Code Quality](https://img.shields.io/badge/mypy-passing-success?style=flat-square)](https://mypy-lang.org/)
[![PEP 8](https://img.shields.io/badge/PEP%208-compliant-success?style=flat-square)](https://www.python.org/dev/peps/pep-0008/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-blue?style=flat-square)](./CHANGELOG.md)

Built with **PostgreSQL**, **Jinja2**, **Pydantic v2**, and **async Python** for maximum reliability and performance.

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [📖 Usage](#-usage)
- [⚙️ Configuration](#️-configuration)
- [📦 Project Structure](#-project-structure)
- [🔧 API Reference](#-api-reference)
- [🧪 Testing](#-testing)
- [🆘 Troubleshooting](#-troubleshooting)
- [📄 License](#-license)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Async Queue Processing** | Polls PostgreSQL queue every 10s (configurable) |
| 🔁 **Auto Retry Logic** | Exponential backoff with configurable max retries |
| 🎨 **Template Rendering** | Jinja2-based HTML & plaintext email templates |
| 📨 **SMTP Compatibility** | Gmail, SendGrid, AWS SES, or any SMTP server |
| ⏰ **Scheduled Emails** | Send emails at specific times (future sends) |
| 📊 **Priority Levels** | Process emails by priority (1=highest, 10=lowest) |
| 📈 **Status Tracking** | Complete lifecycle: pending → processing → sent/failed |
| 🔐 **Connection Pooling** | Thread-safe with psycopg2 connection pool |
| 📝 **Comprehensive Logging** | Structured logging with configurable levels |
| ✅ **Type Safe** | Full Pydantic v2 validation + mypy compliant |
| 🎯 **Production Ready** | Docker-ready, PEP 8 compliant, documented |

---

## 🏗️ Architecture

### System Overview

The Email Service orchestrates a complete email delivery pipeline with queue management, template rendering, and reliable SMTP delivery.

```mermaid
graph TB
    subgraph INPUT["📥 INPUT LAYER"]
        API["🔷 Booking API<br/>Enqueue Emails"]
        CLI["🔶 CLI/Script<br/>Batch Operations"]
    end

    subgraph QUEUE["⏳ QUEUE LAYER"]
        DB["🟠 PostgreSQL<br/>Email Queue<br/>5 Status States"]
    end

    subgraph PROCESSING["⚙️ PROCESSING LAYER"]
        WORKER["🟣 Email Worker<br/>Async Processor<br/>Retry Logic"]
        RENDER["🟡 Jinja2<br/>Template Renderer<br/>HTML/Text"]
    end

    subgraph OUTPUT["📤 OUTPUT LAYER"]
        SMTP["🟢 SMTP Client<br/>Gmail/SendGrid<br/>AWS SES"]
    end

    INPUT --> QUEUE
    QUEUE -->|Poll Every 10s| PROCESSING
    PROCESSING -->|Render Templates| RENDER
    RENDER -->|Send Email| OUTPUT
    OUTPUT -->|Update Status| QUEUE

    style INPUT fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style QUEUE fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style PROCESSING fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style OUTPUT fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style API fill:#bbdefb,color:#0d47a1
    style CLI fill:#ffe0b2,color:#e65100
    style DB fill:#ffe0b2,color:#e65100
    style WORKER fill:#e1bee7,color:#4a148c
    style RENDER fill:#fff59d,color:#f57f17
    style SMTP fill:#c8e6c9,color:#1b5e20
```

### Component Architecture

```mermaid
graph LR
    subgraph CORE["🔧 Core"]
        EXC["Exceptions<br/>5 Types"]
        LOG["Logger<br/>Factory"]
        style EXC fill:#ffcccc,stroke:#c41c3b,stroke-width:2px
        style LOG fill:#ffcccc,stroke:#c41c3b,stroke-width:2px
    end

    subgraph CONFIG["⚙️ Config"]
        SETTINGS["Pydantic v2<br/>Settings"]
        style SETTINGS fill:#cce5ff,stroke:#0056b3,stroke-width:2px
    end

    subgraph MODELS["📊 Models"]
        EMAIL["EmailRecord<br/>Status, Type"]
        REQ["Create<br/>Request"]
        CTX["Template<br/>Context"]
        SMTP["SMTP<br/>Config"]
        STATS["Stats<br/>Analytics"]
        style EMAIL fill:#e1f5ff,stroke:#01579b,stroke-width:2px
        style REQ fill:#e1f5ff,stroke:#01579b,stroke-width:2px
        style CTX fill:#e1f5ff,stroke:#01579b,stroke-width:2px
        style SMTP fill:#e1f5ff,stroke:#01579b,stroke-width:2px
        style STATS fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    end

    subgraph CLIENTS["🌐 Clients"]
        SMTPC["SMTP<br/>Client"]
        style SMTPC fill:#d4edda,stroke:#155724,stroke-width:2px
    end

    subgraph DB["💾 Database"]
        QUEUE["Queue<br/>Manager"]
        style QUEUE fill:#fff3cd,stroke:#856404,stroke-width:2px
    end

    subgraph TMPL["🎨 Templates"]
        RENDERER["Jinja2<br/>Renderer"]
        style RENDERER fill:#f8d7da,stroke:#721c24,stroke-width:2px
    end

    subgraph WORK["🤖 Worker"]
        PROC["Email<br/>Processor"]
        style PROC fill:#e2e3e5,stroke:#383d41,stroke-width:2px
    end

    PROC -->|Uses| SETTINGS
    PROC -->|Uses| QUEUE
    PROC -->|Uses| SMTPC
    PROC -->|Uses| RENDERER
    QUEUE -->|Uses| EMAIL
    RENDERER -->|Uses| CTX
    SMTPC -->|Uses| SMTP
    CORE -.->|Supports| PROC
    MODELS -.->|Validates| PROC
```

### Email Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: Email Enqueued

    PENDING --> SCHEDULED: Scheduled for\nlater time?
    PENDING --> PROCESSING: Worker Picks Up
    SCHEDULED --> PROCESSING: Scheduled Time\nArrived

    PROCESSING --> SENT: ✅ Send Success
    PROCESSING --> RETRY: ❌ Error &\nRetries Left

    RETRY --> PROCESSING: Wait Backoff\nTime
    RETRY --> FAILED: Max Retries\nExceeded

    SENT --> [*]
    FAILED --> [*]

    note right of PENDING
        Max 50 in batch
        Priority ordered
    end note

    note right of SCHEDULED
        Waiting for
        scheduled_for time
    end note

    note right of PROCESSING
        Currently sending
        via SMTP
    end note

    note right of RETRY
        Exponential backoff
        Starting at 300s
    end note
```

### Email Processing Flow

```mermaid
sequenceDiagram
    participant API as 📦 Booking API
    participant DB as 🟠 PostgreSQL
    participant WORKER as 🤖 Worker
    participant RENDER as 🎨 Renderer
    participant SMTP as 📨 SMTP Server

    API->>DB: 1️⃣ Enqueue Email<br/>(status: pending)

    loop Every 10 Seconds
        WORKER->>DB: 2️⃣ Poll Pending<br/>Emails (limit: 50)
        DB-->>WORKER: List of pending emails

        rect rgba(100, 200, 255, 0.3)
            Note over WORKER,RENDER: For Each Email:

            WORKER->>DB: 3️⃣ Mark PROCESSING

            alt Has Template Context
                WORKER->>RENDER: 4️⃣ Render Template
                Note over RENDER: HTML + Plain Text
                RENDER-->>WORKER: Rendered Content
            else Pre-rendered
                Note over WORKER: Use stored body_html
            end

            WORKER->>SMTP: 5️⃣ Send Email

            alt Send Success ✅
                SMTP-->>WORKER: OK (250)
                WORKER->>DB: 6️⃣ Mark SENT<br/>(sent_at=now)
            else Send Failed ❌
                SMTP-->>WORKER: Error

                alt Retries Remaining
                    WORKER->>DB: 7️⃣ Schedule Retry<br/>(next_retry_at)
                else Max Retries
                    WORKER->>DB: 8️⃣ Mark FAILED<br/>(last_error)
                end
            end
        end
    end
```

---

## 🚀 Quick Start

### 📦 Installation

```bash
# Clone or navigate to the project
cd /path/to/email_service

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### ⚙️ Configuration

```bash
# Copy configuration template
cp .env.example .env

# Edit with your credentials
nano .env

# Validate configuration
python scripts/validate_env.py
```

**Required Environment Variables:**
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/db
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 🏃 Run Email Worker

```bash
# Direct Python
python -m email_service.worker.processor

# Docker Compose
docker-compose up email_worker

# Or in your code
from email_service import EmailWorker
import asyncio

worker = EmailWorker()
await worker.run()
```

---

## 📖 Usage

### 📬 Enqueue an Email

```python
from email_service import EmailQueueManager, EmailType

queue = EmailQueueManager()

# With template context (rendered by worker)
email_id = queue.enqueue_email(
    email_type=EmailType.BOOKING_CREATED,
    recipient_email="customer@example.com",
    recipient_name="John Doe",
    subject="Your Booking Confirmation",
    body_html="",  # Will be rendered
    template_context={
        "customer_name": "John Doe",
        "service_type": "Consultation",
        "booking_date": "2025-10-20",
        "booking_time": "14:30",
        "duration_minutes": 60,
        "booking_id": 123,
    },
    priority=5,  # 1=highest, 10=lowest
)

print(f"✅ Email #{email_id} enqueued")
```

### 📧 Send Test Email

```python
from email_service import SMTPClient

client = SMTPClient()

# Validate SMTP configuration
if client.validate_connection():
    print("✅ SMTP connection successful")

# Send test email
if client.send_test_email("admin@example.com"):
    print("✅ Test email sent")
```

### 🎨 Render Templates

```python
from email_service import TemplateRenderer, EmailType

renderer = TemplateRenderer()

# Render HTML template
html = renderer.render_html(
    EmailType.BOOKING_CREATED,
    context={
        "customer_name": "Jane",
        "service_type": "Massage",
        "booking_date": "2025-10-20",
        "booking_time": "15:00",
        "duration_minutes": 60,
    }
)

# Render plain text template
text = renderer.render_text(EmailType.BOOKING_CREATED, context)
```

### 🔍 Check Email Status

```python
from email_service import EmailQueueManager, EmailStatus

queue = EmailQueueManager()

# Get email by ID
email = queue.get_email_by_id(email_id=123)

if email:
    print(f"Status: {email.status}")
    print(f"Retry count: {email.retry_count}")
    if email.status == EmailStatus.FAILED:
        print(f"Error: {email.last_error}")
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `DATABASE_URL` | - | string | PostgreSQL connection URI |
| `SCHEMA_NAME` | test | string | PostgreSQL schema name |
| `SMTP_HOST` | smtp.gmail.com | string | SMTP server hostname |
| `SMTP_PORT` | 587 | int | SMTP port (1-65535) |
| `SMTP_USER` | - | string | SMTP username |
| `SMTP_PASSWORD` | - | string | SMTP password |
| `SMTP_FROM_EMAIL` | noreply@lab01.com | string | Sender email |
| `SMTP_FROM_NAME` | Lab01 Bookings | string | Sender display name |
| `SMTP_USE_TLS` | true | bool | Use TLS encryption |
| `SMTP_TIMEOUT` | 30 | int | Connection timeout (5-300s) |
| `EMAIL_WORKER_POLL_INTERVAL` | 10 | int | Queue poll interval (seconds) |
| `EMAIL_WORKER_BATCH_SIZE` | 50 | int | Emails per batch (1-1000) |
| `EMAIL_RETRY_MAX_ATTEMPTS` | 3 | int | Max retry attempts |
| `EMAIL_RETRY_BACKOFF_SECONDS` | 300 | int | Retry backoff (60-86400s) |
| `LOG_LEVEL` | INFO | string | DEBUG, INFO, WARNING, ERROR |
| `LOG_DIR` | ./logs | string | Log directory |
| `TEMPLATE_DIR` | ./templates | string | Email templates directory |

### Example .env File

```bash
# Database
DATABASE_URL=postgresql://mcp_user:password@localhost:5434/mcp_db
SCHEMA_NAME=public

# SMTP (Gmail example)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Company

# Worker
EMAIL_WORKER_POLL_INTERVAL=10
EMAIL_WORKER_BATCH_SIZE=50
EMAIL_RETRY_MAX_ATTEMPTS=3

# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs
```

---

## 📦 Project Structure

```
email_service/
├── core/                    # Core utilities
│   ├── exceptions.py       # 5 custom exception types
│   ├── logger.py           # Centralized logging factory
│   └── __init__.py
├── config/                  # Configuration management
│   ├── settings.py         # Pydantic v2 EmailConfig
│   └── __init__.py
├── models/                  # Data models
│   ├── email.py            # EmailRecord, EmailStatus, EmailType
│   ├── requests.py         # EmailCreateRequest
│   ├── context.py          # Template contexts (5 types)
│   ├── smtp_config.py      # SMTP configuration
│   ├── stats.py            # EmailStats analytics
│   └── __init__.py
├── clients/                 # External clients
│   ├── smtp.py             # SMTPClient wrapper
│   └── __init__.py
├── database/                # Database operations
│   ├── queue.py            # EmailQueueManager
│   └── __init__.py
├── templates/               # Email templates
│   ├── renderer.py         # Jinja2 TemplateRenderer
│   ├── *.html              # Email templates
│   ├── *.txt               # Plain text variants
│   └── __init__.py
├── worker/                  # Email processing daemon
│   ├── processor.py        # EmailWorker async processor
│   └── __init__.py
├── scripts/                 # Utility scripts
│   ├── validate_env.py     # Configuration validator
│   └── __init__.py
├── .env.example            # Configuration template
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development tools
├── pyproject.toml          # Package metadata (PEP 518)
├── MANIFEST.in             # Distribution manifest
├── LICENSE                 # MIT License
├── README.md              # This file
└── CHANGELOG.md           # Version history
```

---

## 🔧 API Reference

### EmailQueueManager

```python
from email_service import EmailQueueManager, EmailStatus

queue = EmailQueueManager()

# Enqueue email
email_id = queue.enqueue_email(
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
) -> int

# Get pending emails
emails = queue.get_pending_emails(limit: int = 50) -> list[EmailRecord]

# Update status
queue.update_email_status(
    email_id: int,
    status: EmailStatus,
    error: str | None = None,
    sent_at: datetime | None = None,
) -> None

# Retry failed email
queue.retry_email(
    email_id: int,
    error: str,
    backoff_seconds: int = 300,
) -> None

# Get email by ID
email = queue.get_email_by_id(email_id: int) -> EmailRecord | None

# Cleanup old emails
deleted = queue.cleanup_old_emails(days_to_keep: int = 90) -> int
```

### SMTPClient

```python
from email_service import SMTPClient

client = SMTPClient()

# Send email
client.send_email(
    recipient_email: str,
    recipient_name: str | None,
    subject: str,
    body_html: str,
    body_text: str | None = None,
) -> None

# Test connection
is_valid = client.validate_connection() -> bool

# Send test email
success = client.send_test_email(test_recipient: str) -> bool
```

### TemplateRenderer

```python
from email_service import TemplateRenderer, EmailType

renderer = TemplateRenderer()

# Render HTML
html = renderer.render_html(
    email_type: EmailType,
    context: dict[str, Any],
) -> str

# Render plain text
text = renderer.render_text(
    email_type: EmailType,
    context: dict[str, Any],
) -> str

# Check template exists
exists = renderer.template_exists(
    email_type: EmailType,
    format_type: str = "html",
) -> bool
```

---

## 🧪 Testing

### Type Checking

```bash
# Check all type hints (mypy)
mypy email_service/ --ignore-missing-imports

# Expected: "Success: no issues found"
```

### Code Quality

```bash
# Linting (ruff)
ruff check email_service/ --select=E,W,F

# Code formatting (black)
black email_service/ --check

# Import organization (isort)
isort email_service/ --check-only

# Run all tests
pytest email_service/tests/ --cov
```

### Quick Verification

```bash
# Test imports
python -c "from email_service import EmailWorker; print('✅ OK')"

# Validate config
python email_service/scripts/validate_env.py

# Send test email
python -c "
from email_service import SMTPClient
client = SMTPClient()
if client.validate_connection():
    print('✅ SMTP OK')
"
```

---

## 🆘 Troubleshooting

### Issue: "SMTP authentication failed"

**Solution:**
```bash
# 1. Check credentials in .env
nano .env

# 2. For Gmail: Use App Passwords, not your Gmail password
# https://support.google.com/accounts/answer/185833

# 3. Test connection
python -c "
from email_service import SMTPClient
client = SMTPClient()
print(client.validate_connection())
"
```

### Issue: "Connection pool exhausted"

**Solution:**
```bash
# Reduce batch size or increase poll interval in .env
EMAIL_WORKER_BATCH_SIZE=25
EMAIL_WORKER_POLL_INTERVAL=15

# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'mcp_db';"
```

### Issue: "Templates not found"

**Solution:**
```bash
# Check TEMPLATE_DIR in .env
TEMPLATE_DIR=/absolute/path/to/templates

# Verify templates exist
ls email_service/templates/

# Create template if missing
touch email_service/templates/booking_created.html
```

### Issue: "Worker not processing emails"

**Debugging steps:**
```bash
# 1. Check logs
tail -f ./logs/email_service.log

# 2. Verify config is valid
python email_service/scripts/validate_env.py

# 3. Check database connection
psql -c "SELECT count(*) FROM public.email_queue;"

# 4. Check pending emails
psql -c "SELECT id, status FROM public.email_queue LIMIT 5;"
```

---

## 📊 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Throughput** | 50-100 emails/sec | Depends on SMTP provider |
| **Latency** | <100ms queue op | <1s SMTP send |
| **Memory** | ~50MB base | +1MB per 1000 queued |
| **DB Connections** | 10 pool | Configurable |
| **Retry Backoff** | 300s initial | Exponential scaling |

---

## 🤝 Contributing

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Install dev dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install
```

### Code Standards

- **PEP 8**: Enforced with black (88 chars)
- **Type Hints**: Required (mypy compliant)
- **Docstrings**: Google style
- **Imports**: Organized with isort

### Running Tests

```bash
# Unit tests
pytest email_service/tests/

# With coverage
pytest --cov=email_service email_service/tests/

# Type checking
mypy email_service/

# All checks
make test  # or run manually above
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](./LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Lab01-MCP Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 📞 Support

- 📧 **Email**: support@lab01.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/Lab01-MCP/email-service/issues)
- 📚 **Documentation**: Full Google-style docstrings in code
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Lab01-MCP/email-service/discussions)

---

<div align="center">

### Built with ❤️ for Lab01 - AI Sales Platform

**[⬆ Back to Top](#-email-service)**

**Version 2.0.0** • **Updated October 18, 2025**

</div>
