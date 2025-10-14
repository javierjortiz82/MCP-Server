"""Unit tests for monitoring/client_health.py."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monitoring.client_health import (
    ClientHealthMonitor,
    HealthCheck,
    HealthStatus,
    health_monitor,
    run_health_check,
    setup_health_monitoring,
)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test all health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthCheck:
    """Test HealthCheck dataclass."""

    def test_health_check_basic(self):
        """Test basic HealthCheck creation."""
        check = HealthCheck(
            component="test",
            status=HealthStatus.HEALTHY,
            message="Test message",
            response_time_ms=10.5,
        )
        assert check.component == "test"
        assert check.status == HealthStatus.HEALTHY
        assert check.message == "Test message"
        assert check.response_time_ms == 10.5

    def test_health_check_to_dict_basic(self):
        """Test HealthCheck to_dict without optional fields."""
        check = HealthCheck(
            component="test",
            status=HealthStatus.HEALTHY,
            message="Test",
            response_time_ms=10.5,
        )
        result = check.to_dict()
        assert result["component"] == "test"
        assert result["status"] == "healthy"
        assert result["message"] == "Test"
        assert result["response_time_ms"] == 10.5
        assert "details" not in result
        assert "timestamp" not in result

    def test_health_check_to_dict_with_details(self):
        """Test HealthCheck to_dict with details."""
        check = HealthCheck(
            component="test",
            status=HealthStatus.HEALTHY,
            message="Test",
            response_time_ms=10.5,
            details={"key": "value"},
        )
        result = check.to_dict()
        assert result["details"] == {"key": "value"}

    def test_health_check_to_dict_with_timestamp(self):
        """Test HealthCheck to_dict with timestamp."""
        now = datetime.now(UTC)
        check = HealthCheck(
            component="test",
            status=HealthStatus.HEALTHY,
            message="Test",
            response_time_ms=10.5,
            timestamp=now,
        )
        result = check.to_dict()
        assert "timestamp" in result
        assert result["timestamp"] == now.isoformat()


class TestClientHealthMonitorInit:
    """Test ClientHealthMonitor initialization."""

    def test_monitor_initialization(self):
        """Test monitor initializes correctly."""
        monitor = ClientHealthMonitor()
        assert monitor.bot_instance is None
        assert monitor.message_count == 0
        assert monitor.error_count == 0
        assert monitor.start_time > 0

    def test_set_bot_instance(self):
        """Test setting bot instance."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        monitor.set_bot_instance(mock_bot)
        assert monitor.bot_instance == mock_bot

    def test_record_activity(self):
        """Test recording activity."""
        monitor = ClientHealthMonitor()
        initial_count = monitor.message_count
        monitor.record_activity()
        assert monitor.message_count == initial_count + 1
        assert monitor.last_activity > 0

    def test_record_error(self):
        """Test recording errors."""
        monitor = ClientHealthMonitor()
        initial_count = monitor.error_count
        monitor.record_error()
        assert monitor.error_count == initial_count + 1


class TestCheckBotStatus:
    """Test check_bot_status method."""

    @pytest.mark.asyncio
    async def test_bot_not_initialized(self):
        """Test when bot is not initialized."""
        monitor = ClientHealthMonitor()
        result = await monitor.check_bot_status()
        assert result.component == "bot"
        assert result.status == HealthStatus.UNHEALTHY
        assert "not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_bot_client_not_initialized(self):
        """Test when bot client is not initialized."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = None
        monitor.set_bot_instance(mock_bot)
        result = await monitor.check_bot_status()
        assert result.status == HealthStatus.UNHEALTHY
        assert "client not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_bot_healthy_recent_activity(self):
        """Test healthy bot with recent activity."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = MagicMock()
        monitor.set_bot_instance(mock_bot)
        monitor.record_activity()
        result = await monitor.check_bot_status()
        assert result.status == HealthStatus.HEALTHY
        assert "active" in result.message.lower()
        assert "message_count" in result.details
        assert "error_count" in result.details

    @pytest.mark.asyncio
    async def test_bot_degraded_no_recent_activity(self):
        """Test bot degraded due to inactivity."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = MagicMock()
        monitor.set_bot_instance(mock_bot)
        monitor.last_activity = 0  # Very old activity
        result = await monitor.check_bot_status()
        assert result.status == HealthStatus.DEGRADED
        assert "no activity" in result.message.lower()

    @pytest.mark.asyncio
    async def test_bot_status_exception_handling(self):
        """Test exception handling in bot status check."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = MagicMock()
        # Force an exception by making hasattr raise
        monitor.bot_instance = mock_bot
        with patch(
            "monitoring.client_health.hasattr", side_effect=Exception("Test error")
        ):
            result = await monitor.check_bot_status()
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()


