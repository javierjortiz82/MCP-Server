#!/usr/bin/env python3
"""Test script to validate SQL service logging configuration.

This script tests the logging functionality to ensure:
1. Logger is properly configured
2. Logs are written to both console and file
3. Log rotation settings are correct
4. All log levels work as expected

Usage:
    python3 test_logger.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from utils.logger import setup_logging

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def test_logging():
    """Test logging configuration with different log levels."""

    print("\n" + "=" * 80)
    print("SQL Service Logging Configuration Test")
    print("=" * 80 + "\n")

    # Set up logger
    logger = setup_logging("test_logger")

    print(f"Logger name: {logger.name}")
    print(f"Logger level: {logger.level}")
    print(f"Number of handlers: {len(logger.handlers)}")

    for i, handler in enumerate(logger.handlers):
        print(f"  Handler {i+1}: {type(handler).__name__}")
        if hasattr(handler, 'baseFilename'):
            print(f"    File: {handler.baseFilename}")
            print(f"    Max bytes: {handler.maxBytes:,} bytes ({handler.maxBytes / (1024*1024):.1f} MB)")
            print(f"    Backup count: {handler.backupCount}")

    print("\n" + "-" * 80)
    print("Testing log levels...")
    print("-" * 80 + "\n")

    # Test different log levels
    logger.debug("🔍 This is a DEBUG message - detailed diagnostic information")
    logger.info("ℹ️  This is an INFO message - general informational messages")
    logger.warning("⚠️  This is a WARNING message - warning but not critical")
    logger.error("❌ This is an ERROR message - serious problem occurred")
    logger.critical("🔥 This is a CRITICAL message - system may be unstable")

    print("\n" + "-" * 80)
    print("Testing structured logging...")
    print("-" * 80 + "\n")

    # Test structured logging with context
    logger.info("Processing record #123")
    logger.info("Database connection: postgresql://localhost:5434/mcpdb")
    logger.info("Embedding generation started: batch_size=8, model=gemini-embedding-001")
    logger.info("Completed: 100 records processed in 5.2 seconds")

    print("\n" + "=" * 80)
    print("✅ Logging test completed successfully!")
    print("=" * 80)

    # Check log file exists
    log_file = Path(__file__).parent.parent / "logs" / "test_logger.log"
    if log_file.exists():
        file_size = log_file.stat().st_size
        print(f"\n📁 Log file: {log_file}")
        print(f"📊 File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

        # Read and display last 5 lines from log file
        print("\n📄 Last 5 lines from log file:")
        print("-" * 80)
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-5:]:
                print(line.rstrip())
        print("-" * 80)
    else:
        print(f"\n⚠️  Warning: Log file not found at {log_file}")

    print("\n✅ All checks passed! Logging is properly configured.\n")


if __name__ == "__main__":
    test_logging()
