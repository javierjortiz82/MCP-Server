"""Contact Request Models.

Pydantic models for contact form submissions.

Author: Odiseo AI Team
Created: 2025-11-09
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactRequest(BaseModel):
    """Contact form submission request.

    Attributes:
        full_name: Full name of contact (2-255 characters)
        email: Valid email address
        phone: Optional phone number with country code (E.164 format recommended)
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'US', 'CR')
        company: Optional company name
        message: Contact message (10-2000 characters)
        contact_type: Type of inquiry (general, sales, support)
        recaptcha_token: Google reCAPTCHA v3 token for spam prevention

    Example:
        >>> contact = ContactRequest(
        ...     full_name="John Doe",
        ...     email="john@example.com",
        ...     phone="+15551234567",
        ...     country_code="US",
        ...     company="Acme Inc",
        ...     message="I want to learn more about your services",
        ...     contact_type="sales",
        ...     recaptcha_token="03AGdBq..."
        ... )
    """

    full_name: str = Field(
        min_length=2,
        max_length=255,
        description="Full name of the contact person",
        examples=["John Doe", "María García"],
    )

    email: EmailStr = Field(
        description="Valid email address",
        examples=["john@example.com", "maria@empresa.com"],
    )

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=50,
        description="Phone number with country code (E.164 format recommended)",
        examples=["+15551234567", "+506 8765 4321"],
    )

    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=10,
        description="ISO 3166-1 alpha-2 country code",
        examples=["US", "CR", "ES", "MX"],
    )

    company: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Company or organization name",
        examples=["Acme Inc", "Tech Startup"],
    )

    message: str = Field(
        min_length=10,
        max_length=2000,
        description="Contact message or inquiry",
        examples=["I want to learn more about your services"],
    )

    contact_type: Literal["general", "sales", "support"] = Field(
        default="general",
        description="Type of inquiry",
    )

    recaptcha_token: str = Field(
        min_length=20,
        description="Google reCAPTCHA v3 token",
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name contains at least one letter."""
        if not any(c.isalpha() for c in v):
            raise ValueError("Full name must contain at least one letter")
        return v.strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not just whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or only whitespace")
        return v.strip()

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str | None) -> str | None:
        """Validate country code is uppercase."""
        if v:
            return v.upper().strip()
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "full_name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+15551234567",
                    "country_code": "US",
                    "company": "Acme Inc",
                    "message": "I want to learn more about your AI agent services",
                    "contact_type": "sales",
                    "recaptcha_token": "03AGdBq25abcd...",
                }
            ]
        }
    }


class ContactResponse(BaseModel):
    """Contact form submission response.

    Attributes:
        success: Whether submission was successful
        message: Human-readable message
        contact_id: Database ID of created contact request
        created_at: ISO 8601 timestamp of creation

    Example:
        >>> response = ContactResponse(
        ...     success=True,
        ...     message="Thank you! We'll contact you soon.",
        ...     contact_id=42,
        ...     created_at="2025-11-09T10:30:00Z"
        ... )
    """

    success: bool = Field(description="Whether submission was successful")

    message: str = Field(
        description="Human-readable success or error message",
        examples=[
            "Thank you! We'll contact you soon.",
            "Invalid reCAPTCHA token. Please try again.",
        ],
    )

    contact_id: int | None = Field(
        default=None,
        description="Database ID of created contact request",
    )

    created_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp of creation",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Thank you! We'll contact you soon.",
                    "contact_id": 42,
                    "created_at": "2025-11-09T10:30:00Z",
                }
            ]
        }
    }


class ContactStatus(BaseModel):
    """Contact request status for admin dashboard.

    Attributes:
        id: Database ID
        full_name: Contact person name
        email: Email address
        contact_type: Type of inquiry
        status: Current status
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> status = ContactStatus(
        ...     id=42,
        ...     full_name="John Doe",
        ...     email="john@example.com",
        ...     contact_type="sales",
        ...     status="pending",
        ...     created_at="2025-11-09T10:30:00Z",
        ...     updated_at="2025-11-09T10:30:00Z"
        ... )
    """

    id: int
    full_name: str
    email: str
    contact_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
