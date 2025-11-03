#!/usr/bin/env python3
"""MCP Connector - Official Client using Anthropic SDK.

This module provides a connector to MCP servers using the official Anthropic SDK
for full compliance with MCP specifications.
"""

from pathlib import Path
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Observability imports (OPCIÓN 8)
try:
    from email_service.observability.metrics import get_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

# Explicit import to avoid sys.path conflicts across different modules
# (agent/__init__.py manipulates sys.path, potentially loading wrong settings)
try:
    from importlib.util import spec_from_file_location, module_from_spec

    settings_path = Path(__file__).parent.parent / "config" / "settings.py"
    spec = spec_from_file_location("client_mcp_settings_connector", settings_path)
    if spec and spec.loader:
        _settings_module = module_from_spec(spec)
        spec.loader.exec_module(_settings_module)
        settings = _settings_module.settings
    else:
        raise ImportError("Failed to load settings module")
except (ImportError, AttributeError):
    # Fallback: try standard import
    from config.settings import settings


class MCPConnector:
    """MCP Connector - Official client using Anthropic SDK.

    This connector provides full compliance with MCP specifications by using
    the official SDK instead of custom JSON-RPC implementation.

    Example:
        async with MCPConnector("http://localhost:8009/mcp") as connector:
            tools = await connector.list_tools()
            result = await connector.call_tool("search", {"query": "laptop"})
    """

    def __init__(self, url: str | None = None):
        """Initialize MCP connector.

        Args:
            url: MCP server URL (defaults to settings.mcp_base_url)
        """
        # Initialize observability (OPCIÓN 8)
        if OBSERVABILITY_AVAILABLE:
            self.structured_logger = get_structured_logger("mcp_connector")
            self.metrics = get_metrics_collector()
        else:
            self.structured_logger = None
            self.metrics = None

        self.url = url or settings.mcp_base_url
        self.session: ClientSession | None = None
        self.streams: Any = None  # Type from streamablehttp_client context manager
        self.session_ctx: Any = None  # Type from ClientSession context manager

        if self.structured_logger:
            self.structured_logger.info("MCP connector initialized", url=self.url)

    @staticmethod
    async def check_server_health(base_url: str) -> dict[str, Any]:
        """Check MCP server health status.

        Args:
            base_url: Base URL of MCP server (e.g., http://localhost:8009)

        Returns:
            Health status dict with detailed information

        Example response:
            {
                "status": "healthy",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "product_count": 50,
                        "extensions": ["pg_trgm", "unaccent", "vector"]
                    }
                }
            }
        """
        # Track health check with metrics (OPCIÓN 8)
        metrics = None
        logger = None

        # Try to get observability components for health check tracking
        if OBSERVABILITY_AVAILABLE:
            try:
                metrics = get_metrics_collector()
                logger = get_structured_logger("mcp_health_check")
            except Exception:
                pass

        # Extract base URL from MCP endpoint
        if base_url.endswith("/mcp"):
            base_url = base_url[:-4]

        health_url = f"{base_url}/health"

        try:
            if metrics:
                latency_ctx = metrics.record_latency("mcp_health_check_latency")
                latency_ctx.__enter__()
            else:
                latency_ctx = None

            async with httpx.AsyncClient(timeout=settings.MCP_HEALTH_CHECK_TIMEOUT) as client:
                response = await client.get(health_url)
                health_status = response.json()

            if metrics:
                metrics.increment_counter("mcp_health_check_success", 1)
                # Track health status
                if health_status.get("status") == "healthy":
                    metrics.increment_counter("mcp_server_healthy", 1)
                else:
                    metrics.increment_counter("mcp_server_unhealthy", 1)

            if logger:
                logger.info(
                    "Health check completed",
                    url=health_url,
                    status=health_status.get("status"),
                )

            return health_status

        except httpx.RequestError as e:
            if metrics:
                metrics.increment_counter("mcp_health_check_failure", 1)
                metrics.increment_counter("mcp_server_unreachable", 1)
            if logger:
                logger.warning("Health check failed - server unreachable", url=health_url)

            return {
                "status": "unreachable",
                "error": f"Cannot connect to server: {str(e)}",
                "url": health_url,
            }

        except Exception as e:
            if metrics:
                metrics.increment_counter("mcp_health_check_failure", 1)
            if logger:
                logger.exception("Health check failed", url=health_url)

            return {"status": "error", "error": str(e), "url": health_url}

        finally:
            if latency_ctx:
                latency_ctx.__exit__(None, None, None)

    async def __aenter__(self):
        """Async context manager entry."""
        # Connect to MCP server using official transport
        self.streams = streamablehttp_client(self.url)
        stream_tuple = await self.streams.__aenter__()

        # Unpack the three return values from streamablehttp_client
        read_stream, write_stream, get_session_id = stream_tuple

        # Create official ClientSession
        self.session_ctx = ClientSession(read_stream, write_stream)
        self.session = await self.session_ctx.__aenter__()

        # Initialize session with server
        await self.session.initialize()

        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self.session_ctx:
            await self.session_ctx.__aexit__(*args)
        if self.streams:
            await self.streams.__aexit__(*args)

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available MCP tools using official SDK.

        Returns:
            List of tool definitions with name, description, and inputSchema

        Raises:
            RuntimeError: If session is not initialized
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")

        # Track tool discovery with metrics (OPCIÓN 8)
        try:
            if self.metrics:
                latency_ctx = self.metrics.record_latency_async("mcp_list_tools_latency")
            else:
                latency_ctx = None

            if latency_ctx:
                await latency_ctx.__aenter__()

            result = await self.session.list_tools()

            # Convert official Tool objects to dict format
            tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema,
                }
                for tool in result.tools
            ]

            # Track successful tool discovery
            if self.metrics:
                self.metrics.increment_counter("mcp_list_tools_success", 1)
                self.metrics.set_gauge("mcp_tools_available", len(tools))

            if self.structured_logger:
                self.structured_logger.info(
                    "Tools listed successfully",
                    tool_count=len(tools),
                    tool_names=[t["name"] for t in tools],
                )

            return tools

        except Exception as e:
            if self.metrics:
                self.metrics.increment_counter("mcp_list_tools_failure", 1)
            if self.structured_logger:
                self.structured_logger.exception("Failed to list tools")
            raise

        finally:
            if latency_ctx:
                await latency_ctx.__aexit__(None, None, None)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool using official SDK.

        Args:
            name: Tool name
            arguments: Tool arguments as dictionary

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If session is not initialized
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")

        # Track tool execution with metrics (OPCIÓN 8)
        try:
            if self.metrics:
                latency_ctx = self.metrics.record_latency_async(
                    "mcp_tool_call_latency", tags={"tool": name}
                )
            else:
                latency_ctx = None

            if latency_ctx:
                await latency_ctx.__aenter__()

            # Track tool call attempt
            if self.metrics:
                self.metrics.increment_counter(f"mcp_tool_call_attempt_{name}", 1)

            result = await self.session.call_tool(name=name, arguments=arguments)

            # Extract content from official response
            if result.content and len(result.content) > 0:
                first_content = result.content[0]
                # Handle TextContent type
                if hasattr(first_content, "text"):
                    # Try to parse as JSON
                    try:
                        import json

                        response_data = json.loads(first_content.text)
                    except (json.JSONDecodeError, ValueError):
                        response_data = first_content.text
                else:
                    response_data = first_content
            else:
                response_data = None

            # Track successful tool execution
            if self.metrics:
                self.metrics.increment_counter(f"mcp_tool_call_success_{name}", 1)

            if self.structured_logger:
                self.structured_logger.info(
                    "Tool called successfully",
                    tool=name,
                    arguments_keys=list(arguments.keys()) if arguments else [],
                )

            return response_data

        except Exception as e:
            if self.metrics:
                self.metrics.increment_counter(f"mcp_tool_call_failure_{name}", 1)
                self.metrics.increment_counter(f"mcp_tool_error_{type(e).__name__}", 1)
            if self.structured_logger:
                self.structured_logger.exception("Tool execution failed", tool=name)
            raise

        finally:
            if latency_ctx:
                await latency_ctx.__aexit__(None, None, None)

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available MCP resources using official SDK.

        Returns:
            List of resource definitions

        Raises:
            RuntimeError: If session is not initialized
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")

        result = await self.session.list_resources()

        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": getattr(resource, "mimeType", None),
            }
            for resource in result.resources
        ]

    async def read_resource(self, uri: str) -> Any:
        """Read an MCP resource using official SDK.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            RuntimeError: If session is not initialized
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")

        # Note: MCP SDK type hint expects AnyUrl but accepts str in practice
        result = await self.session.read_resource(uri=uri)  # type: ignore[arg-type]

        if result.contents:
            return result.contents[0] if len(result.contents) > 0 else None

        return None

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List available MCP prompts using official SDK.

        Returns:
            List of prompt definitions

        Raises:
            RuntimeError: If session is not initialized
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")

        result = await self.session.list_prompts()

        return [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": getattr(prompt, "arguments", []),
            }
            for prompt in result.prompts
        ]

    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None) -> Any:
        """Get an MCP prompt using official SDK.

        Args:
            name: Prompt name
            arguments: Optional prompt arguments

        Returns:
            Prompt content

        Raises:
            RuntimeError: If session is not initialized
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")

        result = await self.session.get_prompt(name=name, arguments=arguments or {})

        if result.messages:
            return result.messages

        return None


# Helper function for backward compatibility
async def discover_tools_official(
    url: str = "http://localhost:8009/mcp",
) -> list[dict[str, Any]]:
    """Discover MCP tools using official SDK.

    Args:
        url: MCP server URL

    Returns:
        List of tool definitions
    """
    async with MCPConnector(url) as client:
        return await client.list_tools()