class TestCheckMCPConnectivity:
    """Test check_mcp_connectivity method."""

    @pytest.mark.asyncio
    async def test_mcp_bot_not_initialized(self):
        """Test MCP check when bot not initialized."""
        monitor = ClientHealthMonitor()
        result = await monitor.check_mcp_connectivity()
        assert result.component == "mcp_connection"
        assert result.status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_mcp_no_connector(self):
        """Test when MCP connector doesn't exist."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock(spec=[])  # No mcp_client attribute
        monitor.set_bot_instance(mock_bot)
        result = await monitor.check_mcp_connectivity()
        assert result.status == HealthStatus.DEGRADED
        assert "no mcp connector" in result.message.lower()

    @pytest.mark.asyncio
    async def test_mcp_healthy_with_tools(self):
        """Test healthy MCP connection with tools."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.mcp_client = MagicMock()
        mock_bot.mcp_tools = [MagicMock(), MagicMock(), MagicMock()]
        monitor.set_bot_instance(mock_bot)
        result = await monitor.check_mcp_connectivity()
        assert result.status == HealthStatus.HEALTHY
        assert "3 tools" in result.message
        assert result.details["tool_count"] == 3

    @pytest.mark.asyncio
    async def test_mcp_degraded_no_tools(self):
        """Test MCP connected but no tools."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.mcp_client = MagicMock()
        mock_bot.mcp_tools = []
        monitor.set_bot_instance(mock_bot)
        result = await monitor.check_mcp_connectivity()
        assert result.status == HealthStatus.DEGRADED
        assert "no tools" in result.message.lower()

    @pytest.mark.asyncio
    async def test_mcp_exception_handling(self):
        """Test exception handling in MCP check."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.mcp_client = MagicMock()
        monitor.set_bot_instance(mock_bot)
        with patch(
            "monitoring.client_health.hasattr", side_effect=Exception("Test error")
        ):
            result = await monitor.check_mcp_connectivity()
        assert result.status == HealthStatus.UNHEALTHY


class TestCheckGeminiAPI:
    """Test check_gemini_api method."""

    @pytest.mark.asyncio
    async def test_gemini_no_api_key(self):
        """Test when API key not configured."""
        monitor = ClientHealthMonitor()
        with patch.dict(os.environ, {}, clear=True):
            result = await monitor.check_gemini_api()
        assert result.component == "gemini_api"
        assert result.status == HealthStatus.UNHEALTHY
        assert "not configured" in result.message.lower()

    @pytest.mark.asyncio
    async def test_gemini_invalid_api_key(self):
        """Test with invalid API key."""
        monitor = ClientHealthMonitor()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "YOUR_API_KEY_HERE"}):
            result = await monitor.check_gemini_api()
        assert result.status == HealthStatus.UNHEALTHY
        assert "not properly set" in result.message.lower()

    @pytest.mark.asyncio
    async def test_gemini_healthy_with_client(self):
        """Test healthy Gemini API with client."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = MagicMock()
        monitor.set_bot_instance(mock_bot)
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "valid_api_key_123"}):
            result = await monitor.check_gemini_api()
        assert result.status == HealthStatus.HEALTHY
        assert "configured" in result.message.lower()
        assert result.details["api_key_configured"] is True

    @pytest.mark.asyncio
    async def test_gemini_degraded_no_client(self):
        """Test Gemini API configured but no client."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock(spec=[])  # No client attribute
        monitor.set_bot_instance(mock_bot)
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "valid_key"}):
            result = await monitor.check_gemini_api()
        assert result.status == HealthStatus.DEGRADED
        assert "not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_gemini_exception_handling(self):
        """Test exception handling in Gemini check."""
        monitor = ClientHealthMonitor()
        with patch("os.getenv", side_effect=Exception("Test error")):
            result = await monitor.check_gemini_api()
        assert result.status == HealthStatus.UNHEALTHY


