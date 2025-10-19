"""Enhanced logging utility with emoji support for better UX.

Updated to support both console and file logging with rotation.
"""

import logging
import logging.handlers
import sys
from enum import Enum
from pathlib import Path


class LogLevel(Enum):
    """Log levels with emojis for better visual feedback."""

    DEBUG = "🔍 DEBUG"
    INFO = "ℹ️  INFO"
    WARNING = "⚠️  WARNING"
    ERROR = "❌ ERROR"
    CRITICAL = "🔥 CRITICAL"
    SUCCESS = "✅ SUCCESS"
    TOOL_CALL = "🔧 TOOL_CALL"
    MCP_CONNECT = "📡 MCP_CONNECT"
    MCP_RESPONSE = "📨 MCP_RESPONSE"


class MCPLogger:
    """Enhanced logger with emoji support and strategic debugging features.

    This logger provides enhanced logging capabilities with emoji indicators
    for better visual feedback during development and debugging.

    Features:
    - Console output with emoji indicators (cleaner format)
    - File output with full details (timestamps, line numbers)
    - Automatic log rotation (max 10MB, 5 backups)
    - Configurable log directory
    """

    def __init__(
        self,
        name: str = "client_mcp",
        level: str = "INFO",
        log_to_file: bool = True,
        log_dir: str | Path = "logs",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ):
        """Initialize the MCP logger.

        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Enable file logging (default: True)
            log_dir: Directory for log files (default: "logs")
            max_bytes: Maximum log file size in bytes (default: 10MB)
            backup_count: Number of backup log files to keep (default: 5)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Create console handler with emoji formatter (no timestamp)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Create file handler with full details (timestamp, level, line number)
        if log_to_file:
            # Ensure log directory exists (absolute path)
            log_path = Path(log_dir)
            if not log_path.is_absolute():
                # Resolve relative to client_mcp directory
                log_path = Path(__file__).parent.parent / log_dir
            log_path.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler
            log_file = log_path / f"{name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, level.upper()))

            # File formatter with full details
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        self.logger.propagate = False

    def debug(self, message: str, emoji: str = "🔍") -> None:
        """Log debug message with emoji.

        Args:
            message: Debug message
            emoji: Custom emoji (default: 🔍)
        """
        self.logger.debug(f"{emoji} {message}")

    def info(self, message: str, emoji: str = "ℹ️") -> None:
        """Log info message with emoji.

        Args:
            message: Info message
            emoji: Custom emoji (default: ℹ️)
        """
        self.logger.info(f"{emoji} {message}")

    def warning(self, message: str, emoji: str = "⚠️") -> None:
        """Log warning message with emoji.

        Args:
            message: Warning message
            emoji: Custom emoji (default: ⚠️)
        """
        self.logger.warning(f"{emoji} {message}")

    def error(self, message: str, emoji: str = "❌") -> None:
        """Log error message with emoji.

        Args:
            message: Error message
            emoji: Custom emoji (default: ❌)
        """
        self.logger.error(f"{emoji} {message}")

    def exception(self, message: str, emoji: str = "❌") -> None:
        """Log exception with traceback.

        Args:
            message: Exception message
            emoji: Custom emoji (default: ❌)
        """
        self.logger.exception(f"{emoji} {message}")

    def critical(self, message: str, emoji: str = "🔥") -> None:
        """Log critical message with emoji.

        Args:
            message: Critical message
            emoji: Custom emoji (default: 🔥)
        """
        self.logger.critical(f"{emoji} {message}")

    def success(self, message: str, emoji: str = "✅") -> None:
        """Log success message with emoji.

        Args:
            message: Success message
            emoji: Custom emoji (default: ✅)
        """
        self.logger.info(f"{emoji} {message}")

    def tool_call(self, tool_name: str, **kwargs) -> None:
        """Log MCP tool call with parameters.

        Args:
            tool_name: Name of the MCP tool being called
            **kwargs: Tool parameters
        """
        if kwargs:
            args_str = ", ".join([f"{k}='{v}'" for k, v in kwargs.items()])
            self.logger.info(f"🔧 [MCP] Llamando herramienta: {tool_name}({args_str})")
        else:
            self.logger.info(f"🔧 [MCP] Llamando herramienta: {tool_name}()")

    def tool_result(self, result, tool_name: str | None = None) -> None:
        """Log MCP tool result with smart formatting.

        Args:
            result: Tool execution result
            tool_name: Optional tool name for context
        """
        tool_context = f"[{tool_name}] " if tool_name else ""

        if isinstance(result, list):
            self.logger.info(f"✅ [MCP] {tool_context}Resultado: Encontrados {len(result)} elementos")
            if len(result) > 0 and isinstance(result[0], dict):
                for i, item in enumerate(result[:3], 1):
                    item_name = item.get("name", item.get("sku", f"Item {i}"))
                    self.logger.info(f"   {i}. {item_name}")
                if len(result) > 3:
                    self.logger.info(f"   ... y {len(result) - 3} más")
        elif isinstance(result, dict):
            item_name = result.get("name", result.get("sku", "Elemento"))
            self.logger.info(f"✅ [MCP] {tool_context}Resultado: {item_name}")
        else:
            result_str = str(result)
            truncated = result_str[:100] + ("..." if len(result_str) > 100 else "")
            self.logger.info(f"✅ [MCP] {tool_context}Resultado: {truncated}")

    def mcp_connect(self, server_name: str, tools_count: int) -> None:
        """Log MCP server connection.

        Args:
            server_name: Name of the MCP server
            tools_count: Number of available tools
        """
        self.logger.info(f"📡 Conectado a: {server_name}")
        self.logger.info(f"🔧 Herramientas disponibles: {tools_count}")

    def mcp_error(self, error: str, context: str | None = None) -> None:
        """Log MCP-specific error.

        Args:
            error: Error message
            context: Optional context information
        """
        context_str = f" [{context}]" if context else ""
        self.logger.error(f"❌ [MCP]{context_str} Error: {error}")

    def startup_banner(self, app_name: str, version: str = "1.0.0") -> None:
        """Display startup banner.

        Args:
            app_name: Application name
            version: Application version
        """
        self.logger.info(f"🤖 {app_name} v{version}")
        self.logger.info("═" * 50)

    def separator(self, char: str = "─", length: int = 50) -> None:
        """Print a separator line.

        Args:
            char: Character to use for separator
            length: Length of separator
        """
        self.logger.info(char * length)


# Global logger instance (uses LOG_LEVEL from .env)
def _get_global_logger() -> MCPLogger:
    """Get global logger with LOG_LEVEL from settings."""
    try:
        from importlib.util import spec_from_file_location, module_from_spec

        settings_path = Path(__file__).parent.parent / "config" / "settings.py"
        spec = spec_from_file_location("client_mcp_settings_logger", settings_path)
        if spec and spec.loader:
            _settings_module = module_from_spec(spec)
            spec.loader.exec_module(_settings_module)
            settings = _settings_module.settings
            return MCPLogger(level=settings.LOG_LEVEL)
        else:
            raise ImportError("Failed to load settings module")
    except (ImportError, AttributeError):
        # Fallback if settings not available
        try:
            from config.settings import settings
            return MCPLogger(level=settings.LOG_LEVEL)
        except ImportError:
            return MCPLogger(level="INFO")


logger = _get_global_logger()


def get_logger(name: str = "client_mcp", level: str = "INFO") -> MCPLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        MCPLogger: Configured logger instance
    """
    return MCPLogger(name, level)
