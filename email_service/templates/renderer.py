"""Jinja2 template renderer for email service.

Renders HTML and plain-text email templates with dynamic context data.
Supports all email types (booking confirmations, reminders, cancellations, etc).

Author: Lab01-MCP Team
Created: 2025-10-18
Version: 1.0.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from email_service.config import EmailConfig
from email_service.core.exceptions import TemplateRenderError
from email_service.core.logger import get_logger
from email_service.models.email import EmailType
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger

logger = get_logger(__name__)


class TemplateRenderer:
    """Jinja2 template renderer for email templates.

    Loads and renders email templates with dynamic context data.
    Supports both HTML and plain-text variants for each email type.

    Attributes:
        template_dir: Path to directory containing Jinja2 templates.
        env: Configured Jinja2 environment.

    Example:
        renderer = TemplateRenderer()

        # Render HTML template
        html = renderer.render_html(
            email_type=EmailType.BOOKING_CREATED,
            context={
                "customer_name": "John",
                "service_type": "Consultation",
                "booking_date": "2025-10-20"
            }
        )

        # Render plaintext template
        text = renderer.render_text(EmailType.BOOKING_CREATED, context)
    """

    def __init__(self, template_dir: str | None = None) -> None:
        """Initialize template renderer.

        Args:
            template_dir: Path to templates directory (uses config if None).

        Raises:
            TemplateRenderError: If template directory cannot be created.
        """
        # Initialize observability (OPCIÓN 6)
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()

        self.template_dir = Path(template_dir or EmailConfig().TEMPLATE_DIR)

        try:
            self.env = self._init_jinja_env()
            logger.info(f"✅ Template renderer initialized: {self.template_dir}")
            self.logger.info("Template renderer initialized", template_dir=str(self.template_dir))
        except Exception as e:
            logger.error(f"❌ Failed to initialize template renderer: {e}")
            self.logger.exception("Template renderer initialization failed")
            raise TemplateRenderError(f"Failed to initialize Jinja2: {e}") from e

    def _init_jinja_env(self) -> Environment:
        """Initialize Jinja2 environment with custom settings.

        Returns:
            Configured Jinja2 environment with custom filters and security.

        Raises:
            TemplateRenderError: If environment initialization fails.
        """
        # Create template directory if it doesn't exist
        try:
            self.template_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise TemplateRenderError(
                f"Cannot create template directory {self.template_dir}: {e}"
            ) from e

        # Create Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,  # Auto-escape HTML for security
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        env.filters["format_date"] = self._format_date
        env.filters["format_time"] = self._format_time

        return env

    def render_html(self, email_type: EmailType, context: dict[str, Any]) -> str:
        """Render HTML email template.

        Args:
            email_type: Email type determining which template to load.
            context: Dictionary with template variables.

        Returns:
            Rendered HTML string.

        Raises:
            TemplateRenderError: If template not found or rendering fails.

        Example:
            html = renderer.render_html(
                EmailType.BOOKING_CREATED,
                {"customer_name": "John", "booking_date": "2025-10-20"}
            )
        """
        template_name = f"{email_type.value}.html"

        try:
            with self.metrics.record_latency("template_render", tags={"type": email_type.value, "format": "html"}):
                logger.debug(f"📄 Rendering HTML template: {template_name}")
                self.logger.debug("Rendering HTML template", email_type=email_type.value, template_name=template_name)

                template = self.env.get_template(template_name)
                rendered = template.render(**context)

                logger.debug(f"✅ HTML template rendered: {len(rendered)} bytes")
                self.logger.debug("HTML template rendered", email_type=email_type.value, size_bytes=len(rendered))
                self.metrics.increment_counter("templates_rendered_html")
                return rendered

        except TemplateNotFound:
            logger.error(f"❌ HTML template not found: {template_name}")
            self.logger.warning("HTML template not found", template_name=template_name)
            self.metrics.increment_counter("template_render_errors")
            raise TemplateRenderError(
                f"Template not found: {template_name}",
                template_name=template_name,
            ) from None

        except Exception as e:
            logger.error(f"❌ Failed to render HTML template: {e}")
            self.logger.exception("HTML template rendering failed", template_name=template_name)
            self.metrics.increment_counter("template_render_errors")
            raise TemplateRenderError(
                f"Failed to render {template_name}: {e}",
                template_name=template_name,
            ) from e

    def render_text(self, email_type: EmailType, context: dict[str, Any]) -> str:
        """Render plain-text email template.

        Attempts to load .txt template. If not found, generates a fallback
        plain-text version from context data.

        Args:
            email_type: Email type determining which template to load.
            context: Dictionary with template variables.

        Returns:
            Rendered plain-text string.

        Raises:
            TemplateRenderError: If rendering fails.

        Example:
            text = renderer.render_text(
                EmailType.BOOKING_CREATED,
                {"customer_name": "John", "booking_date": "2025-10-20"}
            )
        """
        template_name = f"{email_type.value}.txt"

        try:
            with self.metrics.record_latency("template_render", tags={"type": email_type.value, "format": "text"}):
                logger.debug(f"📄 Rendering text template: {template_name}")
                self.logger.debug("Rendering text template", email_type=email_type.value, template_name=template_name)

                template = self.env.get_template(template_name)
                rendered = template.render(**context)

                logger.debug(f"✅ Text template rendered: {len(rendered)} bytes")
                self.logger.debug("Text template rendered", email_type=email_type.value, size_bytes=len(rendered))
                self.metrics.increment_counter("templates_rendered_text")
                return rendered

        except TemplateNotFound:
            logger.debug(
                f"ℹ️ Text template not found: {template_name}, "
                "using auto-generated fallback"
            )
            self.logger.debug("Using fallback text template", email_type=email_type.value)
            fallback = self._generate_fallback_text(email_type, context)
            self.metrics.increment_counter("templates_rendered_fallback")
            return fallback

        except Exception as e:
            logger.error(f"❌ Failed to render text template: {e}")
            self.logger.exception("Text template rendering failed", template_name=template_name)
            self.metrics.increment_counter("template_render_errors")
            raise TemplateRenderError(
                f"Failed to render {template_name}: {e}",
                template_name=template_name,
            ) from e

    def _generate_fallback_text(
        self, email_type: EmailType, context: dict[str, Any]
    ) -> str:
        """Generate plain-text fallback when .txt template doesn't exist.

        Args:
            email_type: Type of email.
            context: Template context data.

        Returns:
            Auto-generated plain-text email body.
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
            return f"""
Hola {customer_name},

Gracias por confiar en Lab01.

---
Lab01 - AI Sales Platform
            """

    def _format_date(self, date_str: str) -> str:
        """Jinja2 filter to format dates (pass-through).

        Currently returns date string as-is. Dates should be formatted at
        database or template level using Jinja2 date filters or Python datetime.

        Args:
            date_str: Date string to format.

        Returns:
            Date string unchanged.

        Future enhancement:
            Could implement with datetime.strptime() + locale support if needed.
        """
        return date_str

    def _format_time(self, time_str: str) -> str:
        """Jinja2 filter to format times (pass-through).

        Currently returns time string as-is. Times should be formatted at
        database or template level using Jinja2 time filters or Python datetime.

        Args:
            time_str: Time string to format.

        Returns:
            Time string unchanged.

        Future enhancement:
            Could implement with datetime.strptime() + locale support if needed.
        """
        return time_str

    def template_exists(self, email_type: EmailType, format_type: str = "html") -> bool:
        """Check if template file exists for email type.

        Args:
            email_type: Email type to check.
            format_type: "html" or "text".

        Returns:
            True if template file exists, False otherwise.

        Example:
            if renderer.template_exists(EmailType.BOOKING_CREATED, "html"):
                print("Template found")
        """
        ext = "html" if format_type == "html" else "txt"
        template_path = self.template_dir / f"{email_type.value}.{ext}"
        exists = template_path.exists()
        logger.debug(
            f"{'✅' if exists else '❌'} Template check: "
            f"{template_path} ({'exists' if exists else 'not found'})"
        )
        self.logger.debug(
            "Template existence check",
            email_type=email_type.value,
            format_type=format_type,
            exists=exists
        )
        self.metrics.increment_counter("template_checks")
        return exists
