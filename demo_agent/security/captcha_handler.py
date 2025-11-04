"""reCAPTCHA v3 verification handler.

Verifies reCAPTCHA v3 tokens and computes risk scores.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""


import requests

from demo_agent.config.settings import config
from demo_agent.logger import logger


class CaptchaHandler:
    """Handler for reCAPTCHA v3 verification.

    reCAPTCHA v3 provides risk scores (0.0-1.0) without user interaction:
    - 0.0: Likely bot
    - 0.5: Unknown
    - 1.0: Likely human

    Attributes:
        enabled: Whether CAPTCHA verification is enabled
        secret_key: Google reCAPTCHA v3 secret key
        verify_url: Google reCAPTCHA verification endpoint
        score_threshold: Minimum score to accept (default 0.5)
    """

    VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

    def __init__(self, score_threshold: float = 0.5):
        """Initialize CAPTCHA handler.

        Args:
            score_threshold: Minimum reCAPTCHA score to accept (default 0.5)
                - 0.0-0.3: Likely bot, require verification
                - 0.3-0.7: Uncertain, can require CAPTCHA
                - 0.7-1.0: Likely human, allow
        """
        self.enabled = config.ENABLE_CAPTCHA
        self.secret_key = (
            config.RECAPTCHA_SECRET_KEY
            if hasattr(config, "RECAPTCHA_SECRET_KEY")
            else None
        )
        self.score_threshold = score_threshold
        logger.info(
            f"CaptchaHandler initialized (enabled={self.enabled}, "
            f"threshold={score_threshold})"
        )

    async def verify_token(self, token: str, remote_ip: str | None = None) -> dict:
        """Verify reCAPTCHA v3 token with Google.

        Args:
            token: reCAPTCHA response token from client
            remote_ip: Client IP address (optional, for verification)

        Returns:
            dict with keys:
            - success: Whether token is valid
            - score: Risk score (0.0-1.0, higher = more likely human)
            - action: Expected action name
            - challenge_ts: When CAPTCHA was solved
            - hostname: Hostname where CAPTCHA was loaded
            - error_codes: List of error codes (if any)

        Example Response:
        ```json
        {
          "success": true,
          "score": 0.9,
          "action": "demo_query",
          "challenge_ts": "2025-10-31T12:30:45Z",
          "hostname": "example.com",
          "error_codes": []
        }
        ```

        Example Error Response:
        ```json
        {
          "success": false,
          "score": 0.0,
          "error_codes": ["invalid-input-response", "timeout-or-duplicate"]
        }
        ```
        """
        try:
            if not self.enabled:
                logger.debug("CAPTCHA verification disabled")
                return {
                    "success": True,
                    "score": 1.0,
                    "action": "demo_query",
                    "disabled": True,
                }

            if not self.secret_key:
                logger.warning("CAPTCHA secret key not configured")
                return {
                    "success": False,
                    "error_codes": ["missing-input-secret"],
                }

            # Prepare request data
            payload = {
                "secret": self.secret_key,
                "response": token,
            }
            if remote_ip:
                payload["remoteip"] = remote_ip

            logger.debug(f"Verifying reCAPTCHA token from {remote_ip}")

            # Call Google reCAPTCHA API
            response = requests.post(
                self.VERIFY_URL,
                data=payload,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()

            # Extract relevant fields
            return {
                "success": result.get("success", False),
                "score": result.get("score", 0.0),
                "action": result.get("action", "unknown"),
                "challenge_ts": result.get("challenge_ts"),
                "hostname": result.get("hostname"),
                "error_codes": result.get("error-codes", []),
            }

        except requests.RequestException as e:
            logger.exception(f"Error verifying reCAPTCHA token: {e}")
            return {
                "success": False,
                "error_codes": ["network-error"],
                "error_detail": str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error in verify_token: {e}")
            return {
                "success": False,
                "error_codes": ["internal-error"],
                "error_detail": str(e),
            }

    def evaluate_score(self, score: float) -> dict:
        """Evaluate reCAPTCHA score and recommend action.

        Args:
            score: reCAPTCHA risk score (0.0-1.0)

        Returns:
            dict with:
            - risk_level: "low", "medium", or "high"
            - recommendation: "allow", "captcha", or "block"
            - message: Human-readable description

        Risk Levels:
        - 0.0-0.3: High risk (likely bot)
        - 0.3-0.7: Medium risk (uncertain)
        - 0.7-1.0: Low risk (likely human)
        """
        if score >= 0.7:
            return {
                "risk_level": "low",
                "recommendation": "allow",
                "message": f"Likely human user (score: {score:.2f})",
            }
        elif score >= 0.3:
            return {
                "risk_level": "medium",
                "recommendation": "captcha",
                "message": f"Uncertain - may require CAPTCHA verification (score: {score:.2f})",
            }
        else:
            return {
                "risk_level": "high",
                "recommendation": "block",
                "message": f"Likely bot - request blocked (score: {score:.2f})",
            }

    async def should_require_captcha(
        self,
        abuse_score: float,
        captcha_score: float | None = None,
        previous_blocks: int = 0,
    ) -> tuple[bool, str]:
        """Determine if user should be required to complete CAPTCHA.

        Args:
            abuse_score: Fingerprint-based abuse score (0.0-1.0)
            captcha_score: Previous reCAPTCHA score (if available)
            previous_blocks: Number of previous blocks for this user

        Returns:
            Tuple[require_captcha, reason]:
            - require_captcha: True if CAPTCHA should be required
            - reason: Description of why CAPTCHA is required
        """
        try:
            # Always require if abuse score is high
            if abuse_score > 0.8:
                return True, "High abuse score detected"

            # Require if previous reCAPTCHA score was low
            if captcha_score is not None and captcha_score < 0.5:
                return True, "Previous CAPTCHA score was low"

            # Require if multiple previous blocks
            if previous_blocks >= 2:
                return True, "Multiple previous blocks detected"

            # Require if moderate abuse score and suspicious patterns
            if abuse_score > 0.6:
                return True, "Moderate abuse score with suspicious patterns"

            return False, "No CAPTCHA required"

        except Exception as e:
            logger.error(f"Error in should_require_captcha: {e}")
            # Fail safe: require CAPTCHA on error
            return True, f"Error evaluating CAPTCHA requirement: {str(e)}"

    def get_recaptcha_status(self) -> dict:
        """Get reCAPTCHA configuration status.

        Returns:
            dict with:
            - enabled: Whether CAPTCHA is enabled
            - configured: Whether secret key is configured
            - version: "v3" (implicit)
            - score_threshold: Configured threshold
        """
        return {
            "enabled": self.enabled,
            "configured": bool(self.secret_key),
            "version": "v3",
            "score_threshold": self.score_threshold,
            "status": (
                "ready"
                if (self.enabled and self.secret_key)
                else ("disabled" if not self.enabled else "misconfigured")
            ),
        }
