"""Setup test users for reCAPTCHA testing."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

sys.path.insert(0, str(Path(__file__).parent.parent))

from demo_agent.db.connection import get_db
from demo_agent.services.user_service import UserService
import asyncio


async def setup_test_users():
    """Create test users in database."""
    print("\n" + "="*80)
    print("📝 Setting up test users for reCAPTCHA testing")
    print("="*80 + "\n")

    try:
        # Get database connection
        db = get_db()
        print("✅ Database connected")

        # Initialize user service
        user_service = UserService()
        print("✅ User Service initialized\n")

        # Test users to create
        test_users = [
            {
                "email": "test123@example.com",
                "full_name": "Test User 123",
                "password_hash": "hashed_password_123"
            },
            {
                "email": "test456@example.com",
                "full_name": "Test User 456",
                "password_hash": "hashed_password_456"
            },
            {
                "email": "test789@example.com",
                "full_name": "Test User 789",
                "password_hash": "hashed_password_789"
            },
            {
                "email": "test1001@example.com",
                "full_name": "Test User 1001",
                "password_hash": "hashed_password_1001"
            },
            {
                "email": "test1002@example.com",
                "full_name": "Test User 1002",
                "password_hash": "hashed_password_1002"
            },
            {
                "email": "test1003@example.com",
                "full_name": "Test User 1003",
                "password_hash": "hashed_password_1003"
            }
        ]

        print("Creating test users:")
        print("-" * 80)

        for user_data in test_users:
            try:
                # Try to insert user directly into database
                query = """
                    INSERT INTO demo_users
                    (email, full_name, password_hash, is_email_verified, is_active, auth_provider)
                    VALUES (%s, %s, %s, true, true, 'email')
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id
                """
                result = db.execute(query, (
                    user_data["email"],
                    user_data["full_name"],
                    user_data["password_hash"]
                ))
                user_id = result[0][0] if result else "unknown"
                print(f"✅ Created user ID {user_id}: {user_data['email']}")

            except Exception as e:
                print(f"⚠️  User {user_data['email']} may already exist: {e}")

        # Retrieve user IDs
        print("\nRetrieving created/existing user IDs:")
        print("-" * 80)

        query = "SELECT id, email FROM demo_users WHERE email IN ({})".format(
            ','.join("'{}'".format(u['email']) for u in test_users)
        )
        results = db.fetchall(query)

        print("\n" + "="*80)
        print("✅ Test users setup completed")
        print("="*80)
        print("\nTest users available for reCAPTCHA testing:")
        if results:
            for user_id, email in results:
                print(f"  - ID: {user_id}, Email: {email}")
        print("\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_test_users())
