"""Security Audit Logging Module.

Provides comprehensive security event logging for threat detection, incident
response, and compliance auditing.

SECURITY (CWE-778 fix): Insufficient Logging
- Logs all authentication attempts (success/failure)
- Logs authorization failures
- Logs input validation failures
- Logs rate limiting violations
- Logs suspicious behavior detection
- Redacts sensitive data (passwords, tokens, PII)

Critical Security Events Logged:
- Authentication failures (potential brute force)
- Authorization violations (potential privilege escalation)
- Rate limit exceeded (potential abuse)
- Input validation failures (potential injection attacks)
- Session fixation attempts
- CSRF token validation failures
- Webhook signature verification failures
- Oversized request attempts (DoS)

Log Format:
- Structured JSON for SIEM integration
- Timestamp (ISO 8601 with timezone)
- Event type and severity
- User/IP information (for correlation)
- Action outcome (success/failure/blocked)
- Relevant context (sanitized)

References:
- OWASP Logging Cheat Sheet
- NIST SP 800-92: Guide to Computer Security Log Management
- PCI DSS Requirement 10: Log and Monitor All Access
- GDPR Article 32: Security of Processing

Author: Lab01-MCP Team
Created: 2025-11-07
Version: 1.0.0 (Security-Hardened - Phase 4)
"""

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from demo_agent.logger import logger


class SecurityEventType(Enum):
    """Security event types for audit logging.

    These event types align with OWASP and NIST guidelines for
    security monitoring and incident detection.
    """

    # Authentication Events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_MISSING = "auth_missing"
    AUTH_INVALID_TOKEN = "auth_invalid_token"

    # Authorization Events
    AUTHZ_DENIED = "authz_denied"
    AUTHZ_PRIVILEGE_ESCALATION = "authz_privilege_escalation"

    # Rate Limiting Events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_WARNING = "rate_limit_warning"

    # Input Validation Events
    INPUT_VALIDATION_FAILED = "input_validation_failed"
    OVERSIZED_REQUEST = "oversized_request"
    MALFORMED_REQUEST = "malformed_request"

    # Session Security Events
    SESSION_FIXATION_ATTEMPT = "session_fixation_attempt"
    SESSION_HIJACKING_ATTEMPT = "session_hijacking_attempt"
    SESSION_EXPIRED = "session_expired"

    # Injection Attack Attempts
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    COMMAND_INJECTION_ATTEMPT = "command_injection_attempt"

    # Webhook Security Events
    WEBHOOK_SIGNATURE_INVALID = "webhook_signature_invalid"
    WEBHOOK_REPLAY_ATTEMPT = "webhook_replay_attempt"

    # Abuse Detection
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    ACCOUNT_ENUMERATION_ATTEMPT = "account_enumeration_attempt"
    CREDENTIAL_STUFFING_ATTEMPT = "credential_stuffing_attempt"

    # Configuration Changes
    CONFIG_CHANGE = "config_change"
    SECURITY_POLICY_CHANGE = "security_policy_change"


class SecurityEventSeverity(Enum):
    """Severity levels for security events."""

    LOW = "low"  # Informational, no immediate action needed
    MEDIUM = "medium"  # Warrants review, potential security concern
    HIGH = "high"  # Requires immediate investigation
    CRITICAL = "critical"  # Requires urgent response, active attack


class SecurityAuditLogger:
    """Enhanced security audit logger with structured event logging.

    SECURITY: Provides comprehensive audit trail for security events
    while ensuring no sensitive data is leaked in logs.

    Features:
    - Structured JSON logging for SIEM integration
    - Automatic PII/sensitive data redaction
    - Event correlation via request IDs
    - Severity-based alerting
    - Compliance-ready audit trails
    """

    # Sensitive field names to redact (case-insensitive)
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "jwt",
        "session",
        "cookie",
        "credit_card",
        "ssn",
        "email",  # Partial redaction
    }

    def __init__(self, enable_pii_logging: bool = False):
        """Initialize security audit logger.

        Args:
            enable_pii_logging: Enable PII logging (dev/debug only, NEVER in production).
        """
        self.enable_pii_logging = enable_pii_logging

        if enable_pii_logging:
            logger.warning(
                "⚠️ SECURITY WARNING: PII logging is ENABLED. "
                "This should NEVER be enabled in production!"
            )

    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        success: bool = False,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Log a security event with structured data.

        Args:
            event_type: Type of security event.
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL).
            user_id: User ID involved (if applicable).
            ip_address: Client IP address.
            endpoint: API endpoint involved.
            success: Whether the action succeeded.
            message: Human-readable event description.
            details: Additional context (will be sanitized).
            correlation_id: Request correlation ID for tracing.
        """
        # Build structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "success": success,
            "user_id": user_id,
            "ip_address": self._redact_ip(ip_address) if ip_address else None,
            "endpoint": endpoint,
            "message": message,
            "correlation_id": correlation_id,
        }

        # Sanitize and add details
        if details:
            log_entry["details"] = self._sanitize_details(details)

        # Log at appropriate level based on severity
        log_message = f"SECURITY EVENT: {message or event_type.value}"

        if severity == SecurityEventSeverity.CRITICAL:
            logger.critical(log_message, **log_entry)
        elif severity == SecurityEventSeverity.HIGH:
            logger.error(log_message, **log_entry)
        elif severity == SecurityEventSeverity.MEDIUM:
            logger.warning(log_message, **log_entry)
        else:  # LOW
            logger.info(log_message, **log_entry)

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize details dict to remove sensitive data.

        SECURITY (CWE-532 fix): Prevents sensitive data exposure in logs.

        Args:
            details: Details dictionary to sanitize.

        Returns:
            Sanitized details dict.
        """
        sanitized = {}

        for key, value in details.items():
            key_lower = key.lower()

            # Check if field is sensitive
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                if self.enable_pii_logging:
                    # Dev mode: show first/last chars only
                    sanitized[key] = self._partial_redact(str(value))
                else:
                    # Production: full redaction
                    sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Safe field - include as-is
                sanitized[key] = value

        return sanitized

    def _partial_redact(self, value: str) -> str:
        """Partially redact sensitive value (show first/last chars).

        Args:
            value: Value to partially redact.

        Returns:
            Partially redacted string.

        Example:
            "my_secret_token_123" -> "my...123"
        """
        if not value or len(value) < 6:
            return "[REDACTED]"

        return f"{value[:2]}...{value[-3:]}"

    def _redact_ip(self, ip: str) -> str:
        """Redact IP address for GDPR compliance.

        SECURITY (GDPR): IP addresses are PII and must be handled carefully.

        Args:
            ip: IP address to redact.

        Returns:
            Redacted IP (last octet removed for IPv4, last 64 bits for IPv6).

        Example:
            "192.168.1.42" -> "192.168.1.XXX"
        """
        if not ip:
            return "[UNKNOWN]"

        if self.enable_pii_logging:
            return ip  # Dev mode: keep full IP

        # IPv4: redact last octet
        if "." in ip and ":" not in ip:
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.XXX"

        # IPv6: redact last 64 bits
        if ":" in ip:
            parts = ip.split(":")
            if len(parts) >= 4:
                return ":".join(parts[:4]) + "::XXXX"

        # Fallback
        return "[IP_REDACTED]"