class TestCheckSystemResources:
    """Test check_system_resources method."""

    @pytest.mark.asyncio
    async def test_system_resources_normal(self):
        """Test normal system resource usage."""
        monitor = ClientHealthMonitor()
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.cpu_percent.return_value = 10.0
            mock_proc.memory_info.return_value = MagicMock(
                rss=100 * 1024 * 1024
            )  # 100 MB
            mock_process.return_value = mock_proc
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value = MagicMock(percent=50.0)
                result = await monitor.check_system_resources()

        assert result.component == "system_resources"
        assert result.status == HealthStatus.HEALTHY
        assert "normal" in result.message.lower()
        assert result.details["process_cpu_percent"] == 10.0

    @pytest.mark.asyncio
    async def test_system_resources_high_memory(self):
        """Test high memory usage."""
        monitor = ClientHealthMonitor()
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.cpu_percent.return_value = 10.0
            mock_proc.memory_info.return_value = MagicMock(
                rss=1500 * 1024 * 1024
            )  # 1500 MB
            mock_process.return_value = mock_proc
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value = MagicMock(percent=50.0)
                result = await monitor.check_system_resources()

        assert result.status == HealthStatus.DEGRADED
        assert "high resource" in result.message.lower()

    @pytest.mark.asyncio
    async def test_system_resources_high_cpu(self):
        """Test high CPU usage."""
        monitor = ClientHealthMonitor()
        with patch("psutil.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.cpu_percent.return_value = 85.0
            mock_proc.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
            mock_process.return_value = mock_proc
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value = MagicMock(percent=50.0)
                result = await monitor.check_system_resources()

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_system_resources_exception(self):
        """Test exception handling in resource check."""
        monitor = ClientHealthMonitor()
        with patch("psutil.Process", side_effect=Exception("Test error")):
            result = await monitor.check_system_resources()
        assert result.status == HealthStatus.UNKNOWN


class TestGetFullHealth:
    """Test get_full_health method."""

    @pytest.mark.asyncio
    async def test_full_health_all_healthy(self):
        """Test full health check when all components healthy."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = MagicMock()
        mock_bot.mcp_client = MagicMock()
        mock_bot.mcp_tools = [MagicMock()]
        monitor.set_bot_instance(mock_bot)

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "valid_key"}):
            with patch("psutil.Process") as mock_process:
                mock_proc = MagicMock()
                mock_proc.cpu_percent.return_value = 10.0
                mock_proc.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
                mock_process.return_value = mock_proc
                with patch("psutil.virtual_memory") as mock_vm:
                    mock_vm.return_value = MagicMock(percent=50.0)
                    result = await monitor.get_full_health()

        assert result["status"] == "healthy"
        assert result["summary"]["total_checks"] == 4
        assert result["summary"]["healthy"] == 4

    @pytest.mark.asyncio
    async def test_full_health_some_degraded(self):
        """Test full health with some degraded components."""
        monitor = ClientHealthMonitor()
        mock_bot = MagicMock()
        mock_bot.client = MagicMock()
        mock_bot.mcp_client = MagicMock()
        mock_bot.mcp_tools = []  # No tools - degraded
        monitor.set_bot_instance(mock_bot)

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "valid_key"}):
            with patch("psutil.Process") as mock_process:
                mock_proc = MagicMock()
                mock_proc.cpu_percent.return_value = 10.0
                mock_proc.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
                mock_process.return_value = mock_proc
                with patch("psutil.virtual_memory") as mock_vm:
                    mock_vm.return_value = MagicMock(percent=50.0)
                    result = await monitor.get_full_health()

        assert result["status"] == "degraded"
        assert result["summary"]["degraded"] >= 1

    @pytest.mark.asyncio
    async def test_full_health_some_unhealthy(self):
        """Test full health with unhealthy components."""
        monitor = ClientHealthMonitor()
        # Bot not initialized - unhealthy
        with patch.dict(os.environ, {}, clear=True):  # No API key
            result = await monitor.get_full_health()

        assert result["status"] == "unhealthy"
        assert result["summary"]["unhealthy"] >= 1

    @pytest.mark.asyncio
    async def test_full_health_exception_handling(self):
        """Test full health handles exceptions in checks."""
        monitor = ClientHealthMonitor()

        # Mock one check to raise exception
        async def failing_check():
            raise ValueError("Test exception")

        monitor.check_bot_status = failing_check
        result = await monitor.get_full_health()

        # Should still complete and have results
        assert "status" in result
        assert "checks" in result


class TestPrintHealthStatus:
    """Test print_health_status method."""

    def test_print_health_status(self, capsys):
        """Test printing health status."""
        monitor = ClientHealthMonitor()
        health_data = {
            "status": "healthy",
            "timestamp": "2025-01-01T00:00:00Z",
            "uptime_seconds": 100,
            "checks": [
                {
                    "component": "test",
                    "status": "healthy",
                    "message": "All good",
                    "response_time_ms": 10.5,
                    "details": {"key": "value"},
                }
            ],
            "summary": {
                "total_checks": 1,
                "healthy": 1,
                "degraded": 0,
                "unhealthy": 0,
                "unknown": 0,
            },
        }

        monitor.print_health_status(health_data)
        captured = capsys.readouterr()
        assert "CLIENT HEALTH STATUS" in captured.out
        assert "HEALTHY" in captured.out
        assert "test" in captured.out


class TestGlobalFunctions:
    """Test global functions."""

    @pytest.mark.asyncio
    async def test_run_health_check(self):
        """Test run_health_check function."""
        with patch("monitoring.client_health.health_monitor") as mock_monitor:
            mock_monitor.get_full_health = AsyncMock(return_value={"status": "healthy"})
            result = await run_health_check()
        assert result == {"status": "healthy"}

    def test_setup_health_monitoring(self):
        """Test setup_health_monitoring function."""
        mock_bot = MagicMock()
        with patch("monitoring.client_health.health_monitor") as mock_monitor:
            setup_health_monitoring(mock_bot)
            mock_monitor.set_bot_instance.assert_called_once_with(mock_bot)

    def test_global_health_monitor_exists(self):
        """Test global health_monitor instance exists."""
        assert health_monitor is not None
        assert isinstance(health_monitor, ClientHealthMonitor)
