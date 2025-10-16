"""Template Renderer - Jinja2 email template engine.

Renders HTML and plain text email templates with dynamic context:
- Booking creation confirmations
- Booking cancellation notices
- Booking rescheduled notices
- Appointment reminders (24h, 1h)

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from email_service.config import settings
from email_service.models import EmailType


class TemplateRenderer:
    """Jinja2 template renderer for emails.

    Loads templates from email_service/templates/ and renders with context.
    Supports both HTML and plain text variants.
    """

    def __init__(self, template_dir: str | None = None) -> None:
        """Initialize template engine.

        Args:
            template_dir: Template directory path (uses settings if None).
        """
        self.template_dir = Path(template_dir or settings.TEMPLATE_DIR)
        self.env = self._init_jinja_env()

    def _init_jinja_env(self) -> Environment:
        """Initialize Jinja2 environment with custom settings.

        Returns:
            Configured Jinja2 environment.
        """
        # Create template directory if not exists
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Create Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,  # Auto-escape HTML for security
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters (if needed)
        env.filters["format_date"] = self._format_date
        env.filters["format_time"] = self._format_time

        return env

    def render_html(self, email_type: EmailType, context: dict[str, Any]) -> str:
        """Render HTML email template.

        Args:
            email_type: Type of email template to render.
            context: Template context data.

        Returns:
            Rendered HTML string.

        Raises:
            TemplateNotFound: If template file doesn't exist.
        """
        template_name = f"{email_type.value}.html"
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_text(self, email_type: EmailType, context: dict[str, Any]) -> str:
        """Render plain text email template.

        Args:
            email_type: Type of email template to render.
            context: Template context data.

        Returns:
            Rendered plain text string.

        Raises:
            TemplateNotFound: If template file doesn't exist.
        """
        template_name = f"{email_type.value}.txt"

        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            # Fallback: auto-generate plain text from context
            return self._generate_plain_text_fallback(email_type, context)

    def _generate_plain_text_fallback(
        self, email_type: EmailType, context: dict[str, Any]
    ) -> str:
        """Generate plain text fallback when .txt template doesn't exist.

        Args:
            email_type: Type of email.
            context: Template context data.

        Returns:
            Auto-generated plain text.
        """
        customer_name = context.get("customer_name", "Cliente")

        if email_type == EmailType.BOOKING_CREATED:
            return f"""
Hola {customer_name},

Tu cita ha sido confirmada:

Servicio: {context.get('service_type', 'N/A')}
Fecha: {context.get('booking_date', 'N/A')}
Hora: {context.get('booking_time', 'N/A')}
Duración: {context.get('duration_minutes', 'N/A')} minutos

Gracias por confiar en Lab01.

---
Lab01 - AI Sales Platform
            """.strip()

        elif email_type == EmailType.BOOKING_CANCELLED:
            return f"""
Hola {customer_name},

Tu cita ha sido cancelada:

Servicio: {context.get('service_type', 'N/A')}
Fecha: {context.get('booking_date', 'N/A')}
Hora: {context.get('booking_time', 'N/A')}

Gracias por confiar en Lab01.

---
Lab01 - AI Sales Platform
            """.strip()

        elif email_type == EmailType.BOOKING_RESCHEDULED:
            return f"""
Hola {customer_name},

Tu cita ha sido reagendada:

Servicio: {context.get('service_type', 'N/A')}
Fecha anterior: {context.get('old_date', 'N/A')} - {context.get('old_time', 'N/A')}
Nueva fecha: {context.get('new_date', 'N/A')} - {context.get('new_time', 'N/A')}

Gracias por confiar en Lab01.

---
Lab01 - AI Sales Platform
            """.strip()

        elif email_type in (EmailType.REMINDER_24H, EmailType.REMINDER_1H):
            hours_until = context.get("hours_until", "24")
            return f"""
Hola {customer_name},

Recordatorio: Tienes una cita en {hours_until} horas.

Servicio: {context.get('service_type', 'N/A')}
Fecha: {context.get('booking_date', 'N/A')}
Hora: {context.get('booking_time', 'N/A')}

Te esperamos!

---
Lab01 - AI Sales Platform
            """.strip()

        else:
            # Generic fallback
            return f"Hola {customer_name},\n\nGracias por confiar en Lab01.\n\n---\nLab01 - AI Sales Platform"

    def _format_date(self, date_str: str) -> str:
        """Jinja2 filter to format dates.

        Args:
            date_str: Date string (e.g., "2025-10-14").

        Returns:
            Formatted date (e.g., "14 de octubre de 2025").
        """
        # TODO: Implement proper date formatting if needed
        return date_str

    def _format_time(self, time_str: str) -> str:
        """Jinja2 filter to format times.

        Args:
            time_str: Time string (e.g., "14:30").

        Returns:
            Formatted time (e.g., "2:30 PM").
        """
        # TODO: Implement proper time formatting if needed
        return time_str

    def template_exists(self, email_type: EmailType, format_type: str = "html") -> bool:
        """Check if template file exists.

        Args:
            email_type: Type of email template.
            format_type: "html" or "text".

        Returns:
            True if template exists, False otherwise.
        """
        ext = "html" if format_type == "html" else "txt"
        template_path = self.template_dir / f"{email_type.value}.{ext}"
        return template_path.exists()
