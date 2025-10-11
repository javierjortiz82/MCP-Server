import asyncio

from tools.fuzzy_search import fuzzy_search_smart


async def test():
    result = fuzzy_search_smart("rompecabezas", limit=5)
    print("Fuzzy search result for 'rompecabezas':")
    for item in result:
        print(
            f"  SKU: {item.get('sku')}, Name: {item.get('name')}, Description: {item.get('description')}"
        )


asyncio.run(test())
