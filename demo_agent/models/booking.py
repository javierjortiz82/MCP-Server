"""Pydantic models for booking demo requests.

Models for validating and handling demo booking form submissions
with reCAPTCHA verification and phone number validation.

Author: Odiseo AI Team
Created: 2025-11-09
"""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class BookingRequest(BaseModel):
    """Demo booking request from website form.

    Attributes:
        full_name: Customer's full name (2-255 chars)
        email: Valid email address
        phone: International phone number (E.164 format preferred)
        country_code: Phone country code (+1, +506, etc.)
        company: Company name (optional)
        preferred_date: Preferred demo date (YYYY-MM-DD)
        preferred_time: Preferred demo time (HH:MM)
        message: Additional notes (optional, max 2000 chars)
        recaptcha_token: Google reCAPTCHA v3 token for verification
    """

    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, min_length=7, max_length=50)
    country_code: str | None = Field(default=None, min_length=2, max_length=10)
    company: str | None = Field(default=None, max_length=255)
    preferred_date: date
    preferred_time: time
    message: str | None = Field(default=None, max_length=2000)
    recaptcha_token: str = Field(min_length=20)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Ensure full name contains at least one letter."""
        if not any(c.isalpha() for c in v):
            raise ValueError("Full name must contain at least one letter")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate phone number format."""
        if v is None or v.strip() == "":
            return None

        # Remove spaces and common formatting
        cleaned = v.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Must start with + for international format
        if not cleaned.startswith("+"):
            raise ValueError("Phone number must start with + for international format")

        # Must contain only digits after the +
        if not cleaned[1:].isdigit():
            raise ValueError("Phone number must contain only digits after +")

        return v.strip()

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str | None) -> str | None:
        """Trim company name or return None if empty."""
        if v is None or v.strip() == "":
            return None
        return v.strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str | None) -> str | None:
        """Trim message or return None if empty."""
        if v is None or v.strip() == "":
            return None
        return v.strip()


class BookingResponse(BaseModel):
    """Response after booking submission.

    Attributes:
        success: Whether the booking was created successfully
        message: Human-readable status message
        booking_id: Database ID of created booking (if successful)
    """

    success: bool
    message: str
    booking_id: int | None = None
