"""
Fuzzy Search Tool using PostgreSQL pg_trgm and unaccent extensions

This module implements accent-insensitive fuzzy text search capabilities using:
- pg_trgm: Trigram similarity for typo tolerance
- unaccent: Accent removal for Unicode normalization
- normalize_text(): Custom function for case/accent normalization

Features:
- Typo-tolerant search: "licuadora" matches "licu4dora"
- Accent-insensitive: "camara" matches "cámara"
- Case-insensitive: "CAMARA" matches "cámara"

Designed to complement semantic search with exact/approximate text matching.
"""

from config import settings
from utils.db import fetchall
from utils.logger import setup_logging
from utils.i18n import t

# Setup logger for fuzzy search operations
logger = setup_logging("mcp_tools_fuzzy_search")


def fuzzy_search(
    query: str,
    fields: list[str] | None = None,
    min_similarity: float = 0.3,
    limit: int = 20,
    include_similarity: bool = True,
) -> list[dict]:
    """
    Performs fuzzy text search using PostgreSQL pg_trgm extension.

    Args:
        query: Search term to match against
        fields: List of fields to search in ['name', 'description', 'brand', 'category']
                Default: ['name', 'description']
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
                       Default: 0.3 (30% similarity)
        limit: Maximum number of results to return
        include_similarity: Whether to include similarity scores in results

    Returns:
        List of product dictionaries with optional similarity scores

    Raises:
        ValueError: If invalid parameters provided
        RuntimeError: If pg_trgm extension not available
    """

    # Validate inputs
    if not query or not query.strip():
        logger.warning("Empty query provided to fuzzy_search")
        return []

    if not 0.0 <= min_similarity <= 1.0:
        error_msg = t("fuzzy_search.errors.min_similarity_invalid", lang="en", min_similarity=min_similarity)
        raise ValueError(error_msg)

    if limit <= 0:
        error_msg = t("fuzzy_search.errors.limit_invalid", lang="en", limit=limit)
        raise ValueError(error_msg)

    # Default searchable fields
    if fields is None:
        fields = ["name", "description"]

    valid_fields = {"name", "description", "brand", "category"}
    invalid_fields = set(fields) - valid_fields
    if invalid_fields:
        error_msg = t(
            "fuzzy_search.errors.invalid_fields",
            lang="en",
            invalid_fields=", ".join(sorted(invalid_fields)),
            valid_fields=", ".join(sorted(valid_fields))
        )
        raise ValueError(error_msg)

    logger.info(
        "Starting fuzzy search: query='%s', fields=%s, min_similarity=%.2f, limit=%d",
        query,
        fields,
        min_similarity,
        limit,
    )

    # Build similarity conditions for each field using normalized text
    # This enables accent-insensitive search: "camara" matches "cámara"
    similarity_conditions = []
    similarity_selects = []

    for field in fields:
        # Use normalize_text() for both field and query to enable accent-insensitive search
        similarity_conditions.append(
            f"similarity(normalize_text({field}), normalize_text(%s)) >= %s"
        )
        if include_similarity:
            similarity_selects.append(
                f"similarity(normalize_text({field}), normalize_text(%s)) AS {field}_similarity"
            )

    # Build SQL query
    base_fields = "id, sku, name, description, category, brand, tags, color, size, price"
    select_fields = base_fields

    if include_similarity:
        select_fields += ", " + ", ".join(similarity_selects)
        # Add overall max similarity for ordering (using normalized text)
        max_similarities = ", ".join(
            [f"similarity(normalize_text({f}), normalize_text(%s))" for f in fields]
        )
        select_fields += f", GREATEST({max_similarities}) AS max_similarity"

    where_clause = " OR ".join(similarity_conditions)

    # MULTI-TOKEN MATCH BOOST: Count how many query tokens match each product
    # This improves intent detection for queries like "accesorios gaming"
    # Products matching multiple tokens (e.g., category="Gaming" + type="Accesorios") rank higher
    tokens = [t.strip() for t in query.split() if t.strip() and len(t.strip()) > 2]

    if len(tokens) > 1 and include_similarity:
        # Build token match count: count fields where ANY token matches above threshold
        token_match_conditions = []
        for field in fields:
            # For each field, check if ANY token has high similarity
            field_token_checks = []
            for _ in tokens:
                field_token_checks.append(
                    f"similarity(normalize_text({field}), normalize_text(%s)) >= {min_similarity}"
                )
            # Field contributes 1 to count if ANY token matches
            token_match_conditions.append(
                f"CASE WHEN ({' OR '.join(field_token_checks)}) THEN 1 ELSE 0 END"
            )

        token_match_count = f"({' + '.join(token_match_conditions)})"

        # Use CTE to avoid duplicating token_match_count expression
        # Boost factor = 1.5: strong enough to prioritize multi-token matches
        # Example: "accesorios gaming" → Gaming products (match 2 tokens) beat generic Accesorios (match 1)
        sql = f"""
        WITH base_similarity AS (
            SELECT {base_fields}, {", ".join(similarity_selects)},
                   GREATEST({", ".join([f"similarity(normalize_text({f}), normalize_text(%s))" for f in fields])}) AS max_similarity,
                   {token_match_count} AS token_match_count
            FROM {settings.SCHEMA_NAME}.products
            WHERE {where_clause}
        )
        SELECT *,
               max_similarity * (1 + 1.5 * token_match_count) AS intent_boosted_score
        FROM base_similarity
        ORDER BY intent_boosted_score DESC, max_similarity DESC
        LIMIT %s
        """
    elif include_similarity:
        order_clause = "max_similarity DESC"
        sql = f"""
        SELECT {select_fields}
        FROM {settings.SCHEMA_NAME}.products
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT %s
        """
    else:
        order_clause = f"similarity(normalize_text({fields[0]}), normalize_text(%s)) DESC"
        sql = f"""
        SELECT {select_fields}
        FROM {settings.SCHEMA_NAME}.products
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT %s
        """

    # Build parameters in order they appear in SQL
    params = []

    if len(tokens) > 1 and include_similarity:
        # CTE structure: SELECT similarity_selects, max_similarity, token_match_count FROM ... WHERE ...
        # 1. Parameters for similarity_selects (name_similarity, etc.)
        for _ in fields:
            params.append(query)

        # 2. Parameters for max_similarity GREATEST()
        for _ in fields:
            params.append(query)

        # 3. Parameters for token_match_count
        for _ in fields:
            for token in tokens:
                params.append(token)

        # 4. Parameters for WHERE clause
        for _ in fields:
            params.extend([query, str(min_similarity)])

        # 5. LIMIT parameter
        params.append(str(limit))

    elif include_similarity:
        # Non-CTE structure: standard similarity query
        # 1. Parameters for SELECT similarity scores (name_similarity, etc.)
        for _ in fields:
            params.append(query)

        # 2. Parameters for max_similarity calculation
        for _ in fields:
            params.append(query)

        # 3. Parameters for WHERE clause
        for _ in fields:
            params.extend([query, str(min_similarity)])

        # 4. LIMIT parameter
        params.append(str(limit))

    else:
        # No similarity included
        # 1. Parameters for WHERE clause
        for _ in fields:
            params.extend([query, str(min_similarity)])

        # 2. Parameters for ORDER BY
        params.append(query)

        # 3. LIMIT parameter
        params.append(str(limit))

    try:
        rows = fetchall(sql, tuple(params))

        logger.info(
            "Fuzzy search completed: %d results found with similarity >= %.2f",
            len(rows),
            min_similarity,
        )

        # Log similarity scores for debugging
        if include_similarity and rows:
            for row in rows[:3]:  # Log first 3 results
                logger.debug(
                    "Result: '%s' (max_similarity: %.3f)",
                    row.get("name", "N/A"),
                    row.get("max_similarity", 0.0),
                )

        return rows

    except Exception as e:
        logger.error("Error in fuzzy search: %s", e)
        # Check if required extensions are available
        try:
            # Test pg_trgm
            fetchall("SELECT similarity('test', 'test')", ())
            # Test unaccent and normalize_text function
            fetchall("SELECT normalize_text('tést')", ())
        except Exception as ext_error:
            logger.error("Required extensions may not be installed: %s", ext_error)
            raise RuntimeError(
                "pg_trgm and unaccent extensions are required for fuzzy search. "
                "Please run the database initialization script first."
            ) from e
        raise


