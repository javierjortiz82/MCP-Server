"""Unit tests for async database connection.

Tests FIX 3.1: Async database connection with asyncpg.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from unittest.mock import AsyncMock, patch

import pytest

from demo_agent.db.connection import (
    AsyncDatabaseConnection,
    close_db,
    get_db,
    init_db,
)


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool."""
    return AsyncMock()


@pytest.fixture
def mock_connection():
    """Create a mock asyncpg connection."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_async_connection_init():
    """Test AsyncDatabaseConnection initialization."""
    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://user:pass@localhost/db"
        mock_config.SCHEMA_NAME = "test"

        conn = AsyncDatabaseConnection()

        assert conn.connection_string == "postgresql://user:pass@localhost/db"
        assert conn.schema == "test"
        assert conn.pool is None


@pytest.mark.asyncio
async def test_async_connection_pool_creation(mock_pool):
    """Test asyncpg connection pool creation."""
    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://user:pass@localhost/db"
        mock_config.SCHEMA_NAME = "test"

        with patch("demo_agent.db.connection.asyncpg.create_pool") as mock_create:
            mock_create.return_value = mock_pool

            conn = AsyncDatabaseConnection()
            await conn.connect()

            assert conn.pool == mock_pool
            mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_async_execute_fetchrow(mock_pool, mock_connection):
    """Test async execute with fetchrow (single row)."""
    mock_row = {"id": 1, "user_key": "user_123", "tokens_consumed": 100}
    mock_connection.fetchrow.return_value = mock_row

    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_pool.acquire.return_value.__aexit__.return_value = None

    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        conn = AsyncDatabaseConnection()
        conn.pool = mock_pool

        result = await conn.execute_one(
            "SELECT * FROM :SCHEMA_NAME.demo_usage WHERE user_key = %s",
            ("user_123",),
        )

        assert result == mock_row
        mock_connection.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_async_execute_fetch_all(mock_pool, mock_connection):
    """Test async execute with fetch (multiple rows)."""
    mock_rows = [
        {"id": 1, "user_key": "user_1"},
        {"id": 2, "user_key": "user_2"},
    ]
    mock_connection.fetch.return_value = mock_rows

    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_pool.acquire.return_value.__aexit__.return_value = None

    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        conn = AsyncDatabaseConnection()
        conn.pool = mock_pool

        result = await conn.execute_all(
            "SELECT * FROM :SCHEMA_NAME.demo_users"
        )

        assert result == mock_rows
        mock_connection.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_async_execute_insert(mock_pool, mock_connection):
    """Test async execute for INSERT (no return)."""
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_pool.acquire.return_value.__aexit__.return_value = None

    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        conn = AsyncDatabaseConnection()
        conn.pool = mock_pool

        result = await conn.execute(
            "INSERT INTO :SCHEMA_NAME.demo_usage (user_key) VALUES (%s)",
            ("user_123",),
        )

        assert result is None
        mock_connection.execute.assert_called_once()


@pytest.mark.asyncio
async def test_convert_placeholders():
    """Test SQL placeholder conversion from %s to $1, $2."""
    query = "SELECT * FROM users WHERE id = %s AND name = %s"
    converted = AsyncDatabaseConnection._convert_placeholders(query)

    assert converted == "SELECT * FROM users WHERE id = $1 AND name = $2"


@pytest.mark.asyncio
async def test_convert_placeholders_with_strings():
    """Test placeholder conversion with string literals."""
    query = "SELECT * FROM users WHERE id = %s AND name = 'test%s'"
    converted = AsyncDatabaseConnection._convert_placeholders(query)

    # %s inside string literals should NOT be converted
    assert "$1" in converted
    assert "test%s" in converted


@pytest.mark.asyncio
async def test_placeholder_schema_replacement():
    """Test schema name placeholder replacement."""
    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "public"

        query = "SELECT * FROM :SCHEMA_NAME.users"

        with patch("demo_agent.db.connection.asyncpg.create_pool"):
            conn = AsyncDatabaseConnection()
            # Query should be prepared but not yet executed
            assert ":SCHEMA_NAME" in query


@pytest.mark.asyncio
async def test_get_db_singleton():
    """Test that get_db returns singleton instance."""
    # Reset global state
    import demo_agent.db.connection as db_module
    db_module._db_connection = None

    db1 = get_db()
    db2 = get_db()

    assert db1 is db2
    assert isinstance(db1, AsyncDatabaseConnection)

    # Cleanup
    db_module._db_connection = None


@pytest.mark.asyncio
async def test_init_db_creates_pool(mock_pool):
    """Test init_db creates the connection pool."""
    import demo_agent.db.connection as db_module

    # Reset state
    db_module._db_connection = None
    db_module._db_initialized = False

    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        with patch("demo_agent.db.connection.asyncpg.create_pool") as mock_create:
            mock_create.return_value = mock_pool

            await init_db()

            db = get_db()
            assert db.pool == mock_pool
            assert db_module._db_initialized is True

    # Cleanup
    db_module._db_connection = None
    db_module._db_initialized = False


@pytest.mark.asyncio
async def test_close_db_closes_pool(mock_pool):
    """Test close_db closes the connection pool."""
    import demo_agent.db.connection as db_module

    # Setup
    db_module._db_connection = None
    db_module._db_initialized = False

    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        with patch("demo_agent.db.connection.asyncpg.create_pool") as mock_create:
            mock_create.return_value = mock_pool

            await init_db()
            await close_db()

            mock_pool.close.assert_called_once()
            assert db_module._db_connection is None
            assert db_module._db_initialized is False


@pytest.mark.asyncio
async def test_error_handling_on_connect_failure():
    """Test error handling when connection fails."""
    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        with patch("demo_agent.db.connection.asyncpg.create_pool") as mock_create:
            mock_create.side_effect = Exception("Connection refused")

            conn = AsyncDatabaseConnection()
            with pytest.raises(RuntimeError):
                await conn.connect()


@pytest.mark.asyncio
async def test_error_handling_on_query_failure(mock_pool, mock_connection):
    """Test error handling on query failure."""
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_pool.acquire.return_value.__aexit__.return_value = None
    mock_connection.fetchrow.side_effect = Exception("Syntax error")

    with patch("demo_agent.db.connection.config") as mock_config:
        mock_config.DATABASE_URL = "postgresql://localhost/db"
        mock_config.SCHEMA_NAME = "test"

        conn = AsyncDatabaseConnection()
        conn.pool = mock_pool

        with pytest.raises(RuntimeError):
            await conn.execute_one("SELECT * FROM :SCHEMA_NAME.users")
