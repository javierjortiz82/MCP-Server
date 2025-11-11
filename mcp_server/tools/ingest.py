from collections.abc import Iterable

from utils.db import upsert_product
from utils.embeddings import emb_client
from utils.logger import setup_logging

# Setup logger for ingest operations
logger = setup_logging("mcp_tools_ingest")


def ingest_products(products: Iterable[dict]) -> int:
    """Ingest a collection of products by calculating embeddings in batches.

    Each item must contain keys: sku, name, description, category, brand, tags, color, size, price.
    Returns the number of processed items.
    """
    logger.info("Starting product ingestion...")
    batch = []
    processed = 0
    batch_size = 16

    for p in products:
        batch.append(p)
        if len(batch) >= batch_size:
            logger.debug("Processing batch of %d products", len(batch))
            texts = [b.get("description", "") or b.get("name", "") for b in batch]

            try:
                vecs = emb_client.embed(texts)
                for item, vec in zip(batch, vecs, strict=False):
                    item["embedding"] = vec
                    upsert_product(item)
                    processed += 1
                logger.debug("Batch processed successfully: %d products", len(batch))
            except Exception as e:
                logger.error("Error processing product batch: %s", e)
                raise

            batch = []

    # Process remaining products
    if batch:
        logger.debug("Processing final batch of %d products", len(batch))
        texts = [b.get("description", "") or b.get("name", "") for b in batch]

        try:
            vecs = emb_client.embed(texts)
            for item, vec in zip(batch, vecs, strict=False):
                item["embedding"] = vec
                upsert_product(item)
                processed += 1
            logger.debug("Final batch processed successfully: %d products", len(batch))
        except Exception as e:
            logger.error("Error processing final product batch: %s", e)
            raise

    logger.info("Ingestion completed: %d products processed", processed)
    return processed