def fuzzy_search_product_names(query: str, limit: int = 5) -> list[dict]:
    """
    Simplified fuzzy search focused on product names only.

    Optimized for common use case of searching by product name with
    higher similarity threshold for more precise results.
    """
    return fuzzy_search(
        query=query,
        fields=["name"],
        min_similarity=0.4,  # Higher threshold for name-only search
        limit=limit,
        include_similarity=True,
    )


def fuzzy_search_comprehensive(query: str, limit: int = 20) -> list[dict]:
    """
    Comprehensive fuzzy search across all text fields.

    Uses lower similarity threshold to catch more potential matches
    across name, description, brand, and category.
    """
    return fuzzy_search(
        query=query,
        fields=["name", "description", "brand", "category"],
        min_similarity=0.25,  # Lower threshold for broader search
        limit=limit,
        include_similarity=True,
    )


def fuzzy_search_smart(
    query: str,
    fields: list[str] | None = None,
    limit: int = 20,
    strict_threshold: float = 0.3,
    word_threshold: float = 0.4,
    fallback_threshold: float = 0.2,
    name_weight: float = 2.0,
    description_weight: float = 1.0,
    category_weight: float = 1.5,
    brand_weight: float = 1.0,
) -> list[dict]:
    """
    Smart fuzzy search with multi-tier fallback strategy for better typo tolerance.

    This function implements a four-tier search strategy:
    1. Standard similarity search (strict_threshold)
    2. Word similarity search for partial matches (word_threshold) - WITH WEIGHTED SCORING
    2.5. Token-based search - searches by individual words when multi-word query fails (NEW)
    3. Relaxed similarity search as final fallback (fallback_threshold)

    IMPROVED: Now searches in name, description, AND category fields by default.
    This enables finding products by generic category queries like "qué hay en hogar".

    NEW (2025-10-03): Weighted scoring system for Tier 2 to prioritize name matches.
    Fixes issue where description matches outranked name matches (e.g., "sartén eléctrico"
    prioritizing "Escritorio Ajustable" with "eléctrico" in description over "Sartén" in name).

    NEW (2025-10-03): Tier 2.5 token-based search handles multi-word queries with irrelevant terms.
    Fixes issue where "sartenes electricos" (0.200 similarity) fails to find "Sartén" but "sartenes"
    alone (0.444 similarity) would succeed. Tokenizes query and searches by best matching individual word.

    NEW (2025-10-03): Position-based token weighting in Tier 2.5 prioritizes earlier tokens.
    Fixes relevance issue where modifier tokens (e.g., "electricos") with high similarity outrank
    primary tokens (e.g., "sartenes") with medium similarity. Uses formula: weight = 1.0 / (position + 1).
    First token (usually the noun): weight 1.0, second (modifier): 0.5, third: 0.33, etc.

    NEW (2025-10-03): Multi-token match boost for intent detection in Tier 2.5.
    Products matching multiple query tokens across different fields get priority boost.
    Fixes issue where "accesorios gaming" prioritizes generic "Accesorios" over "Gaming" products.
    Formula: intent_boosted_score = base_score × (1 + 0.3 × token_match_count).
    Example: Product matching 2 tokens gets 1.6x boost, 3 tokens gets 1.9x boost.

    Args:
        query: Search term to match against
        fields: List of fields to search in ['name', 'description', 'brand', 'category']
                Default: ['name', 'description', 'category']
        limit: Maximum number of results to return (default: 20, max recommended: 50)
               Balance between token efficiency (~800 tokens for 20 products) and UX
               (allows 5 pages of 4 products). Follows API pagination best practices 2025.
        strict_threshold: Initial similarity threshold for standard search (default: 0.3)
        word_threshold: Threshold for word_similarity search (default: 0.4)
        fallback_threshold: Final fallback threshold (default: 0.2)
        name_weight: Weight multiplier for name field matches (default: 2.0 - highest priority)
        description_weight: Weight for description field matches (default: 1.0 - medium)
        category_weight: Weight for category field matches (default: 1.5 - high)
        brand_weight: Weight for brand field matches (default: 1.0 - medium)

    Returns:
        List of product dictionaries with similarity scores and search tier information

    Architecture Notes:
        - Uses database-level pg_trgm functions for performance
        - Implements graceful degradation pattern
        - Maintains result quality while improving typo tolerance
        - New category index enables fast category-based searches
        - Weighted scoring ensures name matches rank higher than description matches
    """
    if not query or not query.strip():
        logger.warning("Empty query provided to fuzzy_search_smart")
        return []

    if fields is None:
        fields = ["name", "description", "category"]

    logger.info(
        "Starting smart fuzzy search: query='%s', fields=%s, thresholds=[%.2f, %.2f, %.2f]",
        query,
        fields,
        strict_threshold,
        word_threshold,
        fallback_threshold,
    )

    # Tier 1: Standard similarity search
    results = fuzzy_search(
        query=query,
        fields=fields,
        min_similarity=strict_threshold,
        limit=limit,
        include_similarity=True,
    )

    if results:
        logger.info("Smart search succeeded at Tier 1 (standard similarity)")
        for result in results:
            result["search_tier"] = "standard"
        return results

    # Tier 2: Word similarity search (better for partial matches and typos)
    # NEW: With weighted scoring to prioritize name matches
    logger.info("Tier 1 no results, trying Tier 2 (word similarity with weighted scoring)")

    # Build field weights mapping
    field_weights = {
        "name": name_weight,
        "description": description_weight,
        "category": category_weight,
        "brand": brand_weight,
    }

    # Build word similarity search with weighted scoring
    base_fields = "id, sku, name, description, category, brand, tags, color, size, price"
    word_conditions = []
    word_selects = []
    weighted_components = []
    total_weight = 0.0

    for field in fields:
        weight = field_weights.get(field, 1.0)
        total_weight += weight

        # word_similarity works better for finding partial matches
        word_conditions.append(f"word_similarity(%s, {field}) >= %s")
        word_selects.append(f"word_similarity(%s, {field}) AS {field}_word_sim")

        # Add weighted component for scoring
        weighted_components.append(f"(word_similarity(%s, {field}) * {weight})")

    # Calculate weighted similarity score
    weighted_score = f"({' + '.join(weighted_components)}) / {total_weight}"

    # Keep max_word_similarity for backward compatibility
    max_word_similarities = ", ".join([f"word_similarity(%s, {f})" for f in fields])

    select_fields = (
        f"{base_fields}, {', '.join(word_selects)}, "
        f"GREATEST({max_word_similarities}) AS max_word_similarity, "
        f"{weighted_score} AS weighted_similarity"
    )
    where_clause = " OR ".join(word_conditions)

    sql = f"""
    SELECT {select_fields}
    FROM {settings.SCHEMA_NAME}.products
    WHERE {where_clause}
    ORDER BY weighted_similarity DESC, max_word_similarity DESC
    LIMIT %s
    """

    # Build parameters
    params = []
    # For SELECT word similarity scores
    for _ in fields:
        params.append(query)
    # For weighted components calculation
    for _ in fields:
        params.append(query)
    # For GREATEST calculation (max_word_similarity)
    for _ in fields:
        params.append(query)
    # For WHERE conditions
    for _ in fields:
        params.extend([query, str(word_threshold)])
    # Limit
    params.append(str(limit))

    try:
        rows = fetchall(sql, tuple(params))

        if rows:
            tier2_result_count = len(rows)
            logger.info(
                "Smart search succeeded at Tier 2: %d results with word_similarity >= %.2f (weighted scoring)",
                tier2_result_count,
                word_threshold,
            )

            # If we have few results and it's a multi-word query, also try Tier 2.5
            # This helps when irrelevant terms dilute the similarity but one term is very relevant
            if (
                tier2_result_count < 3
                and len([t.strip() for t in query.split() if t.strip() and len(t.strip()) > 2]) > 1
            ):
                logger.info(
                    "Tier 2 found few results (%d), will also try Tier 2.5 for better coverage",
                    tier2_result_count,
                )
                # Store Tier 2 results but don't return yet - try Tier 2.5 too
                tier2_rows = rows
                for row in tier2_rows:
                    row["search_tier"] = "word_similarity"
                    row["max_similarity"] = row.get(
                        "weighted_similarity", row.get("max_word_similarity", 0)
                    )
            else:
                # Enough results, return Tier 2
                for row in rows:
                    row["search_tier"] = "word_similarity"
                    row["max_similarity"] = row.get(
                        "weighted_similarity", row.get("max_word_similarity", 0)
                    )
                return rows
        else:
            tier2_rows = []

    except Exception as e:
        logger.error("Error in Tier 2 word similarity search: %s", e)
        tier2_rows = []

    # Tier 2.5: Token-based search (NEW - handles multi-word queries with irrelevant terms)
    # Execute when: (1) Tier 2 had no results, OR (2) Tier 2 had few results (<3) on multi-word query
    should_try_tier25 = len(tier2_rows) < 3
    if should_try_tier25:
        if tier2_rows:
            logger.info(
                "Tier 2 had few results, trying Tier 2.5 for additional coverage (individual token search)"
            )
        else:
            logger.info("Tier 2 no results, trying Tier 2.5 (individual token search)")

    # Tokenize query and search by individual words
    tokens = [t.strip() for t in query.split() if t.strip() and len(t.strip()) > 2]

    if should_try_tier25 and len(tokens) > 1:  # Only makes sense for multi-word queries
        logger.debug(f"Tokenized query into {len(tokens)} words: {tokens}")

        # Build token-based search with weighted scoring
        # Strategy: For each field, find the BEST matching token
        # Use CTE to avoid parameter duplication
        token_weighted_components = []
        token_total_weight = 0.0
        cte_selects = []

        for field in fields:
            weight = field_weights.get(field, 1.0)
            token_total_weight += weight

            # Build position-weighted token similarities
            # Position weight: 1.0 for first token, 0.5 for second, 0.33 for third, etc.
            # Formula: position_weight = 1.0 / (position + 1)
            position_weighted_token_sims = []
            for token_idx, _ in enumerate(tokens):
                position_weight = 1.0 / (token_idx + 1)
                # Apply position weight to token similarity
                position_weighted_token_sims.append(
                    f"(word_similarity(%s, {field}) * {position_weight})"
                )

            # Maximum position-weighted similarity across all tokens for this field
            max_token_sim = f"GREATEST({', '.join(position_weighted_token_sims)})"
            cte_selects.append(f"{max_token_sim} AS {field}_token_sim")

            # Weighted component using best position-weighted token match per field
            token_weighted_components.append(f"({field}_token_sim * {weight})")

        # Calculate weighted similarity score
        token_weighted_score = f"({' + '.join(token_weighted_components)}) / {token_total_weight}"

        # Build overall max similarity across all fields
        all_field_token_sims = [f"{f}_token_sim" for f in fields]

        # Build WHERE conditions using field similarities
        token_where_conditions = []
        for field in fields:
            token_where_conditions.append(f"{field}_token_sim >= %s")

        # Use CTE to calculate similarities once
        # Also calculate multi-token match count for intent detection
        token_sql = f"""
        WITH token_sims AS (
            SELECT {base_fields}, {", ".join(cte_selects)}
            FROM {settings.SCHEMA_NAME}.products
        ),
        token_match_count AS (
            SELECT *,
                   GREATEST({", ".join(all_field_token_sims)}) AS max_token_similarity,
                   {token_weighted_score} AS weighted_token_similarity,
                   -- Count how many tokens match (above threshold) across ALL fields
                   ({" + ".join([f"CASE WHEN {f}_token_sim >= {word_threshold} THEN 1 ELSE 0 END" for f in fields])}) AS token_match_count
            FROM token_sims
        )
        SELECT *,
               -- Apply intent boost: products matching more query tokens get priority
               -- Formula: base_score * (1 + 0.3 * token_match_count)
               weighted_token_similarity * (1 + 0.3 * token_match_count) AS intent_boosted_score
        FROM token_match_count
        WHERE {" OR ".join(token_where_conditions)}
        ORDER BY intent_boosted_score DESC, weighted_token_similarity DESC, max_token_similarity DESC
        LIMIT %s
        """

        # Build parameters for token search (appears only once in CTE)
        token_params = []
        # For each field's GREATEST() in CTE - add all token params
        for _ in fields:
            for token in tokens:
                token_params.append(token)
        # For WHERE conditions (one threshold per field)
        for _ in fields:
            token_params.append(str(word_threshold))
        # Limit
        token_params.append(str(limit))

        try:
            token_rows = fetchall(token_sql, tuple(token_params))

            if token_rows:
                logger.info(
                    "Smart search succeeded at Tier 2.5: %d results with token-based search",
                    len(token_rows),
                )
                for row in token_rows:
                    row["search_tier"] = "token_based"
                    # Use intent_boosted_score if available, otherwise weighted_token_similarity
                    row["max_similarity"] = row.get(
                        "intent_boosted_score",
                        row.get(
                            "weighted_token_similarity",
                            row.get("max_token_similarity", 0),
                        ),
                    )

                # Combine Tier 2 and Tier 2.5 results if both exist
                if tier2_rows:
                    # Merge and deduplicate by SKU
                    combined = {}
                    for row in tier2_rows:
                        combined[row["sku"]] = row
                    for row in token_rows:
                        sku = row["sku"]
                        # If product exists in both, keep the one with higher score
                        if sku in combined:
                            if row["max_similarity"] > combined[sku]["max_similarity"]:
                                combined[sku] = row
                        else:
                            combined[sku] = row

                    # Sort by score descending
                    final_results = sorted(
                        combined.values(),
                        key=lambda x: x["max_similarity"],
                        reverse=True,
                    )[:limit]
                    logger.info(
                        f"Combined Tier 2 and Tier 2.5: {len(final_results)} unique products"
                    )
                    return final_results
                return token_rows

        except Exception as e:
            logger.error("Error in Tier 2.5 token-based search: %s", e)

    # If we have Tier 2 results but Tier 2.5 didn't execute or failed
    if tier2_rows:
        return tier2_rows

    # Tier 3: Relaxed threshold as final fallback
    logger.info("Tier 2.5 no results, trying Tier 3 (relaxed threshold)")
    results = fuzzy_search(
        query=query,
        fields=fields,
        min_similarity=fallback_threshold,
        limit=limit,
        include_similarity=True,
    )

    if results:
        logger.info(
            "Smart search succeeded at Tier 3: %d results with similarity >= %.2f",
            len(results),
            fallback_threshold,
        )
        for result in results:
            result["search_tier"] = "fallback"
            result["low_confidence"] = True  # Flag for UI to show warning
    else:
        logger.info("No results found even with relaxed threshold")

    return results
