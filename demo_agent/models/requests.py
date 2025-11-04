"""Demo agent request models.

Pydantic v2 models for HTTP request validation and documentation.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""


from pydantic import BaseModel, Field, validator


class Metadata(BaseModel):
    """Request metadata for tracking and rate limiting.

    Attributes:
        ip: Client IP address (required for IP-based rate limiting)
        user_agent: HTTP User-Agent header (for fingerprinting)
        fingerprint: Client fingerprint hash (for VPN detection)
    """

    ip: str = Field(..., description="Client IP address (IPv4 or IPv6)")
    user_agent: str | None = Field(None, description="HTTP User-Agent header")
    fingerprint: str | None = Field(None, description="Client fingerprint hash")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "ip": "203.0.113.42",
                "user_agent": "Mozilla/5.0...",
                "fingerprint": "abc123def456",
            }
        }


class DemoRequest(BaseModel):
    """HTTP POST request for demo agent.

    Attributes:
        user_id: Authenticated user ID (REQUIRED - from demo_users table)
        session_id: Session token for tracking
        input: User query/question
        language: Language preference (es|en, default: es)
        metadata: Request metadata (IP, fingerprint, etc.)

    Note:
        user_id is now REQUIRED. Users must register and verify email
        before accessing demo chat.
    """

    user_id: int = Field(..., description="Authenticated user ID (required)", gt=0)
    session_id: str | None = Field(None, description="Session token (tracking)")
    input: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User query or question",
    )
    language: str = Field(
        default="es",
        pattern="^(es|en)$",
        description="Language preference (es|en)",
    )
    metadata: Metadata = Field(
        ...,
        description="Request metadata (IP, fingerprint, etc.)",
    )

    @validator("input")
    def sanitize_input(cls, v: str) -> str:
        """Sanitize user input."""
        return v.strip()[:2000]

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "user_id": 123,
                "session_id": "sess_abc",
                "input": "¿Cuánto cuesta un laptop?",
                "language": "es",
                "metadata": {
                    "ip": "203.0.113.42",
                    "user_agent": "Mozilla/5.0...",
                    "fingerprint": "abc123def",
                },
            }
        }
