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
    - Conceptual queries: "algo para limpiar automáticamente"
    - Need-based searches: "trabajar desde casa profesionalmente"
    - Benefit/purpose queries: "proteger mi celular de caídas"

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
    logger.info("Iniciando búsqueda vectorial para query: '%s' (k=%d)", query, k)

    vectors = emb_client.embed([query])
    if not vectors:
        logger.warning("No se pudieron generar embeddings para la query")
        return []

    qvec = vectors[0]
    logger.debug("Vector generado para query (dimensión: %d)", len(qvec))

    sql = (
        f"SELECT id, sku, name, description, category, brand, tags, color, size, price,"
        f" embedding <-> %s AS distance"
        f" FROM {settings.SCHEMA_NAME}.products"
        f" WHERE embedding IS NOT NULL"
        f" ORDER BY embedding <-> %s"
        f" LIMIT %s"
    )

    try:
        # Convertir lista de floats a string formato pgvector
        qvec_str = "[" + ",".join(map(str, qvec)) + "]"

        # Pasamos qvec como string dos veces
        rows = fetchall(sql, (qvec_str, qvec_str, k))
        logger.info("Búsqueda vectorial completada: %d resultados encontrados", len(rows))

        # No exponer embedding en resultados
        for r in rows:
            r.pop("distance", None)
        return rows
    except Exception as e:
        logger.error("Error en búsqueda vectorial: %s", e)
        raise
