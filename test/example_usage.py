#!/usr/bin/env python3
"""Example usage of MCP tools discovery with Google GenAI.
This demonstrates how to discover MCP tools and use them with Google GenAI.
"""

import asyncio
import os

from mcp_discovery import discover_tools, get_mcp_server_info


async def example_discovery():
    """Example of discovering MCP tools and converting to GenAI format."""
    try:
        # 1. Get server information
        await get_mcp_server_info("localhost", 8009)

        # 2. Discover and convert tools
        tools = []
        for tool in await discover_tools("localhost", 8009):
            tools.append(tool)

        # 3. Show detailed tool information
        for _i, tool in enumerate(tools, 1):
            func_decl = tool.function_declarations[0]

            if func_decl.parameters and func_decl.parameters.properties:
                for _param_name, param_info in func_decl.parameters.properties.items():
                    getattr(param_info, "type", "unknown")
                    getattr(param_info, "description", "No description")

        # 4. Example usage with Google GenAI

        return tools

    except Exception:
        return []


async def example_with_genai():
    """Example of using discovered MCP tools with Google GenAI."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return

    try:
        # Import here to avoid import errors if not available
        import google.genai as genai

        # Discover MCP tools
        tools = []
        for tool in await discover_tools("localhost", 8009):
            tools.append(tool)

        if not tools:
            return

        # Create GenAI client with MCP tools
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(model="gemini-2.0-flash-001", tools=tools)

        # Example conversation
        example_query = "Search for products related to 'laptop'"

        chat.send_message(example_query)

    except ImportError:
        pass
    except Exception:
        pass


async def main():
    """Main example function."""
    # Run discovery example
    tools = await example_discovery()

    # Run GenAI integration example
    if tools:
        await example_with_genai()
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
