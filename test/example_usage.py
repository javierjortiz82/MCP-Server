#!/usr/bin/env python3
"""
Example usage of MCP tools discovery with Google GenAI.
This demonstrates how to discover MCP tools and use them with Google GenAI.
"""

import asyncio
import os

from mcp_discovery import discover_tools, get_mcp_server_info


async def example_discovery():
    """Example of discovering MCP tools and converting to GenAI format."""
    try:
        print("=" * 60)
        print("🔍 MCP TOOLS DISCOVERY EXAMPLE")
        print("=" * 60)

        # 1. Get server information
        print("\n📊 Getting MCP server information...")
        server_info = await get_mcp_server_info("localhost", 8009)

        print(f"Server Name: {server_info['server_info'].get('name', 'Unknown')}")
        print(f"Protocol Version: {server_info['protocol_version']}")
        print(f"Tools Available: {server_info['tools_count']}")
        print(f"Tool Names: {', '.join(server_info['available_tools'])}")

        # 2. Discover and convert tools
        print("\n🔧 Discovering MCP tools...")
        tools = []
        for tool in await discover_tools("localhost", 8009):
            tools.append(tool)

        print(f"✅ Successfully converted {len(tools)} tools to Google GenAI format")

        # 3. Show detailed tool information
        print("\n📋 Tool Details:")
        for i, tool in enumerate(tools, 1):
            func_decl = tool.function_declarations[0]
            print(f"\n{i}. Tool: {func_decl.name}")
            print(f"   Description: {func_decl.description}")

            if func_decl.parameters and func_decl.parameters.properties:
                print("   Parameters:")
                for param_name, param_info in func_decl.parameters.properties.items():
                    param_type = getattr(param_info, "type", "unknown")
                    param_desc = getattr(param_info, "description", "No description")
                    print(f"     - {param_name} ({param_type}): {param_desc}")

        # 4. Example usage with Google GenAI
        print("\n🚀 Example usage with Google GenAI:")
        print(
            """
# Import the discovery function
from mcp_discovery import discover_tools
from google.genai import types

# Discover tools
async def setup_genai_with_mcp_tools():
    # Discover MCP tools as Python functions
    tools = await discover_tools("localhost", 8009)

    # Use with Google GenAI client
    import google.genai as genai
    client = genai.Client(api_key="your-api-key")

    # Create config with the discovered functions
    config = types.GenerateContentConfig(tools=tools)
    chat = client.chats.create(
        model="gemini-2.0-flash-001",
        config=config
    )

    return chat, tools
        """
        )

        return tools

    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        return []


async def example_with_genai():
    """Example of using discovered MCP tools with Google GenAI."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️ GOOGLE_API_KEY not set. Skipping GenAI example.")
        return

    try:
        print("\n" + "=" * 60)
        print("🤖 GOOGLE GENAI + MCP TOOLS EXAMPLE")
        print("=" * 60)

        # Import here to avoid import errors if not available
        import google.genai as genai

        # Discover MCP tools
        tools = []
        for tool in await discover_tools("localhost", 8009):
            tools.append(tool)

        if not tools:
            print("No MCP tools discovered. Cannot proceed with GenAI example.")
            return

        # Create GenAI client with MCP tools
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(model="gemini-2.0-flash-001", tools=tools)

        print(f"✅ Created GenAI chat with {len(tools)} MCP tools")

        # Example conversation
        example_query = "Search for products related to 'laptop'"
        print(f"\n🔍 Example query: '{example_query}'")

        response = chat.send_message(example_query)
        print(f"🤖 Response: {response.text[:200]}...")

    except ImportError:
        print("⚠️ google-genai not installed. Install with: pip install google-genai")
    except Exception as e:
        print(f"❌ Error with GenAI example: {e}")


async def main():
    """Main example function."""
    print("🚀 Starting MCP Tools Discovery Example")

    # Run discovery example
    tools = await example_discovery()

    # Run GenAI integration example
    if tools:
        await example_with_genai()
    else:
        print("\n⚠️ No tools discovered. Skipping GenAI example.")

    print("\n✨ Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
