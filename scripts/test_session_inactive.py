#!/usr/bin/env python3
"""Quick test script for session inactivity expiration.

Tests the 1-minute inactivity timeout by:
1. Creating a session
2. Verifying it's valid
3. Simulating 2 minutes of inactivity
4. Verifying session is expired
5. Demonstrating need for OTP re-authentication

Usage:
    python scripts/test_session_inactive.py

Author: Lab01-MCP Team
Created: 2025-11-18
"""

import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from demo_agent.config.settings import config
from demo_agent.db.models import DemoSession
from demo_agent.services.session_service import SessionService


def main():
    """Run inactivity timeout test."""
    print("\n" + "=" * 70)
    print("SESSION INACTIVITY TIMEOUT TEST (1 MINUTE)")
    print("=" * 70 + "\n")

    # Setup database
    engine = create_engine(config.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Step 1: Create session
        print("📌 STEP 1: Creating test session...")
        session = DemoSession(
            id=str(uuid4()),
            session_id=f"sess_test_{uuid4().hex[:8]}",
            user_id="javierjortiz82",
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        print(f"✅ Session created:")
        print(f"   Session ID: {session.session_id}")
        print(f"   User ID: {session.user_id}")
        print(f"   Created: {session.created_at.isoformat()}")
        print(f"   Last Activity: {session.last_activity_at.isoformat()}")

        # Step 2: Verify session is valid
        print("\n📌 STEP 2: Verifying session is valid...")
        is_expired = SessionService.is_session_expired(session)
        print(f"✅ Session expired? {is_expired}")
        print(f"   Status: {'❌ EXPIRED' if is_expired else '✅ VALID'}")

        if is_expired:
            print("❌ ERROR: Newly created session is already expired!")
            return

        # Step 3: Simulate inactivity (2 minutes)
        print("\n📌 STEP 3: Simulating 2 minutes of inactivity...")
        print(f"⏱️  Inactivity timeout configured: {config.SESSION_IDLE_TIMEOUT_MINUTES} minute(s)")
        print(f"⏱️  Simulating: 2 minutes without activity")

        # Set last_activity_at to 2 minutes ago
        two_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=2)
        session.last_activity_at = two_minutes_ago

        db.add(session)
        db.commit()
        db.refresh(session)

        print(f"\n✅ Activity timestamp updated:")
        print(f"   Current time: {datetime.now(timezone.utc).isoformat()}")
        print(f"   Last activity: {session.last_activity_at.isoformat()}")
        elapsed = (datetime.now(timezone.utc) - session.last_activity_at).total_seconds()
        print(f"   Elapsed time: {elapsed:.0f} seconds ({elapsed / 60:.2f} minutes)")

        # Step 4: Verify session is now expired
        print("\n📌 STEP 4: Checking if session has expired...")
        is_expired = SessionService.is_session_expired(session)
        reason = SessionService.get_expiration_reason(session)

        print(f"✅ Session expired? {is_expired}")
        print(f"   Status: {'❌ EXPIRED' if is_expired else '✅ VALID'}")

        if is_expired:
            print(f"   Reason: {reason}")
            print(f"\n   ⚠️  SESSION HAS EXPIRED!")
            print(f"   ⚠️  User must re-authenticate with OTP")
        else:
            print("❌ ERROR: Session should be expired but it's still valid!")
            return

        # Step 5: Invalidate session and require OTP
        print("\n📌 STEP 5: Invalidating expired session...")
        success = SessionService.invalidate_session(db, session)

        if success:
            print("✅ Session invalidated (deleted from database)")
            print(f"   Session ID {session.session_id} is no longer valid")
        else:
            print("❌ ERROR: Failed to invalidate session")
            return

        # Step 6: Show API response
        print("\n📌 STEP 6: API Response on next request...")
        print("┌─────────────────────────────────────────────────┐")
        print("│ POST /v1/demo                                   │")
        print("│ Headers: X-Session-ID: " + session.session_id + "        │")
        print("└─────────────────────────────────────────────────┘")
        print("\nResponse: 401 Unauthorized")
        print("```json")
        print("{")
        print('  "success": false,')
        print('  "error": "SessionExpired",')
        print('  "message": "Session expired (idle_timeout). Please log in again.",')
        print('  "reason": "idle_timeout",')
        print('  "action": "login",')
        print('  "hint": "Your session has expired. Please log in again with OTP verification."')
        print("}")
        print("```")

        # Step 7: Show re-authentication flow
        print("\n📌 STEP 7: User must re-authenticate with OTP...")
        print("┌─────────────────────────────────────────────────┐")
        print("│ 1. User receives 401 SessionExpired             │")
        print("│ 2. Frontend displays: 'Session expired'         │")
        print("│ 3. User enters email: javierjortiz82@gmail.com  │")
        print("│ 4. System sends new OTP code                    │")
        print("│ 5. User enters OTP                              │")
        print("│ 6. POST /v1/auth/verify-otp                     │")
        print("│ 7. ✅ NEW session created                        │")
        print("│ 8. User can use app again                       │")
        print("└─────────────────────────────────────────────────┘")

        # Summary
        print("\n" + "=" * 70)
        print("✅ TEST PASSED: Session inactivity timeout working correctly")
        print("=" * 70)
        print("\nSummary:")
        print(f"  • Session timeout: {config.SESSION_IDLE_TIMEOUT_MINUTES} minute(s)")
        print(f"  • After {config.SESSION_IDLE_TIMEOUT_MINUTES + 1} minute(s) inactivity → Session expires")
        print(f"  • User must enter OTP again to continue")
        print(f"  • Each request resets the inactivity timer")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
