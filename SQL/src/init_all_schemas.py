#!/usr/bin/env python3
"""Master initialization script - Creates all database schemas and objects.

This script executes all DDL initialization scripts in the correct dependency order:
1. Base products schema + extensions (init-db.py)
2. Agent memory system (init_memory_system.py)
3. Bookings schema (init_bookings.py)
4. Email queue system (init_email_queue.py)

Each script is executed independently with proper error handling and verification.
If a script fails, the process stops and reports the error.

Prerequisites:
    - PostgreSQL 14+ running
    - Environment variables configured in .env:
        - DATABASE_URL
        - SCHEMA_NAME (default: test)
    - pgvector extension installed

Usage:
    # Initialize all schemas
    python3 SQL/src/init_all_schemas.py

    # Initialize specific schemas only
    python3 SQL/src/init_all_schemas.py --only products,memory

    # Skip specific schemas
    python3 SQL/src/init_all_schemas.py --skip email

    # Dry run (show what would be executed)
    python3 SQL/src/init_all_schemas.py --dry-run

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("init_all_schemas")

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
SQL_SRC_DIR = Path(__file__).parent

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")


# ============================================================================
# SCHEMA INITIALIZATION DEFINITIONS
# ============================================================================

class SchemaInitializer:
    """Defines a database schema initialization step."""

    def __init__(
        self,
        name: str,
        script_path: Path,
        description: str,
        dependencies: list[str] | None = None,
    ):
        """Initialize schema definition.

        Args:
            name: Unique identifier for this schema
            script_path: Path to Python initialization script
            description: Human-readable description
            dependencies: List of schema names that must run before this one
        """
        self.name = name
        self.script_path = script_path
        self.description = description
        self.dependencies = dependencies or []
        self.execution_time: float = 0.0
        self.success: bool = False
        self.error: str | None = None

    def run(self, dry_run: bool = False) -> bool:
        """Execute the initialization script.

        Args:
            dry_run: If True, only log what would be executed

        Returns:
            True if successful, False otherwise
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would execute: python3 {self.script_path}")
            return True

        logger.info(f"Executing: {self.script_path.name}")
        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            self.execution_time = time.time() - start_time
            self.success = True

            # Log output
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        logger.debug(f"  {line}")

            logger.info(f"✅ {self.name} completed in {self.execution_time:.2f}s")
            return True

        except subprocess.CalledProcessError as exc:
            self.execution_time = time.time() - start_time
            self.success = False
            self.error = exc.stderr or str(exc)

            logger.error(f"❌ {self.name} failed after {self.execution_time:.2f}s")
            logger.error(f"Error output:\n{exc.stderr}")
            return False

        except Exception as exc:
            self.execution_time = time.time() - start_time
            self.success = False
            self.error = str(exc)

            logger.exception(f"❌ Unexpected error in {self.name}")
            return False


# ============================================================================
# SCHEMA DEFINITIONS (Dependency Order)
# ============================================================================

SCHEMAS = [
    SchemaInitializer(
        name="products",
        script_path=SQL_SRC_DIR / "init-db.py",
        description="Products schema with pgvector, fuzzy search, and pagination",
        dependencies=[],
    ),
    SchemaInitializer(
        name="memory",
        script_path=SQL_SRC_DIR / "init_memory_system.py",
        description="Agent memory system (sessions, messages, memory blocks)",
        dependencies=["products"],  # Requires schema to exist
    ),
    SchemaInitializer(
        name="bookings",
        script_path=SQL_SRC_DIR / "init_bookings.py",
        description="Bookings schema (appointments, business hours, services)",
        dependencies=["products"],  # Requires schema to exist
    ),
    SchemaInitializer(
        name="email",
        script_path=SQL_SRC_DIR / "init_email_queue.py",
        description="Email notification queue system",
        dependencies=["bookings"],  # Requires appointments table
    ),
]


# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

