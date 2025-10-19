#!/usr/bin/env python3
"""MCP Connector - Official Client using Anthropic SDK.

This module provides a connector to MCP servers using the official Anthropic SDK
for full compliance with MCP specifications.
"""

from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

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
        self.url = url or settings.mcp_base_url
        self.session: ClientSession | None = None
        self.streams: Any = None  # Type from streamablehttp_client context manager
        self.session_ctx: Any = None  # Type from ClientSession context manager

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
        # Extract base URL from MCP endpoint
        if base_url.endswith("/mcp"):
            base_url = base_url[:-4]

        health_url = f"{base_url}/health"

        try:
            async with httpx.AsyncClient(
                timeout=settings.MCP_HEALTH_CHECK_TIMEOUT
            ) as client:
                response = await client.get(health_url)
                return response.json()
        except httpx.RequestError as e:
            return {
                "status": "unreachable",
                "error": f"Cannot connect to server: {str(e)}",
                "url": health_url,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "url": health_url}

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

        result = await self.session.list_tools()

        # Convert official Tool objects to dict format
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in result.tools
        ]

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

        result = await self.session.call_tool(name=name, arguments=arguments)

        # Extract content from official response
        if result.content and len(result.content) > 0:
            first_content = result.content[0]
            # Handle TextContent type
            if hasattr(first_content, "text"):
                # Try to parse as JSON
                try:
                    import json

                    return json.loads(first_content.text)
                except (json.JSONDecodeError, ValueError):
                    return first_content.text
            return first_content

        return None

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
