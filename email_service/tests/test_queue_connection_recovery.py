"""Test suite for email queue connection recovery and retry logic.

This module tests the automatic connection recovery mechanism for the email queue
that handles stale PostgreSQL connections.

Features tested:
- Connection validation (ping test)
- Automatic dead connection detection and replacement
- Automatic retry on OperationalError
- Metrics tracking of recovery operations

Author: Lab01-MCP Team
Date: 2025-11-04
"""

import pytest
from unittest.mock import MagicMock, patch
import psycopg2
from psycopg2 import OperationalError

# Test connection validation
def test_validate_connection_alive():
    """Test connection validation with a healthy connection."""
    from email_service.database.queue import _validate_connection

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = (1,)

    result = _validate_connection(mock_conn)
    assert result is True


def test_validate_connection_dead():
    """Test connection validation detects dead connection."""
    from email_service.database.queue import _validate_connection

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.execute.side_effect = OperationalError("server closed")

    result = _validate_connection(mock_conn)
    assert result is False


@patch("email_service.database.queue.EmailQueueManager._get_connection")
@patch("email_service.database.queue.EmailQueueManager.metrics")
def test_get_pending_emails_retries_on_error(mock_metrics, mock_get_conn):
    """Test get_pending_emails retries on connection error."""
    from email_service.database.queue import EmailQueueManager
    from email_service.config import EmailConfig

    # Setup
    config = EmailConfig()
    manager = EmailQueueManager(config)

    # Mock: first call fails, second succeeds
    call_count = [0]

    def side_effect():
        call_count[0] += 1
        cm = MagicMock()
        if call_count[0] == 1:
            cm.__enter__.side_effect = OperationalError("connection closed")
        else:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            cm.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.execute.return_value = None
            mock_cursor.fetchall.return_value = []
            mock_conn.commit.return_value = None
        cm.__exit__.return_value = None
        return cm

    mock_get_conn.side_effect = side_effect
    manager.metrics.increment_counter = MagicMock()
    manager.metrics.set_gauge = MagicMock()

    # Should retry and succeed
    result = manager.get_pending_emails()
    assert result == []
    assert mock_metrics.increment_counter.called


@patch("email_service.database.queue.EmailQueueManager._get_connection")
@patch("email_service.database.queue.EmailQueueManager.metrics")
def test_enqueue_email_retries_on_error(mock_metrics, mock_get_conn):
    """Test enqueue_email retries on connection error."""
    from email_service.database.queue import EmailQueueManager, EmailType
    from email_service.config import EmailConfig

    # Setup
    config = EmailConfig()
    manager = EmailQueueManager(config)

    # Mock: first call fails, second succeeds
    call_count = [0]

    def side_effect():
        call_count[0] += 1
        cm = MagicMock()
        if call_count[0] == 1:
            cm.__enter__.side_effect = OperationalError("connection closed")
        else:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            cm.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.execute.return_value = None
            mock_cursor.fetchone.return_value = {"enqueue_email": 123}
            mock_conn.commit.return_value = None
        cm.__exit__.return_value = None
        return cm

    mock_get_conn.side_effect = side_effect
    manager.metrics.increment_counter = MagicMock()
    manager.metrics.record_latency.return_value.__enter__ = MagicMock()
    manager.metrics.record_latency.return_value.__exit__ = MagicMock()

    # Should retry and succeed
    result = manager.enqueue_email(
        email_type=EmailType.BOOKING_CREATED,
        recipient_email="test@example.com",
        recipient_name="Test",
        subject="Test",
        body_html="<p>Test</p>"
    )
    assert result == 123
    assert mock_metrics.increment_counter.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
