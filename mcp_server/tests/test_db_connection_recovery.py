"""Test suite for database connection recovery and retry logic.

This module tests the automatic connection recovery mechanism that handles
stale connections in the pool and provides automatic retry on connection errors.

Features tested:
- Connection validation (ping test)
- Automatic dead connection detection and replacement
- Automatic retry on OperationalError
- Metrics tracking of recovery operations
- Graceful degradation when recovery exhausted

Author: Lab01-MCP Team
Date: 2025-11-04
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import psycopg2
from psycopg2 import OperationalError

# Import database module
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils.db as db


class TestConnectionValidation:
    """Test suite for connection validation functionality."""

    def test_validate_connection_alive(self):
        """Test validation passes for healthy connection."""
        # Create mock connection that responds to ping
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = (1,)

        # Validate should return True
        result = db._validate_connection(mock_conn)
        assert result is True

    def test_validate_connection_dead_operational_error(self):
        """Test validation fails when connection raises OperationalError."""
        # Create mock connection that raises OperationalError
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = OperationalError(
            "server closed the connection unexpectedly"
        )

        # Validate should return False
        result = db._validate_connection(mock_conn)
        assert result is False

    def test_validate_connection_dead_interface_error(self):
        """Test validation fails when connection raises InterfaceError."""
        # Create mock connection that raises InterfaceError
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.InterfaceError(
            "connection already closed"
        )

        # Validate should return False
        result = db._validate_connection(mock_conn)
        assert result is False


class TestConnectionRetry:
    """Test suite for automatic retry logic on connection errors."""

    @patch("utils.db.get_conn")
    @patch("utils.db.metrics")
    @patch("utils.db.structured_logger")
    def test_fetchone_retries_on_operational_error(
        self, mock_logger, mock_metrics, mock_get_conn
    ):
        """Test fetchone retries when OperationalError occurs."""
        # Setup: First call fails, second succeeds
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        # Create side_effect to fail first, succeed second
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cm = MagicMock()
            if call_count[0] == 1:
                # First call: raise OperationalError
                cm.__enter__.side_effect = OperationalError(
                    "server closed the connection"
                )
                cm.__exit__.return_value = None
            else:
                # Second call: succeed
                cm.__enter__.return_value = mock_conn
                cm.__exit__.return_value = None
            return cm

        mock_get_conn.side_effect = side_effect

        # Mock cursor operations for successful second call
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = {"id": 1, "name": "test"}

        # Setup metrics mock
        mock_metrics.record_latency.return_value.__enter__ = MagicMock()
        mock_metrics.record_latency.return_value.__exit__ = MagicMock()

        # Call fetchone - should retry and succeed
        result = db.fetchone("SELECT * FROM test")

        # Verify retry was attempted
        assert mock_metrics.increment_counter.called
        # Check for retry metric
        retry_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if "db_connection_retry" in str(call)
        ]
        assert len(retry_calls) > 0

    @patch("utils.db.get_conn")
    @patch("utils.db.metrics")
    @patch("utils.db.structured_logger")
    def test_fetchone_exhausts_retries(
        self, mock_logger, mock_metrics, mock_get_conn
    ):
        """Test fetchone fails after retries exhausted."""
        # Setup: All calls fail with OperationalError
        def side_effect(*args, **kwargs):
            cm = MagicMock()
            cm.__enter__.side_effect = OperationalError(
                "server closed the connection"
            )
            cm.__exit__.return_value = None
            return cm

        mock_get_conn.side_effect = side_effect

        # Setup metrics mock
        mock_metrics.record_latency.return_value.__enter__ = MagicMock()
        mock_metrics.record_latency.return_value.__exit__ = MagicMock()

        # Call fetchone - should raise after retries exhausted
        with pytest.raises(OperationalError):
            db.fetchone("SELECT * FROM test")

        # Verify retry exhaustion was tracked
        exhausted_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if "retry_exhausted" in str(call)
        ]
        assert len(exhausted_calls) > 0

    @patch("utils.db.get_conn")
    @patch("utils.db.metrics")
    @patch("utils.db.structured_logger")
    def test_fetchall_retries_on_operational_error(
        self, mock_logger, mock_metrics, mock_get_conn
    ):
        """Test fetchall retries when OperationalError occurs."""
        # Setup: First call fails, second succeeds
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cm = MagicMock()
            if call_count[0] == 1:
                # First call: raise OperationalError
                cm.__enter__.side_effect = OperationalError(
                    "server closed the connection"
                )
                cm.__exit__.return_value = None
            else:
                # Second call: succeed
                mock_cursor = MagicMock()
                mock_conn = MagicMock()
                cm.__enter__.return_value = mock_conn
                cm.__exit__.return_value = None
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_conn.cursor.return_value.__exit__.return_value = None
                mock_cursor.execute.return_value = None
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "name": "test1"},
                    {"id": 2, "name": "test2"},
                ]
            return cm

        mock_get_conn.side_effect = side_effect

        # Setup metrics mock
        mock_metrics.record_latency.return_value.__enter__ = MagicMock()
        mock_metrics.record_latency.return_value.__exit__ = MagicMock()

        # Call fetchall - should retry and succeed
        result = db.fetchall("SELECT * FROM test")

        # Verify retry was attempted
        assert mock_metrics.increment_counter.called

    @patch("utils.db.get_conn")
    @patch("utils.db.metrics")
    @patch("utils.db.structured_logger")
    def test_execute_retries_on_operational_error(
        self, mock_logger, mock_metrics, mock_get_conn
    ):
        """Test execute retries when OperationalError occurs."""
        # Setup: First call fails, second succeeds
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            cm = MagicMock()
            if call_count[0] == 1:
                # First call: raise OperationalError
                cm.__enter__.side_effect = OperationalError(
                    "server closed the connection"
                )
                cm.__exit__.return_value = None
            else:
                # Second call: succeed
                mock_cursor = MagicMock()
                mock_conn = MagicMock()
                cm.__enter__.return_value = mock_conn
                cm.__exit__.return_value = None
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
                mock_conn.cursor.return_value.__exit__.return_value = None
                mock_cursor.execute.return_value = None
                mock_conn.commit.return_value = None
            return cm

        mock_get_conn.side_effect = side_effect

        # Setup metrics mock
        mock_metrics.record_latency.return_value.__enter__ = MagicMock()
        mock_metrics.record_latency.return_value.__exit__ = MagicMock()

        # Call execute - should retry and succeed
        db.execute("UPDATE test SET name = %s", ("new_name",))

        # Verify retry was attempted
        assert mock_metrics.increment_counter.called


class TestDeadConnectionReplacement:
    """Test suite for automatic dead connection detection and replacement."""

    @patch("utils.db._pool")
    @patch("utils.db._validate_connection")
    @patch("utils.db.metrics")
    @patch("utils.db.structured_logger")
    def test_get_conn_replaces_dead_connection(
        self, mock_logger, mock_metrics, mock_validate, mock_pool
    ):
        """Test get_conn replaces dead connections automatically."""
        # Setup: Validation fails, then succeeds for new connection
        mock_validate.side_effect = [False, True]

        # Setup pool mocks
        mock_dead_conn = MagicMock()
        mock_fresh_conn = MagicMock()
        mock_pool.getconn.side_effect = [mock_dead_conn, mock_fresh_conn]
        mock_pool.putconn = MagicMock()

        # Use context manager
        with db.get_conn() as conn:
            # Should get the fresh connection (second one)
            assert conn == mock_fresh_conn

        # Verify dead connection was returned to pool as closed
        mock_pool.putconn.assert_any_call(mock_dead_conn, close=True)
        # Verify fresh connection was returned normally
        mock_pool.putconn.assert_any_call(mock_fresh_conn)

        # Verify dead connection detection was metrics
        assert mock_metrics.increment_counter.called
        dead_detected_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if "db_connection_dead_detected" in str(call)
        ]
        assert len(dead_detected_calls) > 0

    @patch("utils.db._pool")
    @patch("utils.db._validate_connection")
    @patch("utils.db.structured_logger")
    def test_get_conn_handles_close_error_gracefully(
        self, mock_logger, mock_validate, mock_pool
    ):
        """Test get_conn handles errors during connection close gracefully."""
        # Setup: Validation fails, close raises error
        mock_validate.return_value = False

        mock_dead_conn = MagicMock()
        mock_dead_conn.close.side_effect = Exception("Already closed")
        mock_fresh_conn = MagicMock()
        mock_pool.getconn.side_effect = [mock_dead_conn, mock_fresh_conn]
        mock_pool.putconn = MagicMock()

        # Use context manager - should not raise even though close() failed
        with db.get_conn() as conn:
            assert conn == mock_fresh_conn

        # Should still attempt to return dead connection
        mock_pool.putconn.assert_any_call(mock_dead_conn, close=True)


class TestMetricsTracking:
    """Test suite for metrics tracking of recovery operations."""

    @patch("utils.db.get_conn")
    @patch("utils.db.metrics")
    def test_fetchone_metrics_on_success(self, mock_metrics, mock_get_conn):
        """Test fetchone records success metrics."""
        # Setup mock connection
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_get_conn.return_value.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = {"id": 1}

        # Setup metrics mock
        mock_metrics.record_latency.return_value.__enter__ = MagicMock()
        mock_metrics.record_latency.return_value.__exit__ = MagicMock()

        # Call and verify
        db.fetchone("SELECT * FROM test")

        # Check success metrics
        success_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if "success" in str(call)
        ]
        assert len(success_calls) > 0

    @patch("utils.db.get_conn")
    @patch("utils.db.metrics")
    def test_fetchone_metrics_on_not_found(self, mock_metrics, mock_get_conn):
        """Test fetchone records not found metrics."""
        # Setup mock connection - no result
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        mock_get_conn.return_value.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = None  # No result

        # Setup metrics mock
        mock_metrics.record_latency.return_value.__enter__ = MagicMock()
        mock_metrics.record_latency.return_value.__exit__ = MagicMock()

        # Call and verify
        result = db.fetchone("SELECT * FROM test")

        # Result should be None
        assert result is None

        # Check not_found metrics
        not_found_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if "not_found" in str(call)
        ]
        assert len(not_found_calls) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
