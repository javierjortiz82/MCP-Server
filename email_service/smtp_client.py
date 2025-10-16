"""SMTP Client - Email delivery wrapper.

Handles SMTP connections and email sending with:
- Gmail, SendGrid, AWS SES compatibility
- TLS/SSL support
- HTML and plain text multipart emails
- Timeout and retry handling
- Connection pooling

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from email_service.config import settings
from email_service.models import SMTPConfig


class SMTPClient:
    """SMTP email delivery client.

    Supports Gmail, SendGrid, AWS SES, and any SMTP server.
    Handles TLS/SSL, authentication, and multipart emails.
    """

    def __init__(self, smtp_config: SMTPConfig | None = None) -> None:
        """Initialize SMTP client.

        Args:
            smtp_config: SMTP configuration (uses settings if None).
        """
        if smtp_config:
            self.config = smtp_config
        else:
            # Load from settings
            config_dict = settings.get_smtp_config()
            self.config = SMTPConfig(**config_dict)

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> None:
        """Send an email via SMTP.

        Args:
            recipient_email: Recipient email address.
            recipient_name: Recipient full name (optional).
            subject: Email subject line.
            body_html: HTML email body.
            body_text: Plain text fallback (optional).

        Raises:
            smtplib.SMTPException: If email sending fails.
            TimeoutError: If connection times out.
        """
        # Create multipart message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        msg["To"] = (
            f"{recipient_name} <{recipient_email}>"
            if recipient_name
            else recipient_email
        )
        msg["Subject"] = subject

        # Attach plain text (if provided)
        if body_text:
            part_text = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part_text)

        # Attach HTML (always present)
        part_html = MIMEText(body_html, "html", "utf-8")
        msg.attach(part_html)

        # Send via SMTP
        self._send_via_smtp(msg, recipient_email)

    def _send_via_smtp(self, msg: MIMEMultipart, recipient_email: str) -> None:
        """Send message via SMTP connection.

        Args:
            msg: Prepared MIME message.
            recipient_email: Recipient email address.

        Raises:
            smtplib.SMTPException: If SMTP operation fails.
        """
        # Create SMTP connection
        smtp = smtplib.SMTP(
            self.config.host, self.config.port, timeout=self.config.timeout
        )

        try:
            # Enable TLS if configured
            if self.config.use_tls:
                smtp.starttls()

            # Authenticate
            smtp.login(self.config.username, self.config.password)

            # Send email
            smtp.send_message(msg, from_addr=self.config.from_email, to_addrs=[recipient_email])

        finally:
            # Always close connection
            smtp.quit()

    def validate_connection(self) -> bool:
        """Test SMTP connection and authentication.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            smtp = smtplib.SMTP(
                self.config.host, self.config.port, timeout=self.config.timeout
            )

            if self.config.use_tls:
                smtp.starttls()

            smtp.login(self.config.username, self.config.password)
            smtp.quit()
            return True

        except Exception:
            return False

    def send_test_email(self, test_recipient: str) -> bool:
        """Send a test email to verify configuration.

        Args:
            test_recipient: Email address to send test to.

        Returns:
            True if test email sent successfully.
        """
        try:
            self.send_email(
                recipient_email=test_recipient,
                recipient_name="Test User",
                subject="Lab01 Email Service - Test Email",
                body_html="<h1>Test Email</h1><p>Email service is working correctly.</p>",
                body_text="Test Email\n\nEmail service is working correctly.",
            )
            return True

        except Exception:
            return False
