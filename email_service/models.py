"""Pydantic models for email service.

Defines data structures for email queue records, SMTP configuration,
and email content validation.

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailStatus(str, Enum):
    """Email delivery status."""

    PENDING = "pending"  # Waiting to be processed
    SCHEDULED = "scheduled"  # Waiting for scheduled_for time
    PROCESSING = "processing"  # Currently being sent
    SENT = "sent"  # Successfully delivered
    FAILED = "failed"  # Max retries exceeded


class EmailType(str, Enum):
    """Email notification types."""

    BOOKING_CREATED = "booking_created"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_RESCHEDULED = "booking_rescheduled"
    REMINDER_24H = "reminder_24h"
    REMINDER_1H = "reminder_1h"
    REMINDER_CUSTOM = "reminder_custom"


class EmailRecord(BaseModel):
    """Email queue record model.

    Represents a single email in the queue system.
    """

    id: int
    type: EmailType
    recipient_email: EmailStr
    recipient_name: str | None = None
    subject: str = Field(..., max_length=500)
    body_html: str
    body_text: str | None = None
    status: EmailStatus = EmailStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    last_error: str | None = None
    next_retry_at: datetime | None = None
    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    priority: int = Field(default=5, ge=1, le=10)
    booking_id: int | None = None
    template_context: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
        use_enum_values = True


class EmailCreateRequest(BaseModel):
    """Request model for creating a new email in queue."""

    type: EmailType
    recipient_email: EmailStr
    recipient_name: str | None = None
    subject: str = Field(..., max_length=500, min_length=1)
    body_html: str = Field(..., min_length=10)
    body_text: str | None = None
    booking_id: int | None = None
    template_context: dict[str, Any] | None = None
    scheduled_for: datetime | None = None
    priority: int = Field(default=5, ge=1, le=10)

    @field_validator("subject")
    @classmethod
    def subject_not_empty(cls, v: str) -> str:
        """Validate subject is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()


class EmailTemplateContext(BaseModel):
    """Base context for email templates.

    Each email type should extend this with specific fields.
    """

    customer_name: str
    booking_id: int | None = None


class BookingCreatedContext(EmailTemplateContext):
    """Context for booking_created email template."""

    service_type: str
    booking_date: str
    booking_time: str
    duration_minutes: int
    google_calendar_link: str | None = None


class BookingCancelledContext(EmailTemplateContext):
    """Context for booking_cancelled email template."""

    service_type: str
    booking_date: str
    booking_time: str
    cancellation_reason: str | None = None


class BookingRescheduledContext(EmailTemplateContext):
    """Context for booking_rescheduled email template."""

    service_type: str
    old_date: str
    old_time: str
    new_date: str
    new_time: str
    google_calendar_link: str | None = None


class ReminderContext(EmailTemplateContext):
    """Context for reminder email templates."""

    service_type: str
    booking_date: str
    booking_time: str
    duration_minutes: int
    hours_until: int | None = None  # Hours until appointment
    google_calendar_link: str | None = None


class SMTPConfig(BaseModel):
    """SMTP server configuration."""

    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    username: str
    password: str
    from_email: EmailStr
    from_name: str = "Lab01 Bookings"
    use_tls: bool = True
    timeout: int = Field(default=30, ge=5, le=120)

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        """Validate password is not empty."""
        if not v or not v.strip():
            raise ValueError("SMTP password cannot be empty")
        return v


class EmailStats(BaseModel):
    """Email queue statistics."""

    total_emails: int = 0
    pending_count: int = 0
    processing_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    scheduled_count: int = 0
    success_rate: float = 0.0  # Percentage
    average_retry_count: float = 0.0

    def calculate_success_rate(self) -> None:
        """Calculate success rate based on sent vs failed."""
        total_processed = self.sent_count + self.failed_count
        if total_processed > 0:
            self.success_rate = (self.sent_count / total_processed) * 100
        else:
            self.success_rate = 0.0
