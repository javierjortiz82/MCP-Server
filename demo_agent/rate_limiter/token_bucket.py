"""Token bucket implementation for demo rate limiting.

Implements token-bucket algorithm using PostgreSQL for persistence.
Used to track and limit tokens per user per day.

FIX 3.2: Async database operations
- All db calls converted to async/await
- Non-blocking database I/O
- Part of PHASE 3 async migration

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.1.0 (Async)
"""

from datetime import datetime, timedelta, timezone

from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.logger import logger


class TokenBucket:
    """Token bucket for demo quota management.

    Implements token-bucket algorithm with PostgreSQL persistence:
    - Tracks tokens consumed per user per day
    - Auto-resets at UTC midnight
    - Blocks user for DEMO_COOLDOWN_HOURS after quota exhaustion
    - Prevents race conditions via atomic PostgreSQL UPDATE

    Implementation Details:
    - Uses demo_usage table for state persistence
    - Atomic PostgreSQL UPDATE for race-condition safety
    - Auto-cleanup of stale records (90+ days old)
    - Metrics: tokens_consumed, requests_count, is_blocked, blocked_until

    Example:
        >>> bucket = TokenBucket()
        >>> can_proceed, remaining = await bucket.check_quota("user_123", tokens_needed=250)
        >>> if can_proceed:
        ...     response = await call_gemini()
        ...     remaining = await bucket.deduct_tokens("user_123", tokens_used=response_tokens)
    """

    def __init__(self):
        """Initialize token bucket with database connection."""
        self.db = get_db()
        self.max_tokens = config.DEMO_MAX_TOKENS
        self.cooldown_hours = config.DEMO_COOLDOWN_HOURS
        logger.info(
            f"TokenBucket initialized (max_tokens={self.max_tokens}, "
            f"cooldown={self.cooldown_hours}h)"
        )

    async def check_quota(
        self, user_key: str, tokens_needed: int = 1
    ) -> tuple[bool, int]:
        """Check if user has sufficient quota.

        Args:
            user_key: User identifier (user_id | session_id | fingerprint)
            tokens_needed: Tokens required for this request

        Returns:
            Tuple[bool, int]: (can_proceed, tokens_remaining)
            - can_proceed: True if user has quota and not blocked
            - tokens_remaining: Tokens left after this request

        Logic:
        1. Query demo_usage by user_key
        2. If not exists: create new record with full quota
        3. If exists: check needs_reset() and auto-reset if needed
        4. Check is_blocked and if block has expired
        5. Calculate remaining tokens after tokens_needed
        """
        try:
            logger.debug(f"check_quota({user_key}, tokens_needed={tokens_needed})")

            # Query user's current quota state
            query = """
                SELECT id, user_key, tokens_consumed, requests_count,
                       last_reset, is_blocked, blocked_until
                FROM :SCHEMA_NAME.demo_usage
                WHERE user_key = %s
            """
            result = await self.db.execute_one(query, (user_key,))

            # Create new record if user not seen before
            if not result:
                insert_query = """
                    INSERT INTO :SCHEMA_NAME.demo_usage
                    (user_key, tokens_consumed, requests_count, is_blocked)
                    VALUES (%s, %s, %s, %s)
                """
                await self.db.execute(insert_query, (user_key, 0, 0, False))
                logger.debug(f"Created new quota record for {user_key}")
                return True, self.max_tokens - tokens_needed

            # Check if daily reset is needed (midnight UTC passed)
            last_reset = result["last_reset"]
            now = datetime.now(timezone.utc)
            if last_reset.date() < now.date():
                # Reset quota for new day
                reset_query = """
                    UPDATE :SCHEMA_NAME.demo_usage
                    SET tokens_consumed = 0,
                        requests_count = 0,
                        is_blocked = false,
                        blocked_until = NULL,
                        last_reset = %s
                    WHERE user_key = %s
                """
                await self.db.execute(reset_query, (now, user_key))
                logger.debug(f"Reset daily quota for {user_key}")
                return True, self.max_tokens - tokens_needed

            # Check if user is currently blocked
            if result["is_blocked"]:
                blocked_until = result["blocked_until"]
                if blocked_until and blocked_until > now:
                    # Block is still active
                    tokens_remaining = self.max_tokens - result["tokens_consumed"]
                    logger.warning(f"User {user_key} is blocked until {blocked_until}")
                    return False, tokens_remaining
                else:
                    # Block has expired, auto-unblock
                    unblock_query = """
                        UPDATE :SCHEMA_NAME.demo_usage
                        SET is_blocked = false, blocked_until = NULL
                        WHERE user_key = %s
                    """
                    await self.db.execute(unblock_query, (user_key,))
                    logger.info(f"Auto-unblocked user {user_key}")

            # Calculate remaining tokens after this request
            tokens_remaining = (
                self.max_tokens - result["tokens_consumed"] - tokens_needed
            )
            can_proceed = tokens_remaining >= 0

            logger.debug(
                f"Quota check: {user_key} -> "
                f"consumed={result['tokens_consumed']}, "
                f"remaining={max(0, tokens_remaining)}, "
                f"can_proceed={can_proceed}"
            )

            return can_proceed, max(0, tokens_remaining)

        except Exception as e:
            logger.exception(f"Error in check_quota: {e}")
            # Fail open: allow request but log error for review
            return True, self.max_tokens

    async def deduct_tokens(self, user_key: str, tokens_used: int) -> int:
        """Deduct tokens after request completion.

        Args:
            user_key: User identifier
            tokens_used: Actual tokens consumed by Gemini API

        Returns:
            int: Tokens remaining after deduction

        Logic:
        1. Atomic UPDATE: tokens_consumed += tokens_used, requests_count += 1
        2. Check if quota exceeded (tokens_consumed >= max_tokens)
        3. If exceeded: SET is_blocked = true, blocked_until = NOW() + cooldown_hours
        4. Return remaining tokens
        """
        try:
            logger.debug(f"deduct_tokens({user_key}, tokens_used={tokens_used})")

            # Atomic update: increment tokens and requests count
            query = """
                UPDATE :SCHEMA_NAME.demo_usage
                SET tokens_consumed = tokens_consumed + %s,
                    requests_count = requests_count + 1,
                    updated_at = %s
                WHERE user_key = %s
                RETURNING tokens_consumed, is_blocked
            """
            now = datetime.now(timezone.utc)
            result = await self.db.execute_one(query, (tokens_used, now, user_key))

            if not result:
                logger.error(f"User {user_key} not found after deduction")
                return self.max_tokens

            new_tokens_consumed = result["tokens_consumed"]
            tokens_remaining = max(0, self.max_tokens - new_tokens_consumed)

            # Check if quota exhausted
            if new_tokens_consumed >= self.max_tokens:
                blocked_until = now + timedelta(hours=self.cooldown_hours)
                block_query = """
                    UPDATE :SCHEMA_NAME.demo_usage
                    SET is_blocked = true,
                        blocked_until = %s
                    WHERE user_key = %s
                """
                await self.db.execute(block_query, (blocked_until, user_key))
                logger.warning(
                    f"User {user_key} quota exhausted. "
                    f"Blocked until {blocked_until}"
                )

            logger.debug(
                f"Tokens deducted: {user_key} -> "
                f"consumed={new_tokens_consumed}, "
                f"remaining={tokens_remaining}"
            )
            return tokens_remaining

        except Exception as e:
            logger.exception(f"Error in deduct_tokens: {e}")
            return self.max_tokens

    async def get_quota_status(self, user_key: str) -> dict:
        """Get user's current quota status.

        Args:
            user_key: User identifier

        Returns:
            dict with keys:
            - tokens_used: Tokens consumed today
            - tokens_remaining: Tokens left today
            - percentage_used: Usage percentage (0-100)
            - requests_count: Number of requests today
            - is_blocked: Whether user is currently blocked
            - blocked_until: Block expiration (ISO 8601) or None
            - last_reset: Last quota reset (ISO 8601)
            - next_reset: Next quota reset (ISO 8601 at UTC midnight)
        """
        try:
            logger.debug(f"get_quota_status({user_key})")

            query = """
                SELECT tokens_consumed, requests_count, is_blocked,
                       blocked_until, last_reset
                FROM :SCHEMA_NAME.demo_usage
                WHERE user_key = %s
            """
            result = await self.db.execute_one(query, (user_key,))

            # Default status if user not found
            if not result:
                now = datetime.now(timezone.utc)
                return {
                    "tokens_used": 0,
                    "tokens_remaining": self.max_tokens,
                    "percentage_used": 0,
                    "requests_count": 0,
                    "is_blocked": False,
                    "blocked_until": None,
                    "last_reset": now.isoformat(),
                    "next_reset": self._next_utc_midnight(),
                }

            tokens_consumed = result["tokens_consumed"]
            tokens_remaining = max(0, self.max_tokens - tokens_consumed)
            percentage_used = min(100, int((tokens_consumed / self.max_tokens) * 100))

            # Calculate next reset (next UTC midnight)
            next_reset = self._next_utc_midnight()

            return {
                "tokens_used": tokens_consumed,
                "tokens_remaining": tokens_remaining,
                "percentage_used": percentage_used,
                "requests_count": result["requests_count"],
                "is_blocked": result["is_blocked"],
                "blocked_until": (
                    result["blocked_until"].isoformat()
                    if result["blocked_until"]
                    else None
                ),
                "last_reset": result["last_reset"].isoformat(),
                "next_reset": next_reset,
            }

        except Exception as e:
            logger.exception(f"Error in get_quota_status: {e}")
            return {
                "tokens_used": 0,
                "tokens_remaining": self.max_tokens,
                "percentage_used": 0,
                "requests_count": 0,
                "is_blocked": False,
                "blocked_until": None,
                "last_reset": datetime.now(timezone.utc).isoformat(),
                "next_reset": self._next_utc_midnight(),
            }

    async def refund_tokens(self, user_key: str, tokens_to_refund: int) -> int:
        """Refund tokens to user (for failed API calls).

        Args:
            user_key: User identifier
            tokens_to_refund: Number of tokens to refund

        Returns:
            int: Tokens remaining after refund

        Logic:
        1. Atomic UPDATE: tokens_consumed -= tokens_to_refund
        2. Check if user was blocked due to quota
        3. If blocked: unblock automatically (they now have tokens again)
        4. Return remaining tokens

        Security:
            - Tokens cannot go negative (minimum 0)
            - Validates tokens_to_refund > 0
            - Logs all refunds for audit trail
            - Atomic operation prevents race conditions

        Use Case:
            When Gemini API call fails after tokens deducted:
            - API returns error before generating response
            - Tokens were already deducted via deduct_tokens()
            - Call refund_tokens() to reverse the deduction
            - User is not penalized for infrastructure errors

        Example:
            # User makes request, tokens deducted
            tokens_used = 250
            remaining = await bucket.deduct_tokens("user_123", tokens_used)

            # API call fails before response
            try:
                response = await gemini_client.generate_response(...)
            except Exception:
                # Refund the tokens
                remaining = await bucket.refund_tokens("user_123", tokens_used)
        """
        try:
            if tokens_to_refund <= 0:
                logger.warning(
                    f"Invalid refund amount for {user_key}: {tokens_to_refund}"
                )
                return self.max_tokens

            logger.debug(f"refund_tokens({user_key}, tokens_to_refund={tokens_to_refund})")

            # Atomic update: refund tokens
            query = """
                UPDATE :SCHEMA_NAME.demo_usage
                SET tokens_consumed = MAX(0, tokens_consumed - %s),
                    updated_at = %s
                WHERE user_key = %s
                RETURNING tokens_consumed, is_blocked
            """
            now = datetime.now(timezone.utc)
            result = await self.db.execute_one(query, (tokens_to_refund, now, user_key))

            if not result:
                logger.error(f"User {user_key} not found after refund")
                return self.max_tokens

            new_tokens_consumed = result["tokens_consumed"]
            tokens_remaining = max(0, self.max_tokens - new_tokens_consumed)

            # Check if user was blocked and now has tokens again
            if result["is_blocked"] and new_tokens_consumed < self.max_tokens:
                logger.info(
                    f"User {user_key} auto-unblocking after refund "
                    f"(tokens_consumed={new_tokens_consumed})"
                )
                unblock_query = """
                    UPDATE :SCHEMA_NAME.demo_usage
                    SET is_blocked = false,
                        blocked_until = NULL,
                        updated_at = %s
                    WHERE user_key = %s
                """
                await self.db.execute(unblock_query, (now, user_key))

            logger.warning(
                f"Tokens refunded: {user_key} -> "
                f"refunded={tokens_to_refund}, "
                f"consumed={new_tokens_consumed}, "
                f"remaining={tokens_remaining}"
            )

            return tokens_remaining

        except Exception as e:
            logger.exception(f"Error in refund_tokens: {e}")
            return self.max_tokens

    async def unblock_user(self, user_key: str) -> bool:
        """Manually unblock user (admin operation).

        Args:
            user_key: User identifier

        Returns:
            bool: True if unblock was successful

        Logic:
        - UPDATE demo_usage SET is_blocked = false, blocked_until = NULL
        - Log unblock action for audit trail
        """
        try:
            logger.debug(f"unblock_user({user_key})")

            query = """
                UPDATE :SCHEMA_NAME.demo_usage
                SET is_blocked = false,
                    blocked_until = NULL,
                    updated_at = %s
                WHERE user_key = %s
            """
            now = datetime.now(timezone.utc)
            await self.db.execute(query, (now, user_key))
            logger.warning(f"Admin unblocked user: {user_key}")
            return True

        except Exception as e:
            logger.exception(f"Error in unblock_user: {e}")
            return False

    @staticmethod
    def _next_utc_midnight() -> str:
        """Calculate next UTC midnight timestamp.

        Returns:
            ISO 8601 formatted string of next UTC midnight
        """
        now = datetime.now(timezone.utc)
        # Next midnight is start of tomorrow
        next_midnight = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        return next_midnight.isoformat()
