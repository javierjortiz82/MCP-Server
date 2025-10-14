"""Unit tests for MCPLogger enhanced logging utility."""

import logging
from io import StringIO
from unittest.mock import patch

from utils.logger import LogLevel, MCPLogger, get_logger, logger


class TestLogLevel:
    """Test suite for LogLevel enum."""

    def test_log_level_debug(self):
        """Test DEBUG log level has correct value."""
        assert LogLevel.DEBUG.value == "🔍 DEBUG"

    def test_log_level_info(self):
        """Test INFO log level has correct value."""
        assert LogLevel.INFO.value == "ℹ️  INFO"

    def test_log_level_warning(self):
        """Test WARNING log level has correct value."""
        assert LogLevel.WARNING.value == "⚠️  WARNING"

    def test_log_level_error(self):
        """Test ERROR log level has correct value."""
        assert LogLevel.ERROR.value == "❌ ERROR"

    def test_log_level_critical(self):
        """Test CRITICAL log level has correct value."""
        assert LogLevel.CRITICAL.value == "🔥 CRITICAL"

    def test_log_level_success(self):
        """Test SUCCESS log level has correct value."""
        assert LogLevel.SUCCESS.value == "✅ SUCCESS"

    def test_log_level_tool_call(self):
        """Test TOOL_CALL log level has correct value."""
        assert LogLevel.TOOL_CALL.value == "🔧 TOOL_CALL"

    def test_log_level_mcp_connect(self):
        """Test MCP_CONNECT log level has correct value."""
        assert LogLevel.MCP_CONNECT.value == "📡 MCP_CONNECT"

    def test_log_level_mcp_response(self):
        """Test MCP_RESPONSE log level has correct value."""
        assert LogLevel.MCP_RESPONSE.value == "📨 MCP_RESPONSE"


class TestMCPLoggerInitialization:
    """Test suite for MCPLogger initialization."""

    def test_default_initialization(self):
        """Test MCPLogger with default parameters."""
        test_logger = MCPLogger()
        assert test_logger.logger.name == "client_mcp"
        assert test_logger.logger.level == logging.INFO

    def test_custom_name_initialization(self):
        """Test MCPLogger with custom name."""
        test_logger = MCPLogger(name="test_logger")
        assert test_logger.logger.name == "test_logger"

    def test_custom_level_initialization(self):
        """Test MCPLogger with custom level."""
        test_logger = MCPLogger(level="DEBUG")
        assert test_logger.logger.level == logging.DEBUG

    def test_level_case_insensitive(self):
        """Test log level is case insensitive."""
        test_logger = MCPLogger(level="debug")
        assert test_logger.logger.level == logging.DEBUG

    def test_handlers_configured(self):
        """Test logger has handler configured."""
        test_logger = MCPLogger()
        assert len(test_logger.logger.handlers) > 0

    def test_logger_propagate_disabled(self):
        """Test logger propagation is disabled."""
        test_logger = MCPLogger()
        assert test_logger.logger.propagate is False


