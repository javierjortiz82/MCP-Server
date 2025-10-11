from tools.search import search_products

result = search_products("rompecabezas", k=5)
print("Semantic search result for 'rompecabezas':")
for item in result:
    print(
        f"  SKU: {item.get('sku')}, Name: {item.get('name')}, Similarity: {item.get('similarity')}"
    )
