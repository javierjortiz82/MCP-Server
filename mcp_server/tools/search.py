from config import settings
from utils.db import fetchall
from utils.embeddings import emb_client
from utils.logger import setup_logging

# Setup logger for search operations
logger = setup_logging("mcp_tools_search")


def search_products(query: str, k: int = 5) -> list[dict]:
    """
    Semantic product search using vector embeddings (Google Gemini embedding-001).

    Performs AI-powered conceptual search by converting the query into a 1536-dimensional
    vector and finding products with similar semantic meaning (not just keyword matching).

    Implementation:
    - Generates query embedding using Google Gemini embedding-001
    - Uses PostgreSQL pgvector extension with <-> (L2 distance) operator
    - Searches indexed embedding column (vector(1536) type)
    - Returns products ordered by semantic similarity

    Use cases:
    - Conceptual queries: "something to automatically clean"
    - Need-based searches: "work from home professionally"
    - Benefit/purpose queries: "protect my phone from drops"

    Performance: ~490ms average (embedding generation + vector search)

    Args:
        query: Conceptual search query describing need, benefit, or use case
        k: Number of top results to return (default: 5)

    Returns:
        List of product dicts ordered by similarity (closest first)
        Each dict: {id, sku, name, description, category, brand, tags, color, size, price}
        Note: 'distance' field is removed from results (internal use only)

    Raises:
        Exception: If embedding generation fails or database error occurs
    """
    logger.info("Starting vector search for query: '%s' (k=%d)", query, k)

    vectors = emb_client.embed([query])
    if not vectors:
        logger.warning("Could not generate embeddings for query")
        return []

    qvec = vectors[0]
    logger.debug("Vector generated for query (dimension: %d)", len(qvec))

    sql = (
        f"SELECT id, sku, name, description, category, brand, tags, color, size, price,"
        f" embedding <-> %s AS distance"
        f" FROM {settings.SCHEMA_NAME}.products"
        f" WHERE embedding IS NOT NULL"
        f" ORDER BY embedding <-> %s"
        f" LIMIT %s"
    )

    try:
        # Convert float list to pgvector string format
        qvec_str = "[" + ",".join(map(str, qvec)) + "]"

        # Pass qvec as string twice
        rows = fetchall(sql, (qvec_str, qvec_str, k))
        logger.info("Vector search completed: %d results found", len(rows))

        # Don't expose embedding in results
        for r in rows:
            r.pop("distance", None)
        return rows
    except Exception as e:
        logger.error("Error in vector search: %s", e)
        raise
