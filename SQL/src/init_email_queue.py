#!/usr/bin/env python3
"""Initialize Email Queue Schema.

Executes the create_email_queue.sql script to set up:
- email_queue table with status tracking
- Indexes for optimal worker performance
- SQL utility functions (enqueue, get_pending, update_status, retry, cleanup)
- Permissions for mcp_user

Prerequisites:
    - PostgreSQL running (via Docker or local)
    - Database 'mcp_db' exists
    - Schema 'test' exists
    - User 'mcp_user' exists

Usage:
    python3 SQL/src/init_email_queue.py

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()


def get_database_url() -> str:
    """Load database URL from environment.

    Returns:
        PostgreSQL connection string (DATABASE_URL).

    Raises:
        ValueError: If DATABASE_URL is not set.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Example: postgresql://user:password@host:port/database"
        )
    return database_url


def load_sql_script(schema_name: str = "test") -> str:
    """Load and substitute SQL script.

    Args:
        schema_name: PostgreSQL schema name (default: "test").

    Returns:
        SQL script with substituted schema name.
    """
    sql_file = Path(__file__).parent.parent / "scripts" / "create_email_queue.sql"

    if not sql_file.exists():
        raise FileNotFoundError(f"SQL script not found: {sql_file}")

    sql_content = sql_file.read_text(encoding="utf-8")

    # Substitute schema name placeholder
    sql_content = sql_content.replace("{SCHEMA_NAME}", schema_name)

    return sql_content


def execute_sql(sql: str, database_url: str) -> None:
    """Execute SQL script.

    Args:
        sql: SQL script to execute.
        database_url: PostgreSQL connection string.

    Raises:
        psycopg2.Error: If SQL execution fails.
    """
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
            print("✅ Email queue schema created successfully")
    finally:
        conn.close()


def verify_schema(database_url: str, schema_name: str = "test") -> None:
    """Verify email_queue table was created.

    Args:
        database_url: PostgreSQL connection string.
        schema_name: PostgreSQL schema name.

    Raises:
        RuntimeError: If table doesn't exist.
    """
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_name = 'email_queue'
                )
                """,
                (schema_name,),
            )
            exists = cur.fetchone()[0]

            if not exists:
                raise RuntimeError(
                    f"❌ Table {schema_name}.email_queue was not created"
                )

            print(f"✅ Verified: {schema_name}.email_queue exists")

            # Count functions created
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.routines
                WHERE routine_schema = %s
                AND routine_name IN (
                    'enqueue_email',
                    'get_pending_emails',
                    'update_email_status',
                    'retry_email',
                    'cleanup_old_emails'
                )
                """,
                (schema_name,),
            )
            func_count = cur.fetchone()[0]
            print(f"✅ Verified: {func_count}/5 SQL functions created")

    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    print("🚀 Initializing Email Queue Schema...")

    # Get configuration
    database_url = get_database_url()
    schema_name = os.getenv("SCHEMA_NAME", "test")

    # Extract database name for display
    db_name = database_url.split("/")[-1].split("?")[0]

    print(f"📊 Target database: {db_name}")
    print(f"📊 Target schema: {schema_name}")

    try:
        # Load SQL script
        print("📄 Loading SQL script...")
        sql = load_sql_script(schema_name)

        # Execute SQL
        print("⚙️  Executing SQL script...")
        execute_sql(sql, database_url)

        # Verify creation
        print("🔍 Verifying schema...")
        verify_schema(database_url, schema_name)

        print("\n✅ Email queue initialization complete!")
        print("\n💡 Next steps:")
        print("   1. Configure SMTP settings in .env")
        print("   2. Start email worker: docker-compose up email-worker")
        print("   3. Integrate enqueue_email() calls in bookings.py")

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
