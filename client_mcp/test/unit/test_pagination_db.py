"""Unit tests for core/pagination_db.py."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from core.pagination_db import PaginationDB


class TestPaginationDBInit:
    """Test PaginationDB initialization."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_init_with_persistence_enabled(self, mock_pool_class, mock_settings):
        """Test initialization with persistence enabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        assert db._enabled is True
        assert db._pool is not None
        mock_pool_class.assert_called_once()

    @patch("core.pagination_db.settings")
    def test_init_with_persistence_disabled(self, mock_settings):
        """Test initialization with persistence disabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = False

        db = PaginationDB()

        assert db._enabled is False
        assert db._pool is None

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_init_pool_failure(self, mock_pool_class, mock_settings):
        """Test initialization handles pool creation failure gracefully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        # Simulate connection error
        mock_pool_class.side_effect = Exception("Connection failed")

        db = PaginationDB()

        # Should disable persistence and not raise
        assert db._enabled is False
        assert db._pool is None


class TestSaveContext:
    """Test save_context method."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_save_context_success(self, mock_pool_class, mock_settings):
        """Test saving context successfully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"
        mock_settings.PAGINATION_TTL_HOURS = 24

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        session_id = uuid4()
        products = [{"id": 1, "name": "Product 1"}]

        result = db.save_context(
            session_id=session_id,
            category="test_category",
            tool_name="search_products",
            query="test query",
            products=products,
            current_page=0,
            page_size=4,
        )

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("core.pagination_db.settings")
    def test_save_context_when_disabled(self, mock_settings):
        """Test save_context returns False when persistence is disabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = False

        db = PaginationDB()

        session_id = uuid4()
        products = [{"id": 1, "name": "Product 1"}]

        result = db.save_context(
            session_id=session_id,
            category="test_category",
            tool_name="search_products",
            query="test query",
            products=products,
        )

        assert result is False

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_save_context_handles_error(self, mock_pool_class, mock_settings):
        """Test save_context handles database errors gracefully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"
        mock_settings.PAGINATION_TTL_HOURS = 24

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        session_id = uuid4()
        products = [{"id": 1, "name": "Product 1"}]

        result = db.save_context(
            session_id=session_id,
            category="test_category",
            tool_name="search_products",
            query="test query",
            products=products,
        )

        assert result is False
        mock_conn.rollback.assert_called_once()


class TestLoadContext:
    """Test load_context method."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_load_context_success(self, mock_pool_class, mock_settings):
        """Test loading context successfully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock database result
        db_row = {
            "tool_name": "search_products",
            "query": "test query",
            "products": json.dumps([{"id": 1, "name": "Product 1"}]),
            "current_page": 0,
            "page_size": 4,
            "total_items": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        mock_cursor.fetchone.return_value = db_row
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        session_id = uuid4()
        result = db.load_context(session_id, "test_category")

        assert result is not None
        assert result["tool_name"] == "search_products"
        assert result["query"] == "test query"
        assert len(result["products"]) == 1
        assert result["current_page"] == 0
        assert result["page_size"] == 4

    @patch("core.pagination_db.settings")
    def test_load_context_when_disabled(self, mock_settings):
        """Test load_context returns None when persistence is disabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = False

        db = PaginationDB()

        session_id = uuid4()
        result = db.load_context(session_id, "test_category")

        assert result is None

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_load_context_not_found(self, mock_pool_class, mock_settings):
        """Test load_context returns None when context not found."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        session_id = uuid4()
        result = db.load_context(session_id, "test_category")

        assert result is None


class TestDeleteContext:
    """Test delete_context method."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_delete_context_success(self, mock_pool_class, mock_settings):
        """Test deleting context successfully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        session_id = uuid4()
        result = db.delete_context(session_id, "test_category")

        assert result is True

    @patch("core.pagination_db.settings")
    def test_delete_context_when_disabled(self, mock_settings):
        """Test delete_context returns False when persistence is disabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = False

        db = PaginationDB()

        session_id = uuid4()
        result = db.delete_context(session_id, "test_category")

        assert result is False


class TestCleanupExpired:
    """Test cleanup_expired method."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_cleanup_expired_success(self, mock_pool_class, mock_settings):
        """Test cleanup expired contexts successfully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)  # 5 deleted
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        result = db.cleanup_expired()

        assert result == 5

    @patch("core.pagination_db.settings")
    def test_cleanup_expired_when_disabled(self, mock_settings):
        """Test cleanup_expired returns 0 when persistence is disabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = False

        db = PaginationDB()

        result = db.cleanup_expired()

        assert result == 0


class TestCleanupSession:
    """Test cleanup_session method."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_cleanup_session_success(self, mock_pool_class, mock_settings):
        """Test cleanup session contexts successfully."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.getconn.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        session_id = uuid4()
        result = db.cleanup_session(session_id)

        assert result == 3


class TestClose:
    """Test close method."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_close(self, mock_pool_class, mock_settings):
        """Test closing database pool."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()
        db.close()

        mock_pool.closeall.assert_called_once()


class TestIsEnabled:
    """Test is_enabled property."""

    @patch("core.pagination_db.settings")
    @patch("core.pagination_db.pool.SimpleConnectionPool")
    def test_is_enabled_true(self, mock_pool_class, mock_settings):
        """Test is_enabled returns True when persistence is working."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = True
        mock_settings.PAGINATION_DB_HOST = "localhost"
        mock_settings.PAGINATION_DB_PORT = 5434
        mock_settings.PAGINATION_DB_NAME = "sales"
        mock_settings.PAGINATION_DB_USER = "postgres"
        mock_settings.PAGINATION_DB_PASSWORD = "password"

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        db = PaginationDB()

        assert db.is_enabled is True

    @patch("core.pagination_db.settings")
    def test_is_enabled_false(self, mock_settings):
        """Test is_enabled returns False when persistence is disabled."""
        mock_settings.PAGINATION_PERSISTENCE_ENABLED = False

        db = PaginationDB()

        assert db.is_enabled is False
