from collections.abc import Iterable

from utils.db import upsert_product
from utils.embeddings import emb_client
from utils.logger import setup_logging

# Setup logger for ingest operations
logger = setup_logging("mcp_tools_ingest")


def ingest_products(products: Iterable[dict]) -> int:
    """Ingesta una colección de productos calculando embeddings por lotes.

    Cada item debe contener las claves: sku, name, description, category, brand, tags, color, size, price.
    Devuelve cantidad de elementos procesados.
    """
    logger.info("Iniciando ingesta de productos...")
    batch = []
    processed = 0
    batch_size = 16

    for p in products:
        batch.append(p)
        if len(batch) >= batch_size:
            logger.debug("Procesando lote de %d productos", len(batch))
            texts = [b.get("description", "") or b.get("name", "") for b in batch]

            try:
                vecs = emb_client.embed(texts)
                for item, vec in zip(batch, vecs, strict=False):
                    item["embedding"] = vec
                    upsert_product(item)
                    processed += 1
                logger.debug("Lote procesado exitosamente: %d productos", len(batch))
            except Exception as e:
                logger.error("Error procesando lote de productos: %s", e)
                raise

            batch = []

    # Procesar productos restantes
    if batch:
        logger.debug("Procesando lote final de %d productos", len(batch))
        texts = [b.get("description", "") or b.get("name", "") for b in batch]

        try:
            vecs = emb_client.embed(texts)
            for item, vec in zip(batch, vecs, strict=False):
                item["embedding"] = vec
                upsert_product(item)
                processed += 1
            logger.debug("Lote final procesado exitosamente: %d productos", len(batch))
        except Exception as e:
            logger.error("Error procesando lote final de productos: %s", e)
            raise

    logger.info("Ingesta completada: %d productos procesados", processed)
    return processed
