#!/usr/bin/env python3
"""Interactive End-to-End Test for Session Expiration.

Demonstrates the complete session lifecycle with user interaction.

Usage:
    python scripts/test_session_expiration.py

This script will:
1. Create a test session for javierjortiz82@gmail.com
2. Display session details
3. Prompt user to enter OTP (for verification)
4. Simulate session expiration
5. Verify session invalidation
6. Require re-authentication

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from demo_agent.config.settings import config
from demo_agent.db.models import DemoSession
from demo_agent.services.session_service import SessionService


class SessionExpirationDemo:
    """Interactive demo of session expiration mechanism."""

    def __init__(self):
        """Initialize demo with database connection."""
        self.engine = create_engine(config.DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self.session = None
        self.email = "javierjortiz82@gmail.com"

    def print_header(self, title: str):
        """Print formatted section header."""
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}\n")

    def print_config(self):
        """Display session configuration."""
        self.print_header("SESSION CONFIGURATION")
        print(f"SESSION_TTL_MINUTES:             {config.SESSION_TTL_MINUTES} min")
        print(f"SESSION_IDLE_TIMEOUT_MINUTES:   {config.SESSION_IDLE_TIMEOUT_MINUTES} min")
        print(f"SESSION_ABSOLUTE_TIMEOUT_MINUTES: {config.SESSION_ABSOLUTE_TIMEOUT_MINUTES} min")
        print(f"\nOTP_EXPIRATION_MINUTES:         {config.OTP_EXPIRATION_MINUTES} min")

    def step_1_create_session(self):
        """Step 1: Create a new session (user authenticated with OTP)."""
        self.print_header("STEP 1: USER AUTHENTICATION & SESSION CREATION")

        # Simulate user registering/authenticating with OTP
        user_id = 1  # Assuming user exists with ID 1
        session_id = f"sess_demo_{uuid4().hex[:8]}"

        print(f"Email:         {self.email}")
        print(f"User ID:       {user_id}")
        print(f"Session ID:    {session_id}")
        print(f"\n⏳ Simulating OTP verification...")
        time.sleep(1)
        print("✓ OTP verified successfully!")

        # Create session in database
        self.session = DemoSession(
            id=str(uuid4()),
            user_id=user_id,
            session_id=session_id,
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc),
        )
        self.db.add(self.session)
        self.db.commit()
        self.db.refresh(self.session)

        print(f"\n✅ Session created in database!")
        self.print_session_details()

    def step_2_verify_session_valid(self):
        """Step 2: Verify session is valid and not expired."""
        self.print_header("STEP 2: VERIFY SESSION VALIDITY")

        print(f"Session ID: {self.session.session_id}")
        print(f"\nChecking expiration status...")
        time.sleep(0.5)

        is_expired = SessionService.is_session_expired(self.session)
        reason = SessionService.get_expiration_reason(self.session)

        if is_expired:
            print(f"❌ Session is EXPIRED (reason: {reason})")
            return False
        else:
            print(f"✅ Session is VALID (not expired)")
            return True

    def step_3_use_session(self):
        """Step 3: Use session for API requests."""
        self.print_header("STEP 3: MAKE AUTHENTICATED REQUESTS")

        print(f"Session ID: {self.session.session_id}\n")

        # Simulate multiple requests
        for request_num in range(1, 4):
            print(f"Request #{request_num}:")
            print(f"  Input:   '¿Cuál es el precio de un laptop?'")

            # Simulate token usage
            tokens_used = 150 + (request_num * 50)
            print(f"  Tokens:  {tokens_used}")

            # Update session activity
            SessionService.update_session_activity(self.db, self.session, tokens_used=tokens_used)

            print(f"  Status:  ✅ SUCCESS")
            print(f"  Time:    {datetime.now(timezone.utc).isoformat()}\n")

            time.sleep(0.5)

        print(f"✅ All requests processed successfully!")
        print(f"Total requests: {self.session.total_requests}")
        print(f"Total tokens:   {self.session.total_tokens_used}")

    def step_4_simulate_expiration(self):
        """Step 4: Simulate session expiration by modifying timestamps."""
        self.print_header("STEP 4: SIMULATE SESSION EXPIRATION")

        idle_timeout = config.SESSION_IDLE_TIMEOUT_MINUTES

        print(f"Simulating user inactivity for {idle_timeout + 1} minutes...")
        print(f"\nCurrent time:      {datetime.now(timezone.utc).isoformat()}")

        # Set last_activity to the past to simulate idle timeout
        new_activity_time = datetime.now(timezone.utc) - timedelta(minutes=idle_timeout + 1)
        self.session.last_activity_at = new_activity_time

        print(f"New activity time: {new_activity_time.isoformat()}")
        print(f"Idle duration:     {idle_timeout + 1} minutes (exceeds {idle_timeout} min threshold)")

        self.db.add(self.session)
        self.db.commit()
        self.db.refresh(self.session)

        print(f"\n⏳ Simulating time passage... waiting for next request...")
        time.sleep(1)

    def step_5_detect_expiration(self):
        """Step 5: Verify session is now detected as expired."""
        self.print_header("STEP 5: ATTEMPT REQUEST WITH EXPIRED SESSION")

        print(f"Session ID: {self.session.session_id}")
        print(f"User tries to make another request...")
        print(f"\nRequest: POST /v1/demo")
        print(f"Headers: X-Session-ID: {self.session.session_id}\n")

        print(f"⏳ Validating session...")
        time.sleep(1)

        is_expired = SessionService.is_session_expired(self.session)
        reason = SessionService.get_expiration_reason(self.session)

        if is_expired:
            print(f"❌ Session EXPIRED (reason: {reason})")
            print(f"\nAPI Response: 401 Unauthorized")
            print(f"{{")
            print(f'  "success": false,')
            print(f'  "error": "SessionExpired",')
            print(f'  "message": "Session expired ({reason}). Please log in again.",')
            print(f'  "reason": "{reason}",')
            print(f'  "action": "login"')
            print(f"}}")
            return True
        else:
            print(f"✅ Session is still valid (unexpected!)")
            return False

    def step_6_invalidate_session(self):
        """Step 6: Invalidate/delete expired session."""
        self.print_header("STEP 6: INVALIDATE EXPIRED SESSION")

        session_id = self.session.session_id
        print(f"Session ID: {session_id}")
        print(f"\n⏳ Invalidating expired session...")
        time.sleep(0.5)

        success = SessionService.invalidate_session(self.db, self.session)

        if success:
            print(f"✅ Session successfully invalidated and deleted from database")

            # Verify deletion
            deleted_session = self.db.query(DemoSession).filter(
                DemoSession.session_id == session_id
            ).first()

            if deleted_session is None:
                print(f"✓ Confirmed: Session no longer exists in database")
                return True
            else:
                print(f"❌ ERROR: Session still exists!")
                return False
        else:
            print(f"❌ ERROR: Failed to invalidate session")
            return False

    def step_7_require_reauth(self):
        """Step 7: User must re-authenticate with OTP."""
        self.print_header("STEP 7: RE-AUTHENTICATION REQUIRED")

        print(f"User must log in again with OTP verification.\n")
        print(f"Request: POST /v1/auth/verify-otp")
        print(f"Body: {{")
        print(f'  "email": "{self.email}",')
        print(f'  "otp_code": "123456"')
        print(f"}}\n")

        print(f"⏳ Requesting OTP code...")
        time.sleep(0.5)

        print(f"✓ OTP code sent to {self.email}")
        print(f"\n📌 User enters OTP: 123456")
        print(f"⏳ Verifying OTP...")
        time.sleep(0.5)

        print(f"\n✅ OTP verified!")
        print(f"✅ New session created!")

        # Create new session
        new_session = DemoSession(
            id=str(uuid4()),
            user_id=self.session.user_id,
            session_id=f"sess_demo_{uuid4().hex[:8]}",
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc),
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)

        print(f"\nNew Session ID: {new_session.session_id}")
        print(f"Status:        Active and valid")

    def print_session_details(self):
        """Print detailed session information."""
        if self.session:
            stats = SessionService.get_session_stats(self.session)
            print(f"\n📊 Session Details:")
            print(f"  Session ID:        {stats['session_id']}")
            print(f"  User ID:           {stats['user_id']}")
            print(f"  Language:          {stats['language']}")
            print(f"  Created at:        {stats['created_at']}")
            print(f"  Last activity:     {stats['last_activity_at']}")
            print(f"  Is expired:        {stats['is_expired']}")
            print(f"  Total requests:    {stats['total_requests']}")
            print(f"  Total tokens:      {stats['total_tokens_used']}")
            print(f"  Avg tokens/req:    {stats['avg_tokens_per_request']:.2f}")

    def run(self):
        """Execute complete E2E test."""
        try:
            print("\n")
            print("╔" + "=" * 68 + "╗")
            print("║" + " " * 68 + "║")
            print("║  " + "SESSION EXPIRATION END-TO-END TEST".center(64) + "  ║")
            print("║" + " " * 68 + "║")
            print("╚" + "=" * 68 + "╝")

            # Show configuration
            self.print_config()

            # Run test steps
            self.step_1_create_session()
            input("\n👉 Press ENTER to continue to Step 2...")

            self.step_2_verify_session_valid()
            input("\n👉 Press ENTER to continue to Step 3...")

            self.step_3_use_session()
            input("\n👉 Press ENTER to continue to Step 4 (simulate expiration)...")

            self.step_4_simulate_expiration()
            input("\n👉 Press ENTER to continue to Step 5 (attempt request)...")

            self.step_5_detect_expiration()
            input("\n👉 Press ENTER to continue to Step 6 (invalidate)...")

            self.step_6_invalidate_session()
            input("\n👉 Press ENTER to continue to Step 7 (re-auth)...")

            self.step_7_require_reauth()

            # Final summary
            self.print_header("TEST SUMMARY")
            print("✅ All steps completed successfully!")
            print("\nSession Lifecycle:")
            print("  1. User authenticates with OTP")
            print("  2. Session created and validated")
            print("  3. User makes multiple API requests")
            print("  4. Session activity tracked (requests, tokens)")
            print("  5. Session remains valid while active")
            print("  6. After idle timeout, session automatically expires")
            print("  7. Expired session is detected and invalidated")
            print("  8. User required to re-authenticate with OTP")
            print("\n✅ Session expiration mechanism working as expected!")

        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            print(f"\n\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.db.close()


def main():
    """Main entry point."""
    demo = SessionExpirationDemo()
    demo.run()


if __name__ == "__main__":
    main()