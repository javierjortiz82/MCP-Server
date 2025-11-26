"""Demo Agent - FAQ-based AI assistant with token-bucket rate limiting.

Implements a simple FAQ-based agent that uses Gemini API for responses,
with PostgreSQL-backed token-bucket rate limiting and security hardening.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.1.0 (Async)
"""

from datetime import datetime, timezone

from agent.src.multi_agent.prompt_manager import PromptManager
from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.gemini_client import GeminiClient
from demo_agent.models.responses import TokenWarning
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.observability.structured_logger import get_structured_logger
from demo_agent.rate_limiter.token_bucket import TokenBucket
from demo_agent.security.captcha_handler import CaptchaHandler
from demo_agent.security.fingerprint import FingerprintAnalyzer
from demo_agent.security.ip_limiter import IPLimiter


class DemoAgent:
    """FAQ-based AI assistant with token-bucket rate limiting.

    Provides a limited-scope AI assistant that:
    - Restricts responses to FAQ content only (prevents hallucinations)
    - Tracks token consumption per user (5,000 tokens/day default)
    - Implements rate-limiting via token-bucket algorithm
    - Detects and blocks abuse via IP reputation, fingerprinting, CAPTCHA
    - Caches FAQs from Jinja2 templates for efficient delivery

    Attributes:
        gemini_client: GeminiClient instance for Gemini API calls
        token_bucket: TokenBucket instance for quota management
        prompt_manager: PromptManager instance for FAQ/prompt loading
        db: Database connection for audit logging
        fingerprint_analyzer: FingerprintAnalyzer for VPN/proxy detection
        ip_limiter: IPLimiter for IP-based rate limiting
        captcha_handler: CaptchaHandler for reCAPTCHA verification
    """

    def __init__(self):
        """Initialize DemoAgent with required components."""
        self.gemini_client = GeminiClient()
        self.token_bucket = TokenBucket()
        self.prompt_manager = PromptManager()
        self.db = get_db()
        self.fingerprint_analyzer = FingerprintAnalyzer()
        self.ip_limiter = IPLimiter()
        self.captcha_handler = CaptchaHandler()
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()
        self.logger.info("DemoAgent initialized with security modules and observability")

    async def process_query(
        self,
        user_input: str,
        user_key: str,
        language: str = "es",
        ip_address: str | None = None,
        user_agent: str | None = None,
        client_fingerprint: str | None = None,
        user_timezone: str | None = None,
    ) -> tuple[str | None, int, TokenWarning, str | None]:
        """Process a demo query with rate limiting and token tracking.

        Args:
            user_input: User's query/message
            user_key: User identifier (user_id | session_id | fingerprint)
            language: Language preference (es | en, default: es)
            ip_address: Client IP address
            user_agent: HTTP User-Agent header
            client_fingerprint: Device fingerprint hash
            user_timezone: IANA timezone identifier (e.g., 'America/Costa_Rica')

        Returns:
            Tuple[response_text, tokens_used, warning, error_message]:
            - response_text: Gemini-generated FAQ response (or None if error)
            - tokens_used: Total tokens consumed (0 if request rejected)
            - warning: TokenWarning object with percentage and message
            - error_message: Error string if request was blocked (or None)

        Process Flow:
        1. Check IP rate limiting
        2. Analyze fingerprint and compute abuse score
        3. Check if CAPTCHA is required
        4. Check token quota via TokenBucket
        5. Load FAQ context and build system prompt via PromptManager
        6. Call Gemini API to generate response
        7. Deduct tokens after response received
        8. Check if warning threshold exceeded
        9. Log request to audit trail
        10. Return response with tokens and warning info
        """
        try:
            self.logger.info(
                "Processing query",
                user_key=user_key,
                language=language,
                ip_address=ip_address
            )
            self.metrics.increment_counter("agent_queries_received")

            # Step 1: Check IP rate limiting
            if config.ENABLE_FINGERPRINT and ip_address:
                ip_allowed, requests_count = await self.ip_limiter.check_rate_limit(
                    ip_address
                )
                if not ip_allowed:
                    error_msg = (
                        "Rate limit exceeded para tu IP. "
                        f"Máximo {config.IP_RATE_LIMIT_REQUESTS} solicitudes por minuto."
                    )
                    self.logger.warning(
                        "IP rate limit exceeded",
                        ip_address=ip_address,
                        user_key=user_key
                    )
                    self.metrics.increment_counter("agent_queries_blocked_ip_limit")
                    await self._log_audit(
                        user_key=user_key,
                        ip_address=ip_address,
                        fingerprint=client_fingerprint,
                        user_agent=user_agent,
                        request_input=user_input,
                        is_blocked=True,
                        block_reason="rate_limit_ip",
                        action_taken="blocked",
                        abuse_score=0.8,
                    )
                    return (
                        None,
                        0,
                        TokenWarning(is_warning=True, message=error_msg),
                        error_msg,
                    )

            # Step 2: Analyze fingerprint and compute abuse score
            abuse_score = 0.0
            if config.ENABLE_FINGERPRINT:
                if not client_fingerprint and user_agent and ip_address:
                    client_fingerprint = self.fingerprint_analyzer.generate_fingerprint(
                        user_agent=user_agent,
                        ip_address=ip_address,
                    )

                # Get IP reputation
                ip_stats = await self.ip_limiter.get_ip_stats(ip_address or "")
                ip_reputation = self.ip_limiter.get_reputation_score(
                    ip_address or "", ip_stats
                )

                # Compute abuse score
                abuse_score = self.fingerprint_analyzer.compute_abuse_score(
                    user_agent=user_agent,
                    ip_address=ip_address,
                    ip_reputation=ip_reputation,
                )

                self.logger.debug(
                    "Abuse score computed",
                    user_key=user_key,
                    abuse_score=round(abuse_score, 2)
                )
                self.metrics.set_gauge(f"abuse_score_{user_key}", abuse_score)

                # Block if abuse score is critical (>0.9)
                if abuse_score > 0.9:
                    error_msg = (
                        "Actividad sospechosa detectada. "
                        "Tu cuenta ha sido bloqueada temporalmente."
                    )
                    self.logger.warning(
                        "Critical abuse score",
                        user_key=user_key,
                        abuse_score=round(abuse_score, 2)
                    )
                    self.metrics.increment_counter("agent_queries_blocked_suspicious")
                    await self._log_audit(
                        user_key=user_key,
                        ip_address=ip_address,
                        fingerprint=client_fingerprint,
                        user_agent=user_agent,
                        request_input=user_input,
                        is_blocked=True,
                        block_reason="suspicious_behavior",
                        action_taken="blocked",
                        abuse_score=abuse_score,
                    )
                    return (
                        None,
                        0,
                        TokenWarning(is_warning=True, message=error_msg),
                        error_msg,
                    )

            # Step 3: Check if CAPTCHA is required
            if (
                config.ENABLE_CAPTCHA
                and abuse_score > config.FINGERPRINT_SCORE_THRESHOLD
            ):
                error_msg = (
                    "Actividad sospechosa detectada. "
                    "Completa CAPTCHA para continuar."
                )
                self.logger.warning(
                    "CAPTCHA required",
                    user_key=user_key,
                    abuse_score=round(abuse_score, 2)
                )
                self.metrics.increment_counter("agent_queries_blocked_captcha_required")
                await self._log_audit(
                    user_key=user_key,
                    ip_address=ip_address,
                    fingerprint=client_fingerprint,
                    user_agent=user_agent,
                    request_input=user_input,
                    is_blocked=True,
                    block_reason="captcha_required",
                    action_taken="captcha_required",
                    abuse_score=abuse_score,
                )
                return (
                    None,
                    0,
                    TokenWarning(is_warning=True, message=error_msg),
                    error_msg,
                )

            # Step 4: Check quota before processing
            can_proceed, tokens_remaining = await self.token_bucket.check_quota(
                user_key, tokens_needed=100, user_timezone=user_timezone  # Estimate for pre-check
            )

            if not can_proceed:
                status = await self.token_bucket.get_quota_status(user_key)
                error_msg = (
                    f"Demo bloqueada. Límite de {config.DEMO_MAX_TOKENS:,} "
                    f"tokens alcanzado. Reintenta en {status['next_reset']}."
                )
                self.logger.warning(
                    "Query rejected - quota exceeded",
                    user_key=user_key
                )
                self.metrics.increment_counter("agent_queries_blocked_quota_exceeded")
                await self._log_audit(
                    user_key=user_key,
                    ip_address=ip_address,
                    fingerprint=client_fingerprint,
                    user_agent=user_agent,
                    request_input=user_input,
                    is_blocked=True,
                    block_reason="quota_exceeded",
                    action_taken="blocked",
                )
                return (
                    None,
                    0,
                    TokenWarning(is_warning=True, message=error_msg),
                    error_msg,
                )

            # Step 5: Load system prompt with FAQ context
            # Use tokens_remaining from quota check
            remaining_tokens = tokens_remaining
            system_prompt = self.prompt_manager.get_demo_prompt(
                remaining_tokens=remaining_tokens,
                user_lang=language,
            )

            # FIX 2.2: Token Refund Implementation
            # Pre-deduct estimated tokens and refund if API fails
            tokens_used = 0
            try:
                # Step 6: Call Gemini API
                self.logger.debug(
                    "Calling Gemini API",
                    user_key=user_key
                )
                response_text, tokens_used = await self.gemini_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_input,
                    temperature=config.TEMPERATURE,
                    max_output_tokens=config.MAX_OUTPUT_TOKENS,
                )
                self.metrics.increment_counter("agent_api_calls_successful")
                self.metrics.increment_counter("agent_tokens_generated", tokens_used)

                # Step 7: Deduct tokens after response received (accurate count)
                tokens_remaining = await self.token_bucket.deduct_tokens(
                    user_key, tokens_used=tokens_used
                )

            except Exception as api_error:
                # FIX 2.2: Refund tokens if API fails
                self.logger.warning(
                    "Gemini API failed - refunding tokens",
                    user_key=user_key,
                    tokens_used=tokens_used
                )
                self.metrics.increment_counter("agent_api_calls_failed")
                if tokens_used > 0:
                    tokens_remaining = await self.token_bucket.refund_tokens(
                        user_key, tokens_to_refund=tokens_used
                    )
                    self.logger.info(
                        "Tokens refunded after API failure",
                        user_key=user_key,
                        tokens_refunded=tokens_used,
                        tokens_remaining=tokens_remaining
                    )
                    self.metrics.increment_counter("agent_tokens_refunded", tokens_used)
                raise api_error

            # Step 5: Check warning threshold
            status = await self.token_bucket.get_quota_status(user_key)
            percentage_used = status["percentage_used"]
            is_warning = percentage_used >= config.DEMO_WARNING_THRESHOLD
            warning_msg = None

            if is_warning:
                # Generic English message with dynamic percentage
                # Frontend handles i18n translations based on is_warning flag
                warning_msg = f"You've consumed {percentage_used}% of your daily quota"
                self.metrics.increment_counter("agent_queries_with_warning")

            warning = TokenWarning(
                is_warning=is_warning,
                message=warning_msg,
                percentage_used=percentage_used,
            )

            # Step 9: Log request to audit trail
            await self._log_audit(
                user_key=user_key,
                ip_address=ip_address,
                fingerprint=client_fingerprint,
                user_agent=user_agent,
                request_input=user_input,
                response_length=len(response_text),
                tokens_used=tokens_used,
                is_blocked=False,
                action_taken="allowed",
                abuse_score=abuse_score,
            )

            self.logger.info(
                "Query processed successfully",
                user_key=user_key,
                tokens_used=tokens_used,
                tokens_remaining=tokens_remaining,
                warning=is_warning,
                percentage_used=percentage_used
            )
            self.metrics.increment_counter("agent_queries_successful")

            return response_text, tokens_used, warning, None

        except Exception:
            self.logger.exception("Error processing query", user_key=user_key)
            self.metrics.increment_counter("agent_queries_errors")
            await self._log_audit(
                user_key=user_key,
                ip_address=ip_address,
                fingerprint=client_fingerprint,
                user_agent=user_agent,
                request_input=user_input,
                is_blocked=True,
                block_reason="internal_error",
                action_taken="logged_only",
            )
            error_msg = "Error procesando tu solicitud. " "Por favor intenta más tarde."
            return None, 0, TokenWarning(is_warning=True, message=error_msg), error_msg

    async def _log_audit(
        self,
        user_key: str | None,
        ip_address: str | None,
        fingerprint: str | None,
        user_agent: str | None,
        request_input: str | None,
        response_length: int = 0,
        tokens_used: int = 0,
        is_blocked: bool = False,
        block_reason: str | None = None,
        action_taken: str = "allowed",
        abuse_score: float = 0.0,
    ) -> None:
        """Log request to audit trail for security analysis.

        Args:
            user_key: User identifier
            ip_address: Client IP address
            fingerprint: Client fingerprint
            user_agent: HTTP User-Agent
            request_input: User's query (truncated to 1000 chars)
            response_length: Response text length
            tokens_used: Tokens consumed
            is_blocked: Whether request was blocked
            block_reason: Reason for block (if applicable)
            action_taken: System action taken
            abuse_score: Abuse likelihood (0.0-1.0)
        """
        try:
            query = """
                INSERT INTO :SCHEMA_NAME.demo_audit_log
                (user_key, ip_address, client_fingerprint, request_input,
                 response_length, tokens_used, is_blocked, block_reason,
                 action_taken, user_agent, abuse_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Truncate request_input to 1000 chars
            truncated_input = request_input[:1000] if request_input else None

            await self.db.execute(
                query,
                (
                    user_key,
                    ip_address,
                    fingerprint,
                    truncated_input,
                    response_length,
                    tokens_used,
                    is_blocked,
                    block_reason,
                    action_taken,
                    user_agent,
                    abuse_score,
                ),
            )
            self.logger.debug(
                "Audit logged",
                user_key=user_key,
                action_taken=action_taken,
                is_blocked=is_blocked
            )
            self.metrics.increment_counter("audit_logs_recorded")

        except Exception:
            self.logger.error(
                "Failed to log audit",
                user_key=user_key
            )
            self.metrics.increment_counter("audit_log_errors")

    async def get_user_status(self, user_key: str) -> dict:
        """Get user's current quota status.

        Args:
            user_key: User identifier

        Returns:
            dict with quota status including tokens used, remaining, percentage
        """
        try:
            status = await self.token_bucket.get_quota_status(user_key)
            self.logger.debug(
                "User status retrieved",
                user_key=user_key,
                percentage_used=status.get("percentage_used", 0)
            )
            self.metrics.increment_counter("user_status_queries")
            return status
        except Exception:
            self.logger.exception("Error getting user status", user_key=user_key)
            self.metrics.increment_counter("user_status_errors")
            return {
                "tokens_used": 0,
                "tokens_remaining": config.DEMO_MAX_TOKENS,
                "percentage_used": 0,
                "requests_count": 0,
                "is_blocked": False,
                "blocked_until": None,
                "last_reset": datetime.now(timezone.utc).isoformat(),
                "next_reset": datetime.now(timezone.utc).isoformat(),
            }
