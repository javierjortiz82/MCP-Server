# populate-db.py
"""
Lee /sql/data/products.json, genera embeddings multilingües usando Google ADK (gemini-embedding-001)
y guarda los registros en la tabla sales.products (incluyendo embedding).
Requisitos en .env:
 - DATABASE_URL=postgresql://user:pass@localhost:5432/db
 - GOOGLE_API_KEY=...  (o configuración que use google.genai)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from tenacity import retry, stop_after_attempt, wait_exponential

# google genai client
try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None  # manejar abajo

# pgvector adapter
try:
    from pgvector.psycopg2 import register_vector
except Exception:
    register_vector = None

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("populate-db")

DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "sales")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 8))
JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "products.json")

if not DATABASE_URL:
    logger.error("DATABASE_URL no encontrada en .env")
    raise SystemExit(1)
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY no encontrada en .env")
    raise SystemExit(1)
if genai is None:
    logger.error(
        "google.genai no está instalado. Instala 'google-genai' o paquete equivalente."
    )
    raise SystemExit(1)
if register_vector is None:
    logger.error(
        "pgvector psypg2 adapter no está instalado. Instala 'pgvector' paquete python."
    )
    raise SystemExit(1)

# inicializa cliente Google ADK
client = genai.Client(api_key=GOOGLE_API_KEY)


def load_products(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("El archivo JSON debe contener una lista de productos.")
    logger.info("Cargados %d productos desde %s", len(data), path)
    return data


def build_semantic_text(product: Dict) -> str:
    """Crea una cadena bilingüe (ES/EN) para fomentar embeddings detectables en ambos idiomas."""
    # Concatenamos campos semánticos clave
    fields = [
        product.get("name", ""),
        product.get("description", ""),
        product.get("brand", ""),
        product.get("category", ""),
        " ".join(product.get("tags", []) or []),
    ]
    base = " | ".join([f for f in fields if f])

    # Separador claro para el modelo
    return f"{base}"


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
def make_embedding(text: str) -> List[float]:
    """Llama a Gemini embedding model (gemini-embedding-001). Reintentos por tenacity."""
    logger.debug("Generando embedding (long text %d)...", len(text))
    # Llamada a la API con dimensionalidad específica de 1536
    res = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=1536),
    )
    # La respuesta en google-genai 1.38.0 tiene la estructura res.embeddings[0].values
    try:
        embedding = None
        # Acceder a los embeddings según la estructura de la API actual
        if hasattr(res, "embeddings"):
            # Estructura actual: res.embeddings[0].values
            embedding = res.embeddings[0].values
        elif hasattr(res, "embedding"):
            # Fallback para compatibilidad
            embedding = res.embedding
        else:
            # Intenta acceder como dict si es necesario
            if isinstance(res, dict) and "embeddings" in res:
                embedding = res["embeddings"][0]["values"]

        if not embedding:
            raise RuntimeError("Respuesta API no contiene embedding")
    except Exception as exc:
        logger.exception("Error parsing embedding response: %s", exc)
        raise
    if len(embedding) != 1536:
        logger.warning(
            "Embedding generado tiene longitud %d (esperado 1536).", len(embedding)
        )
    return embedding


def batch_insert_products(conn, rows: List[Dict]):
    """Inserta por lotes usando execute_values. Se espera que cada row tenga embedding (lista float)."""
    register_vector(conn)  # registra adaptador si es necesario
    sql = f"""
    INSERT INTO {SCHEMA_NAME}.products
      (sku, name, description, category, brand, tags, color, size, price, embedding)
    VALUES %s
    ON CONFLICT (sku) DO UPDATE SET
      name = EXCLUDED.name,
      description = EXCLUDED.description,
      category = EXCLUDED.category,
      brand = EXCLUDED.brand,
      tags = EXCLUDED.tags,
      color = EXCLUDED.color,
      size = EXCLUDED.size,
      price = EXCLUDED.price,
      embedding = EXCLUDED.embedding
    """
    tuples = []
    for r in rows:
        tuples.append(
            (
                r.get("sku"),
                r.get("name"),
                r.get("description"),
                r.get("category"),
                r.get("brand"),
                r.get("tags"),
                r.get("color"),
                r.get("size"),
                r.get("price"),
                r.get("embedding"),
            )
        )
    with conn.cursor() as cur:
        execute_values(cur, sql, tuples, template=None, page_size=100)
        conn.commit()
    logger.info("Insertados %d filas (batch).", len(tuples))


def main():
    products = load_products(JSON_PATH)
    # Preparamos lista con semantic_text y luego generamos embeddings por lotes (ejemplo: hacer 10 por batch)
    enriched = []
    batch_size = BATCH_SIZE
    logger.info(
        "Empezando generación de embeddings y carga. Batch size para llamadas a la API: %d",
        batch_size,
    )

    # Conexion DB
    conn = psycopg2.connect(DATABASE_URL)
    try:
        for i, p in enumerate(products):
            st = build_semantic_text(p)
            p["semantic_text"] = st
            enriched.append(p)

            # Si llegamos al batch o fin, procesamos
            if len(enriched) >= batch_size or i == len(products) - 1:
                # Generamos embeddings uno a uno (puedes adaptar a batch si la API lo soporta)
                for item in enriched:
                    text = item["semantic_text"]
                    try:
                        emb = make_embedding(text)
                        item["embedding"] = emb
                        time.sleep(0.05)  # ligera pausa para evitar límites
                    except Exception as exc:
                        logger.exception(
                            "Fallo generando embedding para SKU %s: %s",
                            item.get("sku"),
                            exc,
                        )
                        item["embedding"] = None  # decide estrategia
                # Filtramos solo los que tienen embedding
                to_insert = [x for x in enriched if x.get("embedding")]
                if to_insert:
                    batch_insert_products(conn, to_insert)
                else:
                    logger.warning(
                        "Ningún embedding válido en este batch, saltando inserción."
                    )
                enriched = []
        logger.info("Proceso completado.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
