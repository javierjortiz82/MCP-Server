"""Email Integration Service - Send OTP via Email Queue.

Integrates with email_service worker by enqueueing OTP verification emails
directly in PostgreSQL queue. The email_service worker processes the queue
asynchronously.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 2.0.0
"""

import json
from datetime import datetime, timezone

from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.logger import logger


class EmailIntegrationService:
    """Service for sending OTP emails via PostgreSQL email queue.

    Enqueues OTP verification emails in the database queue. The email_service
    worker (mcp-email-worker container) processes the queue asynchronously.

    Email Queue Table:
        Schema: {SCHEMA_NAME}.email_queue

    Email Worker:
        Container: mcp-email-worker (polls queue every few seconds)

    Email Template:
        - Subject: "Verify your email - {otp_code}"
        - Body: HTML template with OTP code and expiration time
        - Priority: 1 (high priority for verification emails)
    """

    def __init__(self):
        """Initialize EmailIntegrationService with database connection."""
        self.db = get_db()
        logger.info("EmailIntegrationService initialized (PostgreSQL queue mode)")

    async def send_otp_email(
        self,
        recipient_email: str,
        recipient_name: str,
        otp_code: str,
        expires_at: datetime,
        language: str = "es",
    ) -> tuple[bool, str]:
        """Send OTP verification email via email queue.

        Args:
            recipient_email: User's email address.
            recipient_name: User's full name.
            otp_code: 6-digit OTP code (plain-text).
            expires_at: OTP expiration timestamp.
            language: Email language (es, en).

        Returns:
            Tuple[success, message]:
            - success: True if email enqueued successfully
            - message: Success/error message

        Email Content:
            - Subject: "Verify your email - Demo Chat"
            - Body: HTML with OTP code, expiration time, instructions
            - Priority: 1 (high priority for verification)
        """
        try:
            logger.info(f"Enqueueing OTP email to {recipient_email}")

            # Calculate expiration time in hours
            now = datetime.now(timezone.utc)
            hours_remaining = int((expires_at - now).total_seconds() / 3600)

            # Build email subject (localized)
            subject = self._get_subject(language)

            # Build HTML body
            body_html = self._build_html_body(
                recipient_name=recipient_name,
                otp_code=otp_code,
                hours_remaining=hours_remaining,
                language=language,
            )

            # Build plain-text body (fallback)
            body_text = self._build_text_body(
                recipient_name=recipient_name,
                otp_code=otp_code,
                hours_remaining=hours_remaining,
                language=language,
            )

            # Prepare template context for email_service
            template_context = {
                "otp_code": otp_code,
                "expires_at": expires_at.isoformat(),
                "hours_remaining": hours_remaining,
                "language": language,
            }

            # Enqueue email in PostgreSQL
            query = f"""
                SELECT {config.SCHEMA_NAME}.enqueue_email(
                    %s,  -- email_type
                    %s,  -- recipient_email
                    %s,  -- recipient_name
                    %s,  -- subject
                    %s,  -- body_html
                    %s,  -- body_text
                    %s,  -- booking_id (NULL for OTP emails)
                    %s,  -- template_context (JSON)
                    %s,  -- scheduled_for (NOW)
                    %s   -- priority (1 = high)
                ) AS email_id
            """

            result = await self.db.execute_one(
                query,
                (
                    "otp_verification",  # email_type
                    recipient_email,
                    recipient_name,
                    subject,
                    body_html,
                    body_text,
                    None,  # booking_id (not applicable for OTP)
                    json.dumps(template_context),  # template_context
                    datetime.now(timezone.utc),  # scheduled_for
                    1,  # priority (1 = highest)
                ),
            )

            if result and "email_id" in result:
                email_id = result["email_id"]
                logger.info(
                    f"OTP email enqueued successfully for {recipient_email} "
                    f"(email_id: {email_id})"
                )
                return True, "Verification email sent successfully!"
            else:
                logger.error("Failed to enqueue OTP email: no email_id returned")
                return False, "Failed to send verification email. Please try again."

        except Exception as e:
            logger.exception(f"Error in send_otp_email: {e}")
            return False, "Failed to send verification email."

    def _get_subject(self, language: str) -> str:
        """Get email subject (localized).

        Args:
            language: Email language (es, en).

        Returns:
            str: Localized subject line.
        """
        subjects = {
            "es": "Verifica tu correo electrónico - Demo Chat",
            "en": "Verify your email address - Demo Chat",
            "fr": "Vérifiez votre adresse e-mail - Demo Chat",
            "de": "Bestätigen Sie Ihre E-Mail-Adresse - Demo Chat",
            "it": "Verifica il tuo indirizzo email - Demo Chat",
            "pt": "Verifique seu endereço de e-mail - Demo Chat",
        }
        return subjects.get(language, subjects["es"])

    def _build_html_body(
        self,
        recipient_name: str,
        otp_code: str,
        hours_remaining: int,
        language: str,
    ) -> str:
        """Build HTML email body with OTP code.

        Args:
            recipient_name: User's full name.
            otp_code: 6-digit OTP code.
            hours_remaining: Hours until expiration.
            language: Email language.

        Returns:
            str: HTML email body.
        """
        # Localized content
        if language == "en":
            greeting = f"Hello {recipient_name},"
            intro = "Thank you for registering for Demo Chat!"
            code_label = "Your verification code is:"
            expiry_label = f"This code will expire in {hours_remaining} hours."
            instructions = (
                "Enter this code on the verification page to activate your account."
            )
            no_action = "If you didn't request this code, please ignore this email."
            footer = "Best regards,<br>The Demo Chat Team"
        else:  # Spanish (default)
            greeting = f"Hola {recipient_name},"
            intro = "¡Gracias por registrarte en Demo Chat!"
            code_label = "Tu código de verificación es:"
            expiry_label = f"Este código expirará en {hours_remaining} horas."
            instructions = (
                "Ingresa este código en la página de verificación para activar tu cuenta."
            )
            no_action = (
                "Si no solicitaste este código, por favor ignora este correo."
            )
            footer = "Saludos cordiales,<br>El equipo de Demo Chat"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; border-radius: 10px; padding: 30px; margin-bottom: 20px;">
                <h2 style="color: #2c3e50; margin-top: 0;">🔐 {code_label.replace(':', '')}</h2>

                <p>{greeting}</p>
                <p>{intro}</p>

                <div style="background-color: #ffffff; border: 2px solid #3498db; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                    <p style="margin: 0; font-size: 14px; color: #7f8c8d;">{code_label}</p>
                    <p style="font-size: 36px; font-weight: bold; color: #2c3e50; margin: 10px 0; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {otp_code}
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #e74c3c;">
                        ⏰ {expiry_label}
                    </p>
                </div>

                <p>{instructions}</p>

                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px; color: #856404;">
                        <strong>⚠️ Security Note:</strong><br>
                        {no_action}
                    </p>
                </div>

                <p style="margin-top: 30px; color: #7f8c8d;">
                    {footer}
                </p>
            </div>

            <div style="text-align: center; color: #95a5a6; font-size: 12px;">
                <p>This is an automated message, please do not reply.</p>
            </div>
        </body>
        </html>
        """
        return html

    def _build_text_body(
        self,
        recipient_name: str,
        otp_code: str,
        hours_remaining: int,
        language: str,
    ) -> str:
        """Build plain-text email body (fallback).

        Args:
            recipient_name: User's full name.
            otp_code: 6-digit OTP code.
            hours_remaining: Hours until expiration.
            language: Email language.

        Returns:
            str: Plain-text email body.
        """
        if language == "en":
            return f"""
Hello {recipient_name},

Thank you for registering for Demo Chat!

Your verification code is:

    {otp_code}

This code will expire in {hours_remaining} hours.

Enter this code on the verification page to activate your account.

If you didn't request this code, please ignore this email.

Best regards,
The Demo Chat Team

---
This is an automated message, please do not reply.
            """
        else:  # Spanish (default)
            return f"""
Hola {recipient_name},

¡Gracias por registrarte en Demo Chat!

Tu código de verificación es:

    {otp_code}

Este código expirará en {hours_remaining} horas.

Ingresa este código en la página de verificación para activar tu cuenta.

Si no solicitaste este código, por favor ignora este correo.

Saludos cordiales,
El equipo de Demo Chat

---
Este es un mensaje automático, por favor no respondas.
            """
