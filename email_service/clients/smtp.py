"""SMTP client for email delivery.

Provides email sending via SMTP with support for Gmail, SendGrid, AWS SES,
and compatible SMTP servers. Handles multipart emails, TLS/SSL, and error handling.

Author: Lab01-MCP Team
Created: 2025-10-18
Version: 1.0.0
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email_service.config import EmailConfig
from email_service.core.exceptions import SMTPClientError
from email_service.core.logger import get_logger
from email_service.models.smtp_config import SMTPConfig
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger

logger = get_logger(__name__)


class SMTPClient:
    """SMTP email delivery client.

    Sends emails via SMTP with support for multiple providers
    (Gmail, SendGrid, AWS SES). Handles TLS/SSL encryption,
    authentication, and multipart emails (HTML + plaintext).

    Attributes:
        config: SMTP configuration.

    Example:
        client = SMTPClient()
        client.send_email(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            subject="Welcome",
            body_html="<h1>Hello!</h1>",
        )
    """

    def __init__(self, smtp_config: SMTPConfig | None = None) -> None:
        """Initialize SMTP client.

        Args:
            smtp_config: SMTP configuration (uses EmailConfig if None).

        Raises:
            SMTPClientError: If configuration is invalid.
        """
        # Initialize observability (OPCIÓN 6)
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()

        if smtp_config:
            self.config = smtp_config
        else:
            # Load from global settings
            email_config = EmailConfig()
            config_dict = email_config.get_smtp_config()
            self.config = SMTPConfig(
                host=str(config_dict["host"]),
                port=int(config_dict["port"]),
                username=str(config_dict["username"]),
                password=str(config_dict["password"]),
                from_email=str(config_dict["from_email"]),
                from_name=str(config_dict["from_name"]),
                use_tls=bool(config_dict["use_tls"]),
                timeout=int(config_dict["timeout"]),
            )

        logger.info(
            f"🔧 SMTP Client initialized: {self.config.host}:{self.config.port}"
        )
        self.logger.info(
            "SMTP client initialized",
            host=self.config.host,
            port=self.config.port
        )

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> None:
        """Send an email via SMTP.

        Constructs a multipart MIME message with HTML and optional plaintext
        parts, then delivers via SMTP connection.

        Args:
            recipient_email: Recipient email address.
            recipient_name: Recipient full name (optional).
            subject: Email subject line.
            body_html: HTML-formatted email body.
            body_text: Plain-text fallback (optional).

        Raises:
            SMTPClientError: If email sending fails.

        Example:
            client.send_email(
                recipient_email="user@example.com",
                recipient_name="John Doe",
                subject="Booking Confirmed",
                body_html="<h1>Confirmed!</h1>",
                body_text="Your booking is confirmed.",
            )
        """
        try:
            # Track SMTP send operation (OPCIÓN 6)
            with self.metrics.record_latency(
                "smtp_send",
                tags={"recipient": recipient_email}
            ):
                # Create multipart message
                msg = MIMEMultipart("alternative")
                msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
                msg["To"] = (
                    f"{recipient_name} <{recipient_email}>"
                    if recipient_name
                    else recipient_email
                )
                msg["Subject"] = subject

                # Attach plaintext part (if provided)
                if body_text:
                    part_text = MIMEText(body_text, "plain", "utf-8")
                    msg.attach(part_text)

                # Attach HTML part (always present)
                part_html = MIMEText(body_html, "html", "utf-8")
                msg.attach(part_html)

                # Send via SMTP
                self._send_via_smtp(msg, recipient_email)

            logger.info(
                f"✅ Email sent to {recipient_email} - " f"Subject: {subject[:50]}..."
            )
            self.logger.info(
                "Email sent via SMTP",
                recipient=recipient_email,
                subject=subject[:50]
            )
            self.metrics.increment_counter("smtp_sends_successful")

        except Exception as e:
            logger.error(
                f"❌ Failed to send email to {recipient_email}: {e}",
                exc_info=True,
            )
            self.logger.exception(
                "SMTP send failed",
                recipient=recipient_email,
                subject=subject[:50]
            )
            self.metrics.increment_counter("smtp_sends_failed")
            raise SMTPClientError(
                f"Failed to send email to {recipient_email}: {str(e)}",
                is_transient=self._is_transient_error(e),
            ) from e

    def _send_via_smtp(self, msg: MIMEMultipart, recipient_email: str) -> None:
        """Send message via SMTP connection.

        Args:
            msg: Prepared MIME message.
            recipient_email: Recipient email address.

        Raises:
            smtplib.SMTPException: If SMTP operation fails.
            TimeoutError: If connection times out.
        """
        smtp = None
        try:
            # Create SMTP connection
            logger.debug(
                f"🔌 Connecting to SMTP: {self.config.host}:{self.config.port}"
            )
            smtp = smtplib.SMTP(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout,
            )

            # Enable TLS if configured
            if self.config.use_tls:
                logger.debug("🔐 Starting TLS...")
                smtp.starttls()

            # Authenticate
            logger.debug("🔑 Authenticating...")
            smtp.login(self.config.username, self.config.password)

            # Send email
            logger.debug(f"📤 Sending email to {recipient_email}...")
            smtp.send_message(
                msg,
                from_addr=self.config.from_email,
                to_addrs=[recipient_email],
            )

        finally:
            # Always close connection
            if smtp:
                try:
                    smtp.quit()
                except Exception:
                    pass

    def validate_connection(self) -> bool:
        """Test SMTP connection and authentication.

        Attempts to connect and authenticate with the SMTP server
        without sending any email.

        Returns:
            True if connection successful, False otherwise.

        Example:
            if not client.validate_connection():
                logger.error("SMTP configuration invalid")
        """
        smtp = None
        try:
            logger.info("🧪 Testing SMTP connection...")
            smtp = smtplib.SMTP(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout,
            )

            if self.config.use_tls:
                smtp.starttls()

            smtp.login(self.config.username, self.config.password)
            logger.info("✅ SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"❌ SMTP connection test failed: {e}")
            return False

        finally:
            if smtp:
                try:
                    smtp.quit()
                except Exception:
                    pass

    def send_test_email(self, test_recipient: str) -> bool:
        """Send a test email to verify configuration.

        Sends a simple test email to verify SMTP configuration is working.

        Args:
            test_recipient: Email address to send test email to.

        Returns:
            True if test email sent successfully, False otherwise.

        Example:
            if client.send_test_email("admin@example.com"):
                print("Configuration verified!")
        """
        try:
            logger.info(f"📧 Sending test email to {test_recipient}...")
            self.send_email(
                recipient_email=test_recipient,
                recipient_name="Test User",
                subject="Lab01 Email Service - Test Email",
                body_html=(
                    "<h1>Test Email</h1>" "<p>Email service is working correctly.</p>"
                ),
                body_text="Test Email\n\nEmail service is working correctly.",
            )
            logger.info("✅ Test email sent successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Test email failed: {e}")
            return False

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        """Determine if error is temporary (retryable).

        Args:
            error: Exception to evaluate.

        Returns:
            True if error is temporary (connection, timeout),
            False if permanent.
        """
        error_str = str(error).lower()
        transient_keywords = [
            "timeout",
            "connection",
            "temporarily",
            "try again",
            "unavailable",
            "service",
        ]
        return any(keyword in error_str for keyword in transient_keywords)
