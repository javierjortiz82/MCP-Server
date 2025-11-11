import asyncio

from tools.fuzzy_search import fuzzy_search_smart


async def test():
    result = fuzzy_search_smart("rompecabezas", limit=5)
    for _item in result:
        pass


asyncio.run(test())