# Global instance
_audit_logger: Optional[SecurityAuditLogger] = None


def get_audit_logger(enable_pii_logging: bool = False) -> SecurityAuditLogger:
    """Get the global security audit logger instance.

    Args:
        enable_pii_logging: Enable PII logging (dev only).

    Returns:
        SecurityAuditLogger instance.
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger(enable_pii_logging=enable_pii_logging)

    return _audit_logger


# Convenience functions for common security events

def log_auth_failure(
    user_id: Optional[int],
    ip_address: str,
    endpoint: str,
    reason: str,
    correlation_id: Optional[str] = None,
) -> None:
    """Log authentication failure event.

    Args:
        user_id: User ID that failed authentication (if known).
        ip_address: Client IP address.
        endpoint: Endpoint where auth failed.
        reason: Reason for failure.
        correlation_id: Request correlation ID.
    """
    get_audit_logger().log_event(
        event_type=SecurityEventType.AUTH_FAILURE,
        severity=SecurityEventSeverity.MEDIUM,
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        success=False,
        message=f"Authentication failed: {reason}",
        correlation_id=correlation_id,
    )


def log_rate_limit_exceeded(
    user_id: int,
    ip_address: str,
    endpoint: str,
    tokens_used: int,
    tokens_limit: int,
    correlation_id: Optional[str] = None,
) -> None:
    """Log rate limit exceeded event.

    Args:
        user_id: User ID that exceeded rate limit.
        ip_address: Client IP address.
        endpoint: Endpoint accessed.
        tokens_used: Tokens consumed.
        tokens_limit: Token limit.
        correlation_id: Request correlation ID.
    """
    get_audit_logger().log_event(
        event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
        severity=SecurityEventSeverity.MEDIUM,
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        success=False,
        message=f"Rate limit exceeded: {tokens_used}/{tokens_limit} tokens",
        details={"tokens_used": tokens_used, "tokens_limit": tokens_limit},
        correlation_id=correlation_id,
    )


def log_input_validation_failed(
    user_id: Optional[int],
    ip_address: str,
    endpoint: str,
    field_name: str,
    reason: str,
    correlation_id: Optional[str] = None,
) -> None:
    """Log input validation failure event.

    Args:
        user_id: User ID (if known).
        ip_address: Client IP address.
        endpoint: Endpoint accessed.
        field_name: Field that failed validation.
        reason: Validation failure reason.
        correlation_id: Request correlation ID.
    """
    get_audit_logger().log_event(
        event_type=SecurityEventType.INPUT_VALIDATION_FAILED,
        severity=SecurityEventSeverity.LOW,
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        success=False,
        message=f"Input validation failed: {field_name} - {reason}",
        details={"field": field_name, "reason": reason},
        correlation_id=correlation_id,
    )


def log_suspicious_behavior(
    user_id: Optional[int],
    ip_address: str,
    endpoint: str,
    behavior_type: str,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Log suspicious behavior detection event.

    Args:
        user_id: User ID involved.
        ip_address: Client IP address.
        endpoint: Endpoint accessed.
        behavior_type: Type of suspicious behavior detected.
        details: Additional context.
        correlation_id: Request correlation ID.
    """
    get_audit_logger().log_event(
        event_type=SecurityEventType.SUSPICIOUS_BEHAVIOR,
        severity=SecurityEventSeverity.HIGH,
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        success=False,
        message=f"Suspicious behavior detected: {behavior_type}",
        details=details,
        correlation_id=correlation_id,
    )
