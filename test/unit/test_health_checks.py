"""Unit tests for health check functionality."""

import asyncio
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test MCP Server health checks
from mcp.health import ComponentHealth, HealthChecker, HealthStatus

# Test Client health checks
from client_mcp.monitoring.client_health import (
    ClientHealthMonitor,
)
from client_mcp.monitoring.client_health import HealthStatus as ClientHealthStatus


class TestMCPHealthChecker:
    """Test cases for MCP server health checks."""

    @pytest.fixture
    def health_checker(self):
        """Create a health checker instance for testing."""
        app = Mock()
        config = {
            "DB_HOST": "localhost",
            "DB_PORT": 5432,
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_pass",
            "DB_NAME": "test_db",
            "USE_CACHE": False,
        }
        return HealthChecker(app, config)

    @pytest.mark.asyncio
    async def test_database_health_check_healthy(self, health_checker):
        """Test database health check when healthy."""
        with patch("mcp.health.asyncpg.connect") as mock_connect:
            # Mock successful connection
            mock_conn = MagicMock()
            mock_conn.fetchval = asyncio.coroutine(lambda x: 10)
            mock_conn.close = asyncio.coroutine(lambda: None)
            mock_connect.return_value = asyncio.coroutine(lambda **kwargs: mock_conn)()

            result = await health_checker.check_database()

            assert result.status == HealthStatus.HEALTHY
            assert "Connected successfully" in result.message
            assert result.details["tables_count"] == 10

    @pytest.mark.asyncio
    async def test_database_health_check_unhealthy(self, health_checker):
        """Test database health check when connection fails."""
        with patch("mcp.health.asyncpg.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")

            result = await health_checker.check_database()

            assert result.status == HealthStatus.UNHEALTHY
            assert "Database error" in result.message

    @pytest.mark.asyncio
    async def test_system_resources_healthy(self, health_checker):
        """Test system resources check when healthy."""
        with patch("mcp.health.psutil.cpu_percent", return_value=50.0):
            with patch("mcp.health.psutil.virtual_memory") as mock_memory:
                mock_memory.return_value = Mock(
                    percent=60.0,
                    available=1024 * 1024 * 1024,
                )
                with patch("mcp.health.psutil.disk_usage") as mock_disk:
                    mock_disk.return_value = Mock(
                        percent=70.0,
                        free=10 * 1024 * 1024 * 1024,
                    )

                    result = await health_checker.check_system_resources()

                    assert result.status == HealthStatus.HEALTHY
                    assert result.details["cpu_percent"] == 50.0
                    assert result.details["memory_percent"] == 60.0

    @pytest.mark.asyncio
    async def test_system_resources_degraded(self, health_checker):
        """Test system resources check when degraded."""
        with patch("mcp.health.psutil.cpu_percent", return_value=75.0):
            with patch("mcp.health.psutil.virtual_memory") as mock_memory:
                mock_memory.return_value = Mock(
                    percent=80.0,
                    available=512 * 1024 * 1024,
                )
                with patch("mcp.health.psutil.disk_usage") as mock_disk:
                    mock_disk.return_value = Mock(
                        percent=85.0,
                        free=5 * 1024 * 1024 * 1024,
                    )

                    result = await health_checker.check_system_resources()

                    assert result.status == HealthStatus.DEGRADED
                    assert "High resource usage" in result.message

    @pytest.mark.asyncio
    async def test_get_health_overall_status(self, health_checker):
        """Test overall health status aggregation."""
        # Mock individual health checks
        with patch.object(health_checker, "check_database") as mock_db:
            mock_db.return_value = ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=10.0,
                message="OK",
            )

            with patch.object(health_checker, "check_redis") as mock_redis:
                mock_redis.return_value = ComponentHealth(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=20.0,
                    message="Slow",
                )

                with patch.object(health_checker, "check_mcp_tools") as mock_tools:
                    mock_tools.return_value = ComponentHealth(
                        name="tools",
                        status=HealthStatus.HEALTHY,
                        response_time_ms=5.0,
                        message="OK",
                    )

                    with patch.object(
                        health_checker,
                        "check_system_resources",
                    ) as mock_sys:
                        mock_sys.return_value = ComponentHealth(
                            name="system",
                            status=HealthStatus.HEALTHY,
                            response_time_ms=1.0,
                            message="OK",
                        )

                        with patch.object(
                            health_checker,
                            "check_external_apis",
                        ) as mock_apis:
                            mock_apis.return_value = ComponentHealth(
                                name="apis",
                                status=HealthStatus.HEALTHY,
                                response_time_ms=50.0,
                                message="OK",
                            )

                            result = await health_checker.get_health()

                            # Overall should be DEGRADED due to Redis
                            assert result.status == HealthStatus.DEGRADED
                            assert len(result.components) == 5
                            assert result.metrics["healthy_components"] == 4
                            assert result.metrics["degraded_components"] == 1