class TestMCPLoggerBasicMethods:
    """Test suite for basic logging methods."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_debug_message(self, mock_stdout):
        """Test debug method logs message with emoji."""
        test_logger = MCPLogger(level="DEBUG")
        test_logger.debug("Test debug message")

        output = mock_stdout.getvalue()
        assert "🔍" in output
        assert "Test debug message" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_debug_custom_emoji(self, mock_stdout):
        """Test debug method with custom emoji."""
        test_logger = MCPLogger(level="DEBUG")
        test_logger.debug("Test message", emoji="🎯")

        output = mock_stdout.getvalue()
        assert "🎯" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_info_message(self, mock_stdout):
        """Test info method logs message with emoji."""
        test_logger = MCPLogger(level="INFO")
        test_logger.info("Test info message")

        output = mock_stdout.getvalue()
        assert "ℹ️" in output
        assert "Test info message" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_warning_message(self, mock_stdout):
        """Test warning method logs message with emoji."""
        test_logger = MCPLogger(level="WARNING")
        test_logger.warning("Test warning message")

        output = mock_stdout.getvalue()
        assert "⚠️" in output
        assert "Test warning message" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_error_message(self, mock_stdout):
        """Test error method logs message with emoji."""
        test_logger = MCPLogger(level="ERROR")
        test_logger.error("Test error message")

        output = mock_stdout.getvalue()
        assert "❌" in output
        assert "Test error message" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_critical_message(self, mock_stdout):
        """Test critical method logs message with emoji."""
        test_logger = MCPLogger(level="CRITICAL")
        test_logger.critical("Test critical message")

        output = mock_stdout.getvalue()
        assert "🔥" in output
        assert "Test critical message" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_success_message(self, mock_stdout):
        """Test success method logs message with emoji."""
        test_logger = MCPLogger(level="INFO")
        test_logger.success("Test success message")

        output = mock_stdout.getvalue()
        assert "✅" in output
        assert "Test success message" in output


class TestMCPLoggerToolMethods:
    """Test suite for MCP tool-related logging methods."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_call_without_params(self, mock_stdout):
        """Test tool_call method without parameters."""
        test_logger = MCPLogger(level="INFO")
        test_logger.tool_call("search_products")

        output = mock_stdout.getvalue()
        assert "🔧" in output
        assert "search_products()" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_call_with_params(self, mock_stdout):
        """Test tool_call method with parameters."""
        test_logger = MCPLogger(level="INFO")
        test_logger.tool_call("search_products", query="laptop", limit=10)

        output = mock_stdout.getvalue()
        assert "🔧" in output
        assert "search_products" in output
        assert "query='laptop'" in output
        assert "limit='10'" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_list(self, mock_stdout):
        """Test tool_result method with list result."""
        test_logger = MCPLogger(level="INFO")
        result = [
            {"name": "Laptop 1", "price": 999},
            {"name": "Laptop 2", "price": 1299},
        ]
        test_logger.tool_result(result)

        output = mock_stdout.getvalue()
        assert "✅" in output
        assert "Encontrados 2 elementos" in output
        assert "Laptop 1" in output
        assert "Laptop 2" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_long_list(self, mock_stdout):
        """Test tool_result method with long list (more than 3 items)."""
        test_logger = MCPLogger(level="INFO")
        result = [{"name": f"Item {i}"} for i in range(5)]
        test_logger.tool_result(result)

        output = mock_stdout.getvalue()
        assert "Encontrados 5 elementos" in output
        assert "... y 2 más" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_dict(self, mock_stdout):
        """Test tool_result method with dict result."""
        test_logger = MCPLogger(level="INFO")
        result = {"name": "Gaming Laptop", "price": 1299}
        test_logger.tool_result(result)

        output = mock_stdout.getvalue()
        assert "✅" in output
        assert "Gaming Laptop" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_dict_with_sku(self, mock_stdout):
        """Test tool_result method with dict containing SKU."""
        test_logger = MCPLogger(level="INFO")
        result = {"sku": "LAPTOP-001", "price": 999}
        test_logger.tool_result(result)

        output = mock_stdout.getvalue()
        assert "LAPTOP-001" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_string(self, mock_stdout):
        """Test tool_result method with string result."""
        test_logger = MCPLogger(level="INFO")
        test_logger.tool_result("Simple string result")

        output = mock_stdout.getvalue()
        assert "Simple string result" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_long_string(self, mock_stdout):
        """Test tool_result method with long string (truncation)."""
        test_logger = MCPLogger(level="INFO")
        long_string = "x" * 150
        test_logger.tool_result(long_string)

        output = mock_stdout.getvalue()
        assert "..." in output
        assert len(output) < len(long_string)

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_with_tool_name(self, mock_stdout):
        """Test tool_result method with tool name context."""
        test_logger = MCPLogger(level="INFO")
        test_logger.tool_result("result", tool_name="search")

        output = mock_stdout.getvalue()
        assert "[search]" in output


