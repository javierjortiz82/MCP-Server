from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from config import settings
from utils.logger import setup_logging

# Setup logger for database operations
logger = setup_logging("mcp_db")


_pool = None


def init_db(minconn: int = 1, maxconn: int = 5) -> None:
    """Initialize database connection pool and register pgvector type.

    Creates a PostgreSQL connection pool and registers the pgvector extension
    to enable vector operations for embeddings storage and similarity search.
    This function should be called once during application startup.

    Args:
        minconn: Minimum number of connections in the pool (default: 1)
        maxconn: Maximum number of connections in the pool (default: 5)

    Raises:
        Exception: If vector type registration fails or database connection fails

    Example:
        >>> init_db()  # Use defaults
        >>> init_db(minconn=2, maxconn=10)  # Custom pool size
    """
    global _pool
    if _pool is None:
        logger.info("Inicializando pool de conexiones a base de datos...")
        _pool = SimpleConnectionPool(minconn, maxconn, dsn=settings.DATABASE_URL)
        # register vector adapter on a temporary connection
        conn = _pool.getconn()
        try:
            register_vector(conn)
            conn.commit()
            logger.info("Tipo vector registrado correctamente en PostgreSQL")
        except Exception as e:
            logger.error("Error al registrar tipo vector: %s", e)
            raise
        finally:
            _pool.putconn(conn)
        logger.info("Pool de conexiones inicializado exitosamente")


@contextmanager
def get_conn() -> Iterator[psycopg2.extensions.connection]:
    """Context manager that provides a database connection from the pool.

    Yields a connection with autocommit disabled. The caller is responsible for
    committing, rolling back, or closing the connection as needed. The connection
    is automatically returned to the pool when the context exits.

    Yields:
        psycopg2.extensions.connection: Database connection from the pool

    Raises:
        AssertionError: If pool initialization fails (should never happen due to init check)

    Example:
        >>> with get_conn() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT * FROM products")
        ...     conn.commit()
    """
    if _pool is None:
        init_db()
    assert _pool is not None  # For type checker
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


def fetchone(query: str, params: tuple[Any, ...] = ()) -> dict | None:
    """Execute a query and return a single row as a dictionary.

    Args:
        query: SQL query string (can include %s placeholders)
        params: Tuple of parameters for query placeholders (default: empty tuple)

    Returns:
        Dictionary with column names as keys and values, or None if no row found

    Example:
        >>> result = fetchone("SELECT * FROM products WHERE id = %s", (42,))
        >>> if result:
        ...     print(result['name'])
    """
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def fetchall(query: str, params: tuple[Any, ...] = ()) -> list[dict]:
    """Execute a query and return all rows as a list of dictionaries.

    Args:
        query: SQL query string (can include %s placeholders)
        params: Tuple of parameters for query placeholders (default: empty tuple)

    Returns:
        List of dictionaries, each representing a row with column names as keys

    Example:
        >>> results = fetchall("SELECT * FROM products WHERE category = %s", ("Electronics",))
        >>> for product in results:
        ...     print(product['name'], product['price'])
    """
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    """Execute a query without returning results (INSERT, UPDATE, DELETE, etc.).

    Automatically commits the transaction after successful execution.

    Args:
        query: SQL query string (can include %s placeholders)
        params: Tuple of parameters for query placeholders (default: empty tuple)

    Raises:
        Exception: If query execution fails, transaction will be rolled back automatically

    Example:
        >>> execute("UPDATE products SET price = %s WHERE id = %s", (99.99, 42))
        >>> execute("DELETE FROM products WHERE sku = %s", ("OLD-001",))
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        conn.commit()


def upsert_product(product: dict) -> None:
    """Insert or update a product in the database.

    Uses PostgreSQL's INSERT ... ON CONFLICT to perform an "upsert" operation.
    If a product with the same SKU exists, it updates all fields except embedding
    (only updates embedding if new value is not None).

    Args:
        product: Dictionary containing product data with keys:
                 - sku (str, required): Stock Keeping Unit, unique identifier
                 - name (str): Product name
                 - description (str): Product description
                 - category (str): Product category
                 - brand (str): Product brand
                 - tags (str): Product tags
                 - color (str): Product color
                 - size (str): Product size
                 - price (float): Product price
                 - embedding (list[float] | None): Vector embedding for semantic search

    Raises:
        Exception: If database operation fails

    Example:
        >>> product = {
        ...     "sku": "LAPTOP-001",
        ...     "name": "Gaming Laptop",
        ...     "price": 1299.99,
        ...     "category": "Electronics",
        ...     "embedding": [0.1, 0.2, ...]  # 1536-dim vector
        ... }
        >>> upsert_product(product)
    """
    sql = f"""
    INSERT INTO {settings.SCHEMA_NAME}.products
        (sku, name, description, category, brand, tags, color, size, price, embedding)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (sku) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        category = EXCLUDED.category,
        brand = EXCLUDED.brand,
        tags = EXCLUDED.tags,
        color = EXCLUDED.color,
        size = EXCLUDED.size,
        price = EXCLUDED.price,
        embedding = COALESCE(EXCLUDED.embedding, {settings.SCHEMA_NAME}.products.embedding)
    ;
    """
    params = (
        product.get("sku"),
        product.get("name"),
        product.get("description"),
        product.get("category"),
        product.get("brand"),
        product.get("tags"),
        product.get("color"),
        product.get("size"),
        product.get("price"),
        product.get("embedding"),
    )
    execute(sql, params)
