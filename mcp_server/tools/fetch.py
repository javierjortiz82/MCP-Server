from config import settings
from utils.db import fetchone
from utils.logger import setup_logging

# Setup logger for fetch operations
logger = setup_logging("mcp_tools_fetch")


def fetch_by_sku(sku: str) -> dict | None:
    """
    Fetch a single product by exact SKU (Stock Keeping Unit) code.

    Performs direct database lookup using exact SKU matching. This is the fastest
    search method (~9ms average) and should be used when the client explicitly
    mentions a product code.

    Use cases:
    - "quiero el TOY-0018"
    - "busco el producto COMP-0038"
    - "dame información del SKU HOME-0007"

    Performance: ~9ms average (direct indexed lookup)

    Args:
        sku: Exact product SKU code (case-sensitive)
             Format examples: COMP-0009, TOY-0018, HOME-0007, AUTO-0016

    Returns:
        Product dict if found, None if not found
        Dict contains: {id, sku, name, description, category, brand, tags, color, size, price}

    Example:
        >>> fetch_by_sku("TOY-0018")
        {'id': 18, 'sku': 'TOY-0018', 'name': 'Puzzle 1000 Piezas', ...}
        >>> fetch_by_sku("INVALID-SKU")
        None
    """
    logger.debug("Buscando producto por SKU: %s", sku)
    sql = (
        f"SELECT id, sku, name, description, category, brand, tags, color, size, price "
        f"FROM {settings.SCHEMA_NAME}.products WHERE sku = %s"
    )
    result = fetchone(sql, (sku,))
    if result:
        logger.debug("Producto encontrado por SKU %s: ID=%s", sku, result.get("id"))
    else:
        logger.warning("No se encontró producto con SKU: %s", sku)
    return result


def fetch_by_id(product_id: int) -> dict | None:
    """
    Fetch a single product by internal database ID.

    Performs direct database lookup using the product's primary key ID. Similar to
    fetch_by_sku but uses numeric ID instead of SKU code. Rarely used by end clients
    (they typically reference SKU codes), but useful for internal operations.

    Performance: ~9ms average (direct primary key lookup)

    Args:
        product_id: Database primary key ID (integer)

    Returns:
        Product dict if found, None if not found
        Dict contains: {id, sku, name, description, category, brand, tags, color, size, price}

    Example:
        >>> fetch_by_id(18)
        {'id': 18, 'sku': 'TOY-0018', 'name': 'Puzzle 1000 Piezas', ...}
        >>> fetch_by_id(9999)
        None
    """
    logger.debug("Buscando producto por ID: %s", product_id)
    sql = (
        f"SELECT id, sku, name, description, category, brand, tags, color, size, price "
        f"FROM {settings.SCHEMA_NAME}.products WHERE id = %s"
    )
    result = fetchone(sql, (product_id,))
    if result:
        logger.debug("Producto encontrado por ID %s: SKU=%s", product_id, result.get("sku"))
    else:
        logger.warning("No se encontró producto con ID: %s", product_id)
    return result