class TestClientHealthMonitor:
    """Test cases for client health monitoring."""

    @pytest.fixture
    def health_monitor(self):
        """Create a health monitor instance for testing."""
        return ClientHealthMonitor()

    @pytest.mark.asyncio
    async def test_bot_status_not_initialized(self, health_monitor):
        """Test bot status when not initialized."""
        result = await health_monitor.check_bot_status()

        assert result.status == ClientHealthStatus.UNHEALTHY
        assert "Bot not initialized" in result.message

    @pytest.mark.asyncio
    async def test_bot_status_healthy(self, health_monitor):
        """Test bot status when healthy."""
        # Mock bot instance
        mock_bot = Mock()
        mock_bot.client = Mock()
        health_monitor.set_bot_instance(mock_bot)
        health_monitor.record_activity()

        result = await health_monitor.check_bot_status()

        assert result.status == ClientHealthStatus.HEALTHY
        assert "Bot active and running" in result.message

    @pytest.mark.asyncio
    async def test_bot_status_inactive(self, health_monitor):
        """Test bot status when inactive."""
        mock_bot = Mock()
        mock_bot.client = Mock()
        health_monitor.set_bot_instance(mock_bot)
        health_monitor.last_activity = 0  # Very old activity

        result = await health_monitor.check_bot_status()

        assert result.status == ClientHealthStatus.DEGRADED
        assert "No activity" in result.message

    @pytest.mark.asyncio
    async def test_mcp_connectivity_healthy(self, health_monitor):
        """Test MCP connectivity when healthy."""
        mock_bot = Mock()
        mock_bot.mcp_connector = Mock()
        mock_bot.mcp_tools = ["tool1", "tool2", "tool3"]
        health_monitor.set_bot_instance(mock_bot)

        result = await health_monitor.check_mcp_connectivity()

        assert result.status == ClientHealthStatus.HEALTHY
        assert "3 tools available" in result.message

    @pytest.mark.asyncio
    async def test_gemini_api_no_key(self, health_monitor):
        """Test Gemini API check without API key."""
        with patch.dict("os.environ", {}, clear=True):
            result = await health_monitor.check_gemini_api()

            assert result.status == ClientHealthStatus.UNHEALTHY
            assert "API key not configured" in result.message

    @pytest.mark.asyncio
    async def test_gemini_api_placeholder_key(self, health_monitor):
        """Test Gemini API check with placeholder key."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "YOUR_API_KEY_HERE"}):
            result = await health_monitor.check_gemini_api()

            assert result.status == ClientHealthStatus.UNHEALTHY
            assert "not properly set" in result.message

    @pytest.mark.asyncio
    async def test_full_health_aggregation(self, health_monitor):
        """Test full health status aggregation."""
        mock_bot = Mock()
        mock_bot.client = Mock()
        mock_bot.mcp_connector = Mock()
        mock_bot.mcp_tools = ["tool1"]
        health_monitor.set_bot_instance(mock_bot)
        health_monitor.record_activity()

        with patch.dict("os.environ", {"GOOGLE_API_KEY": "valid_key"}):
            with patch("psutil.Process") as mock_process:
                mock_proc = Mock()
                mock_proc.cpu_percent.return_value = 30.0
                mock_proc.memory_info.return_value = Mock(rss=100 * 1024 * 1024)
                mock_process.return_value = mock_proc

                with patch("psutil.virtual_memory") as mock_memory:
                    mock_memory.return_value = Mock(percent=50.0)

                    result = await health_monitor.get_full_health()

                    assert result["status"] == ClientHealthStatus.HEALTHY.value
                    assert len(result["checks"]) == 4
                    assert result["summary"]["healthy"] == 4

    def test_record_activity(self, health_monitor):
        """Test activity recording."""
        initial_count = health_monitor.message_count
        health_monitor.record_activity()

        assert health_monitor.message_count == initial_count + 1
        assert health_monitor.last_activity > 0

    def test_record_error(self, health_monitor):
        """Test error recording."""
        initial_count = health_monitor.error_count
        health_monitor.record_error()

        assert health_monitor.error_count == initial_count + 1


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_liveness_endpoint(self):
        """Test liveness probe endpoint."""
        from mcp.health import HealthChecker

        app = Mock()
        config = {}
        checker = HealthChecker(app, config)

        result = await checker.get_liveness()

        assert result["status"] == "alive"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_readiness_endpoint_ready(self):
        """Test readiness probe when ready."""
        from mcp.health import HealthChecker

        app = Mock()
        config = {}
        checker = HealthChecker(app, config)

        with patch.object(checker, "check_database") as mock_db:
            mock_db.return_value = ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=10.0,
                message="OK",
            )

            result = await checker.get_readiness()

            assert result["ready"] is True
            assert result["database"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness_endpoint_not_ready(self):
        """Test readiness probe when not ready."""
        from mcp.health import HealthChecker

        app = Mock()
        config = {}
        checker = HealthChecker(app, config)

        with patch.object(checker, "check_database") as mock_db:
            mock_db.return_value = ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=10.0,
                message="Connection failed",
            )

            result = await checker.get_readiness()

            assert result["ready"] is False
            assert result["database"] == "unhealthy"
