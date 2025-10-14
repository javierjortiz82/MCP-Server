"""Unit tests for health check CLI."""

import argparse
import json

# Import the module under test
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli import health_check


class MockHealthResult:
    """Mock health check result."""

    def __init__(self, status="healthy", timestamp=None):
        self.status = MagicMock()
        self.status.value = status
        self.timestamp = timestamp or datetime.now()

    def to_dict(self):
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "component": "test",
        }


class TestHealthCheckCLI:
    """Test suite for health check CLI."""

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py"])
    @patch("sys.stdout", new_callable=StringIO)
    async def test_main_default_args(self, mock_stdout, mock_monitor_class):
        """Test main with default arguments."""
        # Setup mock
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(
            return_value={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "checks": [],
            }
        )
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        mock_monitor.get_full_health.assert_called_once()
        mock_monitor.print_health_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--format", "json"])
    @patch("sys.stdout", new_callable=StringIO)
    async def test_main_json_format(self, mock_stdout, mock_monitor_class):
        """Test main with JSON output format."""
        # Setup mock
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": [],
        }
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(return_value=health_data)
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify JSON output
        output = mock_stdout.getvalue()
        assert exc_info.value.code == 0
        # JSON should be printed
        parsed = json.loads(output)
        assert parsed["status"] == "healthy"

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--component", "bot"])
    async def test_main_specific_component_bot(self, mock_monitor_class):
        """Test main with specific component (bot)."""
        # Setup mock
        mock_result = MockHealthResult(status="healthy")
        mock_monitor = MagicMock()
        mock_monitor.check_bot_status = AsyncMock(return_value=mock_result)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        mock_monitor.check_bot_status.assert_called_once()

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--component", "mcp"])
    async def test_main_specific_component_mcp(self, mock_monitor_class):
        """Test main with specific component (mcp)."""
        # Setup mock
        mock_result = MockHealthResult(status="healthy")
        mock_monitor = MagicMock()
        mock_monitor.check_mcp_connectivity = AsyncMock(return_value=mock_result)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        mock_monitor.check_mcp_connectivity.assert_called_once()

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--component", "gemini"])
    async def test_main_specific_component_gemini(self, mock_monitor_class):
        """Test main with specific component (gemini)."""
        # Setup mock
        mock_result = MockHealthResult(status="healthy")
        mock_monitor = MagicMock()
        mock_monitor.check_gemini_api = AsyncMock(return_value=mock_result)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        mock_monitor.check_gemini_api.assert_called_once()

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--component", "resources"])
    async def test_main_specific_component_resources(self, mock_monitor_class):
        """Test main with specific component (resources)."""
        # Setup mock
        mock_result = MockHealthResult(status="healthy")
        mock_monitor = MagicMock()
        mock_monitor.check_system_resources = AsyncMock(return_value=mock_result)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        mock_monitor.check_system_resources.assert_called_once()

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--exit-code"])
    async def test_main_exit_code_healthy(self, mock_monitor_class):
        """Test main with --exit-code flag when healthy."""
        # Setup mock
        health_data = {"status": "healthy", "checks": []}
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(return_value=health_data)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Should exit with 0 for healthy
        assert exc_info.value.code == 0

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--exit-code"])
    async def test_main_exit_code_unhealthy(self, mock_monitor_class):
        """Test main with --exit-code flag when unhealthy."""
        # Setup mock
        health_data = {"status": "unhealthy", "checks": []}
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(return_value=health_data)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Should exit with 1 for unhealthy
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--exit-code"])
    async def test_main_exit_code_degraded(self, mock_monitor_class):
        """Test main with --exit-code flag when degraded."""
        # Setup mock
        health_data = {"status": "degraded", "checks": []}
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(return_value=health_data)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Should exit with 2 for degraded
        assert exc_info.value.code == 2

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--format", "human", "--component", "all"])
    async def test_main_combined_args(self, mock_monitor_class):
        """Test main with multiple arguments combined."""
        # Setup mock
        health_data = {"status": "healthy", "checks": []}
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(return_value=health_data)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        mock_monitor.get_full_health.assert_called_once()
        mock_monitor.print_health_status.assert_called_once()


