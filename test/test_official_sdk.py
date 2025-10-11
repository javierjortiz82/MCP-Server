#!/usr/bin/env python3
"""
Test MCP Connector Integration

Tests the MCP Connector using official Anthropic MCP SDK.
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client_mcp.core.mcp_connector import MCPConnector


async def test_connection():
    """Test basic connection to MCP server."""
    print("🔍 Test 1: Conexión al servidor MCP...")

    try:
        async with MCPConnector("http://localhost:8009/mcp"):
            print("  ✅ Conexión exitosa")
            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_list_tools():
    """Test listing MCP tools."""
    print("\n🔍 Test 2: Listar herramientas MCP...")

    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            tools = await client.list_tools()
            print(f"  ✅ Encontradas {len(tools)} herramientas:")

            for i, tool in enumerate(tools, 1):
                print(f"     {i}. {tool['name']}: {tool['description'][:60]}...")

            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_call_tool():
    """Test calling an MCP tool."""
    print("\n🔍 Test 3: Llamar herramienta MCP...")

    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            # Test search_products tool
            result = await client.call_tool(
                "search_products", {"query": "laptop", "k": 3}
            )

            if result:
                if isinstance(result, list):
                    print(f"  ✅ Resultado: {len(result)} productos encontrados")
                    for i, item in enumerate(result[:3], 1):
                        if isinstance(item, dict):
                            name = item.get("name", "N/A")
                            print(f"     {i}. {name}")
                else:
                    print(f"  ✅ Resultado: {result}")
            else:
                print("  ⚠️  Sin resultados")

            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_list_resources():
    """Test listing MCP resources."""
    print("\n🔍 Test 4: Listar recursos MCP...")

    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            resources = await client.list_resources()

            if resources:
                print(f"  ✅ Encontrados {len(resources)} recursos:")
                for i, resource in enumerate(resources, 1):
                    print(f"     {i}. {resource['uri']}: {resource['name']}")
            else:
                print("  ℹ️  Sin recursos disponibles")

            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_list_prompts():
    """Test listing MCP prompts."""
    print("\n🔍 Test 5: Listar prompts MCP...")

    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            prompts = await client.list_prompts()

            if prompts:
                print(f"  ✅ Encontrados {len(prompts)} prompts:")
                for i, prompt in enumerate(prompts, 1):
                    print(
                        f"     {i}. {prompt['name']}: {prompt['description'][:50]}..."
                    )
            else:
                print("  ℹ️  Sin prompts disponibles")

            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Test Suite - Official MCP SDK")
    print("=" * 60)

    results = []

    # Run tests
    results.append(await test_connection())
    results.append(await test_list_tools())
    results.append(await test_call_tool())
    results.append(await test_list_resources())
    results.append(await test_list_prompts())

    # Summary
    print("\n" + "=" * 60)
    print("📊 Resumen de Tests")
    print("=" * 60)

    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100

    print(f"✅ Exitosos: {passed}/{total}")
    print(f"❌ Fallidos: {total - passed}/{total}")
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")

    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron! SDK oficial funcionando correctamente.")
    else:
        print(
            f"\n⚠️  {total - passed} test(s) fallaron. Verifica la conexión al servidor MCP."
        )


if __name__ == "__main__":
    print(
        "\n💡 Nota: Asegúrate de que el servidor MCP esté corriendo en localhost:8009\n"
    )

    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n👋 Tests interrumpidos por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error ejecutando tests: {e}")
        sys.exit(1)