class TestMCPLoggerMCPMethods:
    """Test suite for MCP-specific logging methods."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_mcp_connect(self, mock_stdout):
        """Test mcp_connect method."""
        test_logger = MCPLogger(level="INFO")
        test_logger.mcp_connect("ProductsServer", 5)

        output = mock_stdout.getvalue()
        assert "📡" in output
        assert "ProductsServer" in output
        assert "5" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_mcp_error_without_context(self, mock_stdout):
        """Test mcp_error method without context."""
        test_logger = MCPLogger(level="ERROR")
        test_logger.mcp_error("Connection failed")

        output = mock_stdout.getvalue()
        assert "❌" in output
        assert "[MCP]" in output
        assert "Connection failed" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_mcp_error_with_context(self, mock_stdout):
        """Test mcp_error method with context."""
        test_logger = MCPLogger(level="ERROR")
        test_logger.mcp_error("Timeout", context="tool_call")

        output = mock_stdout.getvalue()
        assert "[tool_call]" in output
        assert "Timeout" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_startup_banner(self, mock_stdout):
        """Test startup_banner method."""
        test_logger = MCPLogger(level="INFO")
        test_logger.startup_banner("Odiseo Bot", "2.0.0")

        output = mock_stdout.getvalue()
        assert "🤖" in output
        assert "Odiseo Bot" in output
        assert "2.0.0" in output
        assert "═" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_startup_banner_default_version(self, mock_stdout):
        """Test startup_banner with default version."""
        test_logger = MCPLogger(level="INFO")
        test_logger.startup_banner("Test App")

        output = mock_stdout.getvalue()
        assert "1.0.0" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_separator(self, mock_stdout):
        """Test separator method with default parameters."""
        test_logger = MCPLogger(level="INFO")
        test_logger.separator()

        output = mock_stdout.getvalue()
        assert "─" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_separator_custom_char(self, mock_stdout):
        """Test separator method with custom character."""
        test_logger = MCPLogger(level="INFO")
        test_logger.separator(char="=", length=30)

        output = mock_stdout.getvalue()
        assert "=" in output


class TestGlobalLogger:
    """Test suite for global logger instance."""

    def test_global_logger_exists(self):
        """Test global logger instance exists."""
        assert logger is not None
        assert isinstance(logger, MCPLogger)

    def test_global_logger_usable(self):
        """Test global logger instance is usable."""
        # Should not raise any errors
        with patch("sys.stdout", new_callable=StringIO):
            logger.info("Test message")


class TestGetLoggerFactory:
    """Test suite for get_logger factory function."""

    def test_get_logger_default(self):
        """Test get_logger with default parameters."""
        test_logger = get_logger()
        assert isinstance(test_logger, MCPLogger)
        assert test_logger.logger.name == "client_mcp"

    def test_get_logger_custom_name(self):
        """Test get_logger with custom name."""
        test_logger = get_logger(name="custom_logger")
        assert test_logger.logger.name == "custom_logger"

    def test_get_logger_custom_level(self):
        """Test get_logger with custom level."""
        test_logger = get_logger(level="DEBUG")
        assert test_logger.logger.level == logging.DEBUG

    def test_get_logger_returns_new_instance(self):
        """Test get_logger returns new instance each time."""
        logger1 = get_logger(name="logger1")
        logger2 = get_logger(name="logger2")
        assert logger1 is not logger2


class TestLoggerEdgeCases:
    """Test suite for edge cases and special scenarios."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_empty_tool_result_list(self, mock_stdout):
        """Test tool_result with empty list."""
        test_logger = MCPLogger(level="INFO")
        test_logger.tool_result([])

        output = mock_stdout.getvalue()
        assert "Encontrados 0 elementos" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_dict_without_name_or_sku(self, mock_stdout):
        """Test tool_result with dict without name or sku."""
        test_logger = MCPLogger(level="INFO")
        result = {"price": 999, "stock": 10}
        test_logger.tool_result(result)

        output = mock_stdout.getvalue()
        assert "Elemento" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_tool_result_list_with_non_dict_items(self, mock_stdout):
        """Test tool_result with list of non-dict items."""
        test_logger = MCPLogger(level="INFO")
        test_logger.tool_result([1, 2, 3, 4, 5])

        output = mock_stdout.getvalue()
        assert "Encontrados 5 elementos" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_multiple_handlers_removed(self, mock_stdout):
        """Test that existing handlers are removed during init."""
        # Create logger with handler
        test_logger = MCPLogger()
        initial_handler_count = len(test_logger.logger.handlers)

        # Recreate logger with same name
        test_logger2 = MCPLogger()

        # Should still have only 1 handler
        assert len(test_logger2.logger.handlers) == initial_handler_count

    @patch("sys.stdout", new_callable=StringIO)
    def test_logger_level_filtering(self, mock_stdout):
        """Test log level filtering works correctly."""
        # Logger set to WARNING, debug/info should not appear
        test_logger = MCPLogger(level="WARNING")
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")

        output = mock_stdout.getvalue()
        assert "Debug message" not in output
        assert "Info message" not in output
        assert "Warning message" in output