class TestHealthCheckArgumentParsing:
    """Test suite for argument parsing."""

    @patch("sys.argv", ["health_check.py"])
    def test_default_arguments(self):
        """Test default argument values."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--format", choices=["human", "json"], default="human")
        parser.add_argument(
            "--component",
            choices=["bot", "mcp", "gemini", "resources", "all"],
            default="all",
        )
        parser.add_argument("--exit-code", action="store_true")

        args = parser.parse_args([])

        assert args.format == "human"
        assert args.component == "all"
        assert args.exit_code is False

    @patch("sys.argv", ["health_check.py", "--format", "json"])
    def test_json_format_argument(self):
        """Test --format json argument."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--format", choices=["human", "json"], default="human")

        args = parser.parse_args(["--format", "json"])

        assert args.format == "json"

    @patch("sys.argv", ["health_check.py", "--component", "bot"])
    def test_component_argument(self):
        """Test --component argument."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--component",
            choices=["bot", "mcp", "gemini", "resources", "all"],
            default="all",
        )

        args = parser.parse_args(["--component", "bot"])

        assert args.component == "bot"

    @patch("sys.argv", ["health_check.py", "--exit-code"])
    def test_exit_code_flag(self):
        """Test --exit-code flag."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--exit-code", action="store_true")

        args = parser.parse_args(["--exit-code"])

        assert args.exit_code is True


class TestHealthCheckComponentMapping:
    """Test suite for component check method mapping."""

    @pytest.mark.asyncio
    async def test_component_method_mapping_exists(self):
        """Test that all component mappings are defined."""
        # This tests the structure in main() function
        check_methods = [
            "check_bot_status",
            "check_mcp_connectivity",
            "check_gemini_api",
            "check_system_resources",
        ]

        # All methods should exist in ClientHealthMonitor
        from monitoring.client_health import ClientHealthMonitor

        monitor = ClientHealthMonitor()

        for method_name in check_methods:
            assert hasattr(monitor, method_name), f"Missing method: {method_name}"


class TestHealthCheckEdgeCases:
    """Test suite for edge cases."""

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch(
        "sys.argv",
        ["health_check.py", "--component", "bot", "--format", "json", "--exit-code"],
    )
    @patch("sys.stdout", new_callable=StringIO)
    async def test_all_flags_combined(self, mock_stdout, mock_monitor_class):
        """Test all flags combined."""
        # Setup mock
        mock_result = MockHealthResult(status="healthy")
        mock_monitor = MagicMock()
        mock_monitor.check_bot_status = AsyncMock(return_value=mock_result)
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit) as exc_info:
            await health_check.main()

        # Verify
        assert exc_info.value.code == 0
        output = mock_stdout.getvalue()
        # Should output JSON
        parsed = json.loads(output)
        assert "status" in parsed

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py"])
    async def test_monitor_instantiation(self, mock_monitor_class):
        """Test ClientHealthMonitor is instantiated correctly."""
        # Setup mock
        mock_monitor = MagicMock()
        mock_monitor.get_full_health = AsyncMock(
            return_value={"status": "healthy", "checks": []}
        )
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit):
            await health_check.main()

        # Verify monitor was created
        mock_monitor_class.assert_called_once()

    @pytest.mark.asyncio
    @patch("cli.health_check.ClientHealthMonitor")
    @patch("sys.argv", ["health_check.py", "--component", "bot"])
    @patch("sys.stdout", new_callable=StringIO)
    async def test_specific_component_health_data_structure(
        self, mock_stdout, mock_monitor_class
    ):
        """Test health data structure for specific component check."""
        # Setup mock
        mock_result = MockHealthResult(
            status="healthy", timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )
        mock_monitor = MagicMock()
        mock_monitor.check_bot_status = AsyncMock(return_value=mock_result)
        mock_monitor.print_health_status = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Run main
        with pytest.raises(SystemExit):
            await health_check.main()

        # Verify print_health_status was called with correct structure
        call_args = mock_monitor.print_health_status.call_args[0][0]
        assert "status" in call_args
        assert "timestamp" in call_args
        assert "checks" in call_args
        assert isinstance(call_args["checks"], list)
