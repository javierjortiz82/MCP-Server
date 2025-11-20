"""Dynamic Response Templates for Booking Agent.

This module provides a centralized, template-based message generation system
to replace hardcoded bilingual messages in booking_agent.py.

Architecture:
    - Messages are defined as Python dictionaries (easy to maintain)
    - Support for bilingual content (Spanish/English)
    - Variable substitution using Python string formatting
    - Type-safe message generation
    - Easy to extend with new languages

Usage:
    >>> from response_templates import ResponseTemplates
    >>> templates = ResponseTemplates()
    >>> msg = templates.get_welcome_message(
    ...     language="es",
    ...     full_name="Juan Pérez",
    ...     previous_login="2025-11-17 15:27:40"
    ... )

Author: Lab01-MCP Team
Created: 2025-11-19
Version: 1.0.0
"""

from datetime import datetime
from typing import Any


class ResponseTemplates:
    """Centralized template-based message generator for booking agent.

    This class replaces hardcoded bilingual messages with a structured,
    maintainable template system. All messages are defined in dictionaries
    with clear categorization and variable substitution.

    Attributes:
        templates (dict): Nested dictionary containing all message templates
            organized by category and language.

    Example:
        >>> templates = ResponseTemplates()
        >>> # Welcome message after OTP verification
        >>> msg = templates.get_welcome_message("es", "Juan", "2025-11-17...")
        >>> print(msg)
        ¡Excelente! ¡Bienvenido(a), Juan!
        Tu última conexión fue el 17 de November de 2025 a las 03:27 PM.
        ...
    """

    def __init__(self):
        """Initialize response templates."""
        self.templates = self._load_templates()

    def _load_templates(self) -> dict:
        """Load all message templates.

        Returns:
            dict: Nested dictionary with templates organized by:
                  category -> message_type -> language -> template_string

        Template Structure:
            {
                "auth": {
                    "request_email": {
                        "es": "Para comenzar, necesito tu correo...",
                        "en": "To get started, I need your email..."
                    },
                    ...
                },
                "welcome": { ... },
                "errors": { ... }
            }
        """
        return {
            # ================================================================
            # AUTHENTICATION MESSAGES
            # ================================================================
            "auth": {
                "request_email": {
                    "es": (
                        "Para comenzar con tu reserva, necesito verificar tu identidad.\n\n"
                        "¿Cuál es tu correo electrónico?"
                    ),
                    "en": (
                        "To start your booking, I need to verify your identity.\n\n"
                        "What's your email address?"
                    ),
                },
                "invalid_email": {
                    "es": (
                        "❌ El formato del correo electrónico no es válido.\n\n"
                        "Por favor, proporciona un email válido (ejemplo: usuario@dominio.com)"
                    ),
                    "en": (
                        "❌ The email format is not valid.\n\n"
                        "Please provide a valid email (example: user@domain.com)"
                    ),
                },
                "otp_sent": {
                    "es": (
                        "✅ Perfecto! He enviado un código de verificación de 6 dígitos a {email}.\n\n"
                        "Por favor, revisa tu bandeja de entrada y proporciona el código.\n"
                        "El código expira en 10 minutos."
                    ),
                    "en": (
                        "✅ Perfect! I've sent a 6-digit verification code to {email}.\n\n"
                        "Please check your inbox and provide the code.\n"
                        "The code expires in 10 minutes."
                    ),
                },
                "otp_error": {
                    "es": (
                        "❌ No pude enviar el código de verificación.\n\n"
                        "Por favor, verifica que el correo sea válido e intenta de nuevo."
                    ),
                    "en": (
                        "❌ I couldn't send the verification code.\n\n"
                        "Please verify that the email is valid and try again."
                    ),
                },
                "otp_invalid": {
                    "es": (
                        "❌ El código proporcionado no es válido.\n\n"
                        "Por favor, verifica el código en tu email e intenta de nuevo."
                    ),
                    "en": (
                        "❌ The code provided is not valid.\n\n"
                        "Please check the code in your email and try again."
                    ),
                },
                "otp_incorrect_with_retries": {
                    "es": (
                        "❌ Código incorrecto. Te quedan {attempts_remaining} intentos.\n\n"
                        "Por favor, verifica el código en tu email e inténtalo de nuevo."
                    ),
                    "en": (
                        "❌ Incorrect code. You have {attempts_remaining} attempts remaining.\n\n"
                        "Please check the code in your email and try again."
                    ),
                },
                "request_name_new_user": {
                    "es": (
                        "¡Excelente! Tu identidad ha sido verificada.\n\n"
                        "Para personalizar tu experiencia, ¿podrías decirme tu nombre?"
                    ),
                    "en": (
                        "Excellent! Your identity has been verified.\n\n"
                        "To personalize your experience, could you please tell me your name?"
                    ),
                },
                "otp_invalid_length": {
                    "es": (
                        "El código de verificación debe ser exactamente 6 dígitos.\n\n"
                        "Proporcionaste: {code} ({length} dígitos)\n\n"
                        "Por favor, revisa tu email y proporciona el código de 6 dígitos."
                    ),
                    "en": (
                        "The verification code must be exactly 6 digits.\n\n"
                        "You provided: {code} ({length} digits)\n\n"
                        "Please check your email and provide the 6-digit code."
                    ),
                },
                "email_not_in_memory": {
                    "es": "No encontré tu email en memoria. Por favor, comienza de nuevo con tu correo.",
                    "en": "I couldn't find your email in memory. Please start over with your email address.",
                },
                "verification_error": {
                    "es": "Error al verificar código: {error}",
                    "en": "Error verifying code: {error}",
                },
                "auth_continue_email": {
                    "es": (
                        "Gracias por tu mensaje.\n\n"
                        "Para autenticarte, por favor proporciona tu correo electrónico."
                    ),
                    "en": (
                        "Thank you for your message.\n\n"
                        "To authenticate, please provide your email address."
                    ),
                },
                "prompt_continue_email": {
                    "es": (
                        "Gracias por tu mensaje.\n\n"
                        "Para continuar, necesito verificar tu email. Por favor, proporciona tu correo electrónico."
                    ),
                    "en": (
                        "Thank you for your message.\n\n"
                        "To continue, I need to verify your email. Please provide your email address."
                    ),
                },
                "prompt_otp_sent_simple": {
                    "es": (
                        "¡Perfecto! He enviado un código de verificación a {email}.\n\n"
                        "Por favor, revisa tu email y proporciona el código de 6 dígitos."
                    ),
                    "en": (
                        "Perfect! I've sent a verification code to {email}.\n\n"
                        "Please check your email and provide the 6-digit code."
                    ),
                },
                "prompt_verifying_code": {
                    "es": (
                        "¡Excelente! Verificando tu código {code}...\n\n"
                        "Por favor espera mientras confirmo tu identidad."
                    ),
                    "en": (
                        "Great! Verifying your code {code}...\n\n"
                        "Please wait while I confirm your identity."
                    ),
                },
                "prompt_default_email": {
                    "es": "Para continuar, por favor proporciona tu correo electrónico.",
                    "en": "To continue, please provide your email address.",
                },
            },
            # ================================================================
            # WELCOME MESSAGES
            # ================================================================
            "welcome": {
                "authenticated_with_history": {
                    "es": (
                        "¡Excelente! ¡Bienvenido(a), {full_name}!\n\n"
                        "Tu última conexión fue el {last_login_date}.\n\n"
                        "¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?\n\n"
                        "📅 **Opciones de Reserva:**\n"
                        "• Crear una nueva cita\n"
                        "• Ver mis citas\n"
                        "• Reprogramar una cita\n"
                        "• Cancelar una cita\n"
                        "• Consultar horarios disponibles\n\n"
                        "¡Solo dime qué necesitas!"
                    ),
                    "en": (
                        "Excellent! Welcome, {full_name}!\n\n"
                        "Your last login was on {last_login_date}.\n\n"
                        "You're now authenticated! How can I help you today?\n\n"
                        "📅 **Booking Options:**\n"
                        "• Create a new appointment\n"
                        "• View my appointments\n"
                        "• Reschedule an appointment\n"
                        "• Cancel an appointment\n"
                        "• Check available time slots\n\n"
                        "Just tell me what you'd like to do!"
                    ),
                },
                "authenticated_no_history": {
                    "es": (
                        "¡Excelente! ¡Bienvenido(a), {full_name}!\n\n"
                        "¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?\n\n"
                        "📅 **Opciones de Reserva:**\n"
                        "• Crear una nueva cita\n"
                        "• Ver mis citas\n"
                        "• Reprogramar una cita\n"
                        "• Cancelar una cita\n"
                        "• Consultar horarios disponibles\n\n"
                        "¡Solo dime qué necesitas!"
                    ),
                    "en": (
                        "Excellent! Welcome, {full_name}!\n\n"
                        "You're now authenticated! How can I help you today?\n\n"
                        "📅 **Booking Options:**\n"
                        "• Create a new appointment\n"
                        "• View my appointments\n"
                        "• Reschedule an appointment\n"
                        "• Cancel an appointment\n"
                        "• Check available time slots\n\n"
                        "Just tell me what you'd like to do!"
                    ),
                },
                "authenticated_generic": {
                    "es": (
                        "¡Excelente! ¡Bienvenido(a)!\n\n"
                        "¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?\n\n"
                        "📅 **Opciones de Reserva:**\n"
                        "• Crear una nueva cita\n"
                        "• Ver mis citas\n"
                        "• Reprogramar una cita\n"
                        "• Cancelar una cita\n"
                        "• Consultar horarios disponibles\n\n"
                        "¡Solo dime qué necesitas!"
                    ),
                    "en": (
                        "Excellent! Welcome!\n\n"
                        "You're now authenticated! How can I help you today?\n\n"
                        "📅 **Booking Options:**\n"
                        "• Create a new appointment\n"
                        "• View my appointments\n"
                        "• Reschedule an appointment\n"
                        "• Cancel an appointment\n"
                        "• Check available time slots\n\n"
                        "Just tell me what you'd like to do!"
                    ),
                },
                "new_user_with_name": {
                    "es": (
                        "¡Gracias, {full_name}! Es un placer conocerte.\n\n"
                        "¡Ya estás autenticado! ¿En qué puedo ayudarte hoy?\n\n"
                        "📅 **Opciones de Reserva:**\n"
                        "• Crear una nueva cita\n"
                        "• Ver mis citas\n"
                        "• Reprogramar una cita\n"
                        "• Cancelar una cita\n"
                        "• Consultar horarios disponibles\n\n"
                        "¡Solo dime qué necesitas!"
                    ),
                    "en": (
                        "Thank you, {full_name}! It's a pleasure to meet you.\n\n"
                        "You're now authenticated! How can I help you today?\n\n"
                        "📅 **Booking Options:**\n"
                        "• Create a new appointment\n"
                        "• View my appointments\n"
                        "• Reschedule an appointment\n"
                        "• Cancel an appointment\n"
                        "• Check available time slots\n\n"
                        "Just tell me what you'd like to do!"
                    ),
                },
            },
            # ================================================================
            # SESSION MANAGEMENT MESSAGES
            # ================================================================
            "session": {
                "expired": {
                    "es": (
                        "⏰ Tu sesión ha expirado por inactividad.\n\n"
                        "Por seguridad, necesito verificar tu identidad nuevamente.\n\n"
                        "¿Cuál es tu correo electrónico?"
                    ),
                    "en": (
                        "⏰ Your session has expired due to inactivity.\n\n"
                        "For security, I need to verify your identity again.\n\n"
                        "What's your email address?"
                    ),
                },
                "not_authenticated_in_flow": {
                    "es": (
                        "🔐 Necesito verificar tu identidad antes de continuar.\n\n"
                        "¿Cuál es tu correo electrónico?"
                    ),
                    "en": (
                        "🔐 I need to verify your identity before continuing.\n\n"
                        "What's your email address?"
                    ),
                },
                "not_authenticated": {
                    "es": (
                        "🔐 Para proceder con tu reserva, necesito verificar tu identidad.\n\n"
                        "¿Cuál es tu correo electrónico?"
                    ),
                    "en": (
                        "🔐 To proceed with your booking, I need to verify your identity.\n\n"
                        "What's your email address?"
                    ),
                },
                "user_changed": {
                    "es": (
                        "🔄 Detecté que estás usando un correo diferente ({new_email}).\n\n"
                        "Por seguridad, necesito verificar tu identidad con el nuevo correo.\n\n"
                        "He enviado un código de verificación a {new_email}."
                    ),
                    "en": (
                        "🔄 I detected you're using a different email ({new_email}).\n\n"
                        "For security, I need to verify your identity with the new email.\n\n"
                        "I've sent a verification code to {new_email}."
                    ),
                },
            },
            # ================================================================
            # ERROR MESSAGES
            # ================================================================
            "errors": {
                "auth_check_failed": {
                    "es": (
                        "❌ Ocurrió un error al verificar tu autenticación.\n\n"
                        "Por favor, proporciona tu correo electrónico para continuar."
                    ),
                    "en": (
                        "❌ An error occurred while verifying your authentication.\n\n"
                        "Please provide your email address to continue."
                    ),
                },
                "verification_failed": {
                    "es": (
                        "❌ No pude verificar el código.\n\n"
                        "Por favor, intenta de nuevo o solicita un nuevo código."
                    ),
                    "en": (
                        "❌ I couldn't verify the code.\n\n"
                        "Please try again or request a new code."
                    ),
                },
            },
        }

    def _format_datetime(self, dt_str: str | None, language: str) -> str | None:
        """Format ISO datetime string to human-readable format.

        Args:
            dt_str: ISO format datetime string (e.g., "2025-11-17T15:27:40+00:00")
            language: Language code ("es" or "en")

        Returns:
            Formatted date string or None if dt_str is None

        Example:
            >>> _format_datetime("2025-11-17T15:27:40+00:00", "es")
            "17 de November de 2025 a las 03:27 PM"
        """
        if not dt_str:
            return None

        try:
            # Parse ISO datetime
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

            if language == "es":
                return dt.strftime("%d de %B de %Y a las %I:%M %p")
            else:
                return dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            return None

    def get_message(
        self,
        category: str,
        message_type: str,
        language: str = "es",
        **kwargs: Any,
    ) -> str:
        """Get a formatted message from templates.

        Args:
            category: Message category ("auth", "welcome", "session", "errors")
            message_type: Specific message type within category
            language: Language code ("es" or "en", default: "es")
            **kwargs: Variables to substitute in the message template

        Returns:
            Formatted message string

        Raises:
            KeyError: If category or message_type not found
            ValueError: If language not supported

        Example:
            >>> get_message("auth", "otp_sent", "es", email="user@example.com")
            "✅ Perfecto! He enviado un código..."
        """
        # Validate inputs
        if category not in self.templates:
            raise KeyError(f"Unknown category: {category}")

        if message_type not in self.templates[category]:
            raise KeyError(f"Unknown message_type: {message_type} in category: {category}")

        if language not in ["es", "en"]:
            raise ValueError(f"Unsupported language: {language}. Use 'es' or 'en'")

        # Get template
        template = self.templates[category][message_type][language]

        # Format with variables
        return template.format(**kwargs)

    # ================================================================
    # CONVENIENCE METHODS (Type-Safe, Easy to Use)
    # ================================================================

    def get_welcome_message(
        self,
        language: str,
        full_name: str | None = None,
        previous_login: str | None = None,
    ) -> str:
        """Get welcome message after successful authentication.

        Args:
            language: Language code ("es" or "en")
            full_name: User's full name (optional)
            previous_login: ISO timestamp of last login (optional)

        Returns:
            Formatted welcome message with booking options menu

        Example:
            >>> get_welcome_message("es", "Juan Pérez", "2025-11-17T15:27:40Z")
            "¡Excelente! ¡Bienvenido(a), Juan Pérez!\\n\\nTu última conexión..."
        """
        # Determine which template to use
        has_real_name = full_name and full_name not in [
            "Temporary User",
            "Usuario",
            "User",
            "",
        ]

        if has_real_name and previous_login:
            # User with name and login history
            formatted_date = self._format_datetime(previous_login, language)
            return self.get_message(
                "welcome",
                "authenticated_with_history",
                language,
                full_name=full_name,
                last_login_date=formatted_date,
            )
        elif has_real_name:
            # User with name but no login history
            return self.get_message(
                "welcome",
                "authenticated_no_history",
                language,
                full_name=full_name,
            )
        else:
            # Generic welcome (no name)
            return self.get_message("welcome", "authenticated_generic", language)

    def get_new_user_welcome(self, language: str, full_name: str) -> str:
        """Get welcome message for new user after name capture.

        Args:
            language: Language code ("es" or "en")
            full_name: User's provided name

        Returns:
            Formatted welcome message for new user
        """
        return self.get_message(
            "welcome",
            "new_user_with_name",
            language,
            full_name=full_name,
        )

    def get_session_expired_message(self, language: str) -> str:
        """Get session expired message.

        Args:
            language: Language code ("es" or "en")

        Returns:
            Session expired message
        """
        return self.get_message("session", "expired", language)

    def get_auth_required_message(
        self,
        language: str,
        in_auth_flow: bool = False,
    ) -> str:
        """Get authentication required message.

        Args:
            language: Language code ("es" or "en")
            in_auth_flow: Whether user is already in auth flow

        Returns:
            Authentication required message
        """
        msg_type = "not_authenticated_in_flow" if in_auth_flow else "not_authenticated"
        return self.get_message("session", msg_type, language)

    def get_otp_sent_message(self, language: str, email: str) -> str:
        """Get OTP sent confirmation message.

        Args:
            language: Language code ("es" or "en")
            email: Email address where OTP was sent

        Returns:
            OTP sent confirmation message
        """
        return self.get_message("auth", "otp_sent", language, email=email)

    def get_otp_error_message(self, language: str) -> str:
        """Get OTP sending error message.

        Args:
            language: Language code ("es" or "en")

        Returns:
            OTP error message
        """
        return self.get_message("auth", "otp_error", language)

    def get_otp_incorrect_message(
        self,
        language: str,
        attempts_remaining: int,
    ) -> str:
        """Get OTP incorrect message with retry count.

        Args:
            language: Language code ("es" or "en")
            attempts_remaining: Number of attempts remaining

        Returns:
            OTP incorrect message with retry information
        """
        return self.get_message(
            "auth",
            "otp_incorrect_with_retries",
            language,
            attempts_remaining=attempts_remaining,
        )

    def get_name_request_message(self, language: str) -> str:
        """Get name request message for new users.

        Args:
            language: Language code ("es" or "en")

        Returns:
            Name request message
        """
        return self.get_message("auth", "request_name_new_user", language)
