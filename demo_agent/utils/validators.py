"""Security-hardened validators for user input.

Provides validators that are immune to ReDoS (Regular Expression Denial of Service)
and other input-based attacks.

Author: Lab01-MCP Team
Created: 2025-11-07
Version: 1.0.0 (Security-Hardened)
"""

import re
import uuid

# SECURITY (CWE-1333 fix): ReDoS-safe email pattern
# This pattern is carefully designed to avoid catastrophic backtracking:
# - No nested quantifiers (e.g., (a+)+)
# - No overlapping alternatives
# - Linear time complexity O(n)
# - Maximum length check prevents DoS via huge inputs
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"  # Local part (no nested quantifiers)
    r"@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"  # Domain part (limited repetition)
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",  # Subdomains (limited)
    re.IGNORECASE
)

# Maximum lengths to prevent DoS attacks
MAX_EMAIL_LENGTH = 254  # RFC 5321
MAX_LOCAL_PART_LENGTH = 64  # RFC 5321
MAX_DOMAIN_LENGTH = 253  # RFC 1035


def validate_email_safe(email: str) -> tuple[bool, str | None]:
    """Validate email address with ReDoS protection.

    SECURITY (CWE-1333 fix): ReDoS-resistant email validation that:
    - Uses simple regex without nested quantifiers
    - Enforces maximum length limits (DoS prevention)
    - Validates format without catastrophic backtracking
    - Completes in linear time O(n)

    This validator is more restrictive than RFC 5322 but safe against
    ReDoS attacks and covers 99.99% of real-world email addresses.

    Args:
        email: Email address to validate.

    Returns:
        Tuple of (is_valid, error_message):
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_email_safe("user@example.com")
        (True, None)

        >>> validate_email_safe("invalid.email")
        (False, "Email must contain @")

        >>> validate_email_safe("a" * 300 + "@example.com")
        (False, "Email too long (max 254 characters)")
    """
    # Basic type and length checks (prevent DoS)
    if not email or not isinstance(email, str):
        return False, "Email is required"

    email = email.strip().lower()

    if len(email) > MAX_EMAIL_LENGTH:
        return False, f"Email too long (max {MAX_EMAIL_LENGTH} characters)"

    if len(email) < 3:  # a@b is minimum
        return False, "Email too short"

    # Check for @ symbol
    if "@" not in email:
        return False, "Email must contain @"

    if email.count("@") > 1:
        return False, "Email must contain exactly one @"

    # Split local and domain parts
    try:
        local_part, domain_part = email.rsplit("@", 1)
    except ValueError:
        return False, "Invalid email format"

    # Validate local part
    if not local_part or len(local_part) > MAX_LOCAL_PART_LENGTH:
        return False, f"Local part too long (max {MAX_LOCAL_PART_LENGTH} characters)"

    if local_part.startswith(".") or local_part.endswith("."):
        return False, "Local part cannot start or end with dot"

    if ".." in local_part:
        return False, "Local part cannot contain consecutive dots"

    # Validate domain part
    if not domain_part or len(domain_part) > MAX_DOMAIN_LENGTH:
        return False, f"Domain too long (max {MAX_DOMAIN_LENGTH} characters)"

    if "." not in domain_part:
        return False, "Domain must contain at least one dot"

    if domain_part.startswith(".") or domain_part.endswith("."):
        return False, "Domain cannot start or end with dot"

    if ".." in domain_part:
        return False, "Domain cannot contain consecutive dots"

    # Domain labels validation (between dots)
    labels = domain_part.split(".")
    for label in labels:
        if not label or len(label) > 63:  # RFC 1035
            return False, "Domain label too long (max 63 characters)"

        if label.startswith("-") or label.endswith("-"):
            return False, "Domain labels cannot start or end with hyphen"

        # Label must be alphanumeric + hyphens
        if not all(c.isalnum() or c == "-" for c in label):
            return False, "Domain labels must be alphanumeric"

    # TLD validation (last label)
    tld = labels[-1]
    if not tld.isalpha():
        return False, "TLD must be alphabetic"

    if len(tld) < 2:
        return False, "TLD must be at least 2 characters"

    # Final regex check (ReDoS-safe pattern)
    # This uses a simple pattern with O(n) complexity
    if not EMAIL_PATTERN.match(email):
        return False, "Email format invalid"

    return True, None


