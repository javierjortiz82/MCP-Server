from config import settings
from utils.db import fetchall
from utils.embeddings import emb_client
from utils.logger import setup_logging

# Observability imports (OPCIÓN 9)
try:
    from email_service.observability.metrics import get_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

# Setup logger for search operations
logger = setup_logging("mcp_tools_search")

# Initialize observability for search (OPCIÓN 9)
if OBSERVABILITY_AVAILABLE:
    structured_logger = get_structured_logger("search_tool")
    metrics = get_metrics_collector()
else:
    structured_logger = None
    metrics = None


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
    try:
        # Track vector search with metrics (OPCIÓN 9)
        if metrics:
            latency_ctx = metrics.record_latency("search_vector_search_latency")
            latency_ctx.__enter__()
        else:
            latency_ctx = None

        if metrics:
            metrics.increment_counter("search_vector_searches_attempted", 1)

        logger.info("Starting vector search for query: '%s' (k=%d)", query, k)

        # Track embedding generation separately (OPCIÓN 9)
        if metrics:
            embed_ctx = metrics.record_latency("search_embedding_generation_latency")
            embed_ctx.__enter__()
        else:
            embed_ctx = None

        try:
            vectors = emb_client.embed([query])
        finally:
            if embed_ctx:
                embed_ctx.__exit__(None, None, None)

        if not vectors:
            logger.warning("Could not generate embeddings for query")
            if metrics:
                metrics.increment_counter("search_embedding_generation_failed", 1)
            return []

        if metrics:
            metrics.increment_counter("search_embedding_generation_successful", 1)

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

            if metrics:
                metrics.increment_counter("search_vector_searches_successful", 1)
                metrics.set_gauge("search_vector_results_count", len(rows))

            if structured_logger:
                structured_logger.info(
                    "Vector search completed",
                    query=query,
                    results_count=len(rows),
                    k=k
                )

            # Don't expose embedding in results
            for r in rows:
                r.pop("distance", None)
            return rows

        except Exception as e:
            if metrics:
                metrics.increment_counter("search_vector_searches_failed", 1)
                metrics.increment_counter(f"search_error_{type(e).__name__}", 1)
            if structured_logger:
                structured_logger.exception("Vector search failed", query=query)
            logger.error("Error in vector search: %s", e)
            raise

    finally:
        if latency_ctx:
            latency_ctx.__exit__(None, None, None)