def verify_prerequisites() -> None:
    """Verify that all prerequisites are met.

    Raises:
        SystemExit: If prerequisites are not met
    """
    logger.info("Verifying prerequisites...")

    # Check DATABASE_URL
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not set in environment")
        logger.error("   Set it in .env file: DATABASE_URL=postgresql://user:pass@host:port/db")
        raise SystemExit(1)

    # Check database connection
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        logger.info(f"✅ Database connection successful")
    except psycopg2.Error as exc:
        logger.error(f"❌ Cannot connect to database: {exc}")
        raise SystemExit(1)

    # Check all script files exist
    missing_scripts = []
    for schema in SCHEMAS:
        if not schema.script_path.exists():
            missing_scripts.append(schema.script_path)

    if missing_scripts:
        logger.error("❌ Missing initialization scripts:")
        for script in missing_scripts:
            logger.error(f"   - {script}")
        raise SystemExit(1)

    logger.info(f"✅ All {len(SCHEMAS)} initialization scripts found")
    logger.info(f"✅ Using schema: {SCHEMA_NAME}")


def verify_schema_objects() -> dict[str, Any]:
    """Verify that all expected database objects were created.

    Returns:
        Dictionary with verification results
    """
    logger.info("")
    logger.info("Verifying database objects...")

    conn = None
    results = {
        "tables": [],
        "functions": [],
        "indexes": [],
        "extensions": [],
    }

    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # Verify extensions
            cur.execute(
                "SELECT extname FROM pg_extension WHERE extname IN "
                "('pg_trgm', 'unaccent', 'pgcrypto', 'vector', 'uuid-ossp')"
            )
            results["extensions"] = [row[0] for row in cur.fetchall()]

            # Verify tables
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY table_name
                """,
                (SCHEMA_NAME,),
            )
            results["tables"] = [row[0] for row in cur.fetchall()]

            # Verify functions
            cur.execute(
                """
                SELECT p.proname
                FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname = %s
                ORDER BY p.proname
                """,
                (SCHEMA_NAME,),
            )
            results["functions"] = [row[0] for row in cur.fetchall()]

            # Count indexes
            cur.execute(
                """
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE schemaname = %s
                """,
                (SCHEMA_NAME,),
            )
            results["indexes"] = cur.fetchone()[0]

    except Exception as exc:
        logger.warning(f"⚠️  Verification incomplete: {exc}")
        return results
    finally:
        if conn:
            conn.close()

    # Log results
    logger.info(f"✅ Extensions: {len(results['extensions'])} installed")
    for ext in results["extensions"]:
        logger.info(f"   - {ext}")

    logger.info(f"✅ Tables: {len(results['tables'])} created")
    for table in results["tables"]:
        logger.info(f"   - {SCHEMA_NAME}.{table}")

    logger.info(f"✅ Functions: {len(results['functions'])} created")
    logger.info(f"✅ Indexes: {results['indexes']} created")

    return results


# ============================================================================
# EXECUTION FUNCTIONS
# ============================================================================

def filter_schemas(
    schemas: list[SchemaInitializer],
    only: list[str] | None = None,
    skip: list[str] | None = None,
) -> list[SchemaInitializer]:
    """Filter schemas based on --only and --skip arguments.

    Args:
        schemas: List of all schema initializers
        only: If provided, only include these schemas
        skip: If provided, exclude these schemas

    Returns:
        Filtered list of schemas
    """
    if only:
        schemas = [s for s in schemas if s.name in only]

    if skip:
        schemas = [s for s in schemas if s.name not in skip]

    return schemas


def check_dependencies(schemas: list[SchemaInitializer]) -> bool:
    """Check if all dependencies are satisfied.

    Args:
        schemas: List of schemas to execute

    Returns:
        True if all dependencies are satisfied
    """
    schema_names = {s.name for s in schemas}

    for schema in schemas:
        for dep in schema.dependencies:
            if dep not in schema_names:
                logger.error(f"❌ Dependency error: {schema.name} requires {dep}")
                return False

    return True


def execute_schemas(
    schemas: list[SchemaInitializer], dry_run: bool = False
) -> tuple[int, int]:
    """Execute schema initialization scripts.

    Args:
        schemas: List of schemas to initialize
        dry_run: If True, only log what would be executed

    Returns:
        Tuple of (success_count, failure_count)
    """
    total = len(schemas)
    success_count = 0
    failure_count = 0

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"EXECUTING {total} SCHEMA INITIALIZATION SCRIPT(S)")
    logger.info("=" * 80)

    for i, schema in enumerate(schemas, 1):
        logger.info("")
        logger.info(f"[{i}/{total}] {schema.description}")
        logger.info("-" * 80)

        if schema.run(dry_run=dry_run):
            success_count += 1
        else:
            failure_count += 1
            logger.error("")
            logger.error("Stopping execution due to error")
            break

    return success_count, failure_count


def print_summary(
    schemas: list[SchemaInitializer],
    success_count: int,
    failure_count: int,
    total_time: float,
) -> None:
    """Print execution summary.

    Args:
        schemas: List of executed schemas
        success_count: Number of successful executions
        failure_count: Number of failed executions
        total_time: Total execution time in seconds
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 80)

    # Print individual results
    for schema in schemas:
        if schema.success:
            logger.info(f"✅ {schema.name:<15} {schema.description}")
            logger.info(f"   Execution time: {schema.execution_time:.2f}s")
        elif schema.error:
            logger.error(f"❌ {schema.name:<15} {schema.description}")
            logger.error(f"   Error: {schema.error[:100]}")
        else:
            logger.info(f"⏭️  {schema.name:<15} Skipped")

    # Print totals
    logger.info("")
    logger.info(f"Total schemas: {len(schemas)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"Total time: {total_time:.2f}s")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main() -> None:
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Initialize all database schemas for Lab01-MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize all schemas
  python3 SQL/src/init_all_schemas.py

  # Initialize only products and memory
  python3 SQL/src/init_all_schemas.py --only products,memory

  # Initialize all except email
  python3 SQL/src/init_all_schemas.py --skip email

  # Dry run (show what would be executed)
  python3 SQL/src/init_all_schemas.py --dry-run
        """,
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Comma-separated list of schemas to initialize (e.g., products,memory)",
    )
    parser.add_argument(
        "--skip",
        type=str,
        help="Comma-separated list of schemas to skip (e.g., email)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without actually running scripts",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print header
    logger.info("=" * 80)
    logger.info("LAB01-MCP DATABASE INITIALIZATION")
    logger.info("=" * 80)
    logger.info(f"Schema: {SCHEMA_NAME}")
    logger.info(f"Database: {DATABASE_URL.split('@')[1] if DATABASE_URL else 'NOT SET'}")

    if args.dry_run:
        logger.info("Mode: DRY RUN (no changes will be made)")

    start_time = time.time()

    try:
        # Step 1: Verify prerequisites
        verify_prerequisites()

        # Step 2: Filter schemas
        schemas = SCHEMAS.copy()
        if args.only:
            only_list = [s.strip() for s in args.only.split(",")]
            schemas = filter_schemas(schemas, only=only_list)
            logger.info(f"Filtered to: {', '.join(s.name for s in schemas)}")

        if args.skip:
            skip_list = [s.strip() for s in args.skip.split(",")]
            schemas = filter_schemas(schemas, skip=skip_list)
            logger.info(f"Skipping: {', '.join(skip_list)}")

        # Step 3: Check dependencies
        if not check_dependencies(schemas):
            raise SystemExit(1)

        # Step 4: Execute schemas
        success_count, failure_count = execute_schemas(schemas, dry_run=args.dry_run)

        # Step 5: Verify results (if not dry run)
        if not args.dry_run and failure_count == 0:
            verify_schema_objects()

        # Step 6: Print summary
        total_time = time.time() - start_time
        print_summary(schemas, success_count, failure_count, total_time)

        # Exit with appropriate code
        if failure_count > 0:
            logger.error("")
            logger.error("=" * 80)
            logger.error("❌ INITIALIZATION FAILED")
            logger.error("=" * 80)
            raise SystemExit(1)
        else:
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ ALL SCHEMAS INITIALIZED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Populate products: python3 SQL/src/populate-db.py")
            logger.info("  2. Seed booking data: python3 SQL/src/seed_booking_data.py")
            logger.info("  3. Start MCP server: cd mcp_server && python server.py")
            logger.info("")

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("Interrupted by user")
        raise SystemExit(130)

    except SystemExit:
        raise

    except Exception as exc:
        logger.exception(f"Unexpected error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