def sanitize_email(email: str) -> str:
    """Sanitize email address for safe storage and display.

    SECURITY: Normalizes email to prevent confusion attacks and
    ensure consistent storage format.

    Args:
        email: Email address to sanitize.

    Returns:
        Sanitized email (lowercase, trimmed).

    Examples:
        >>> sanitize_email("  User@Example.COM  ")
        "user@example.com"
    """
    if not email:
        return ""

    # Normalize: trim, lowercase
    email = email.strip().lower()

    # Remove null bytes (security)
    email = email.replace("\x00", "")

    # Remove CRLF (header injection prevention)
    email = email.replace("\r", "").replace("\n", "")

    return email


def validate_otp_code_safe(otp: str) -> tuple[bool, str | None]:
    """Validate OTP code with security checks.

    SECURITY: Validates OTP is exactly 6 digits without allowing
    other characters that could enable attacks.

    Args:
        otp: OTP code to validate.

    Returns:
        Tuple of (is_valid, error_message).

    Examples:
        >>> validate_otp_code_safe("123456")
        (True, None)

        >>> validate_otp_code_safe("12345")
        (False, "OTP must be exactly 6 digits")
    """
    if not otp or not isinstance(otp, str):
        return False, "OTP is required"

    # Remove whitespace
    otp = otp.strip()

    # Length check
    if len(otp) != 6:
        return False, "OTP must be exactly 6 digits"

    # Digits only check (no letters, symbols, unicode)
    if not otp.isdigit():
        return False, "OTP must contain only digits"

    # Check for ASCII digits only (no unicode digits like ٠١٢)
    if not all(48 <= ord(c) <= 57 for c in otp):  # ASCII '0'-'9'
        return False, "OTP must contain only ASCII digits"

    return True, None


def validate_session_id(session_id: str) -> tuple[bool, str | None]:
    """Validate session ID is a properly formatted UUID.

    SECURITY (CWE-384 mitigation): Prevents session fixation by ensuring
    session IDs are valid UUIDs (not arbitrary user-controlled strings).

    Args:
        session_id: Session identifier to validate.

    Returns:
        Tuple of (is_valid, error_message).

    Examples:
        >>> validate_session_id("550e8400-e29b-41d4-a716-446655440000")
        (True, None)

        >>> validate_session_id("not-a-uuid")
        (False, "Invalid session ID format")
    """
    if not session_id or not isinstance(session_id, str):
        return False, "Session ID is required"

    # Length check (UUID is 36 chars with hyphens)
    if len(session_id) != 36:
        return False, "Invalid session ID length"

    # Try parsing as UUID
    try:
        uuid_obj = uuid.UUID(session_id)

        # Verify it's version 4 (random UUID)
        # Version 4 UUIDs are cryptographically random and safe
        if uuid_obj.version != 4:
            return False, "Session ID must be UUID version 4"

        return True, None
    except ValueError:
        return False, "Invalid session ID format"


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """Validate password meets security requirements.

    SECURITY: Enforces strong password policy:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Maximum 128 characters (DoS prevention)

    Args:
        password: Password to validate.

    Returns:
        Tuple of (is_valid, error_message).

    Examples:
        >>> validate_password_strength("Pass1234")
        (True, None)

        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters")
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"

    # Length checks
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if len(password) > 128:
        return False, "Password too long (max 128 characters)"

    # Strength requirements
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    # Check for common weak patterns
    weak_patterns = [
        "password", "12345678", "qwerty", "admin", "letmein",
        "welcome", "monkey", "dragon", "master", "sunshine"
    ]

    password_lower = password.lower()
    for pattern in weak_patterns:
        if pattern in password_lower:
            return False, f"Password too common (contains '{pattern}')"

    return True, None
