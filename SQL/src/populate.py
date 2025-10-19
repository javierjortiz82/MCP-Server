#!/usr/bin/env python3
"""
Lab01-MCP Unified Data Loader

Loads JSON data from @SQL/data/ and populates database or generates SQL.
Special handling for products: generates embeddings on-the-fly during insertion.

Uso:
    python3 populate.py --db                             # Insert all tables to database
    python3 populate.py --db --table products            # Insert only products (with embeddings)
    python3 populate.py --db --embeddings                # Insert all + generate embeddings (products only)
    python3 populate.py --output-sql-dir ../04_seed/    # Generate SQL files for all tables
    python3 populate.py --output-sql-dir ../04_seed/ --table products  # Generate SQL for products

Requisitos en .env:
    DATABASE_URL, GOOGLE_API_KEY (for embeddings), SCHEMA_NAME

"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import argparse
from typing import Dict, List, Optional
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from tenacity import retry, stop_after_attempt, wait_exponential

# Google Gemini
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# pgvector
try:
    from pgvector.psycopg2 import register_vector
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("populate")

DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 8))
OUTPUT_DIMENSIONALITY = int(os.getenv("OUTPUT_DIMENSIONALITY", 1536))

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"

# Table metadata: (table_name, json_filename, has_embeddings, needs_api, columns_list)
TABLES = [
    ("products", "01_products.json", True, True,
     ["sku", "name", "description", "category", "brand", "tags", "color", "size", "price", "embedding"]),
    ("service_types", "02_service_types.json", False, False, None),
    ("business_hours", "03_business_hours.json", False, False, None),
    ("blocked_times", "04_blocked_times.json", False, False, None),
    ("service_hours", "05_service_hours.json", False, False, None),
    ("appointments", "06_appointments.json", False, False, None),
    ("email_queue", "07_email_queue.json", False, False, None),
    ("conversation_sessions", "08_conversation_sessions.json", False, False, None),
    ("conversation_messages", "09_conversation_messages.json", False, False, None),
    ("agent_memory_blocks", "10_agent_memory_blocks.json", False, False, None),
    ("user_memory_profiles", "11_user_memory_profiles.json", False, False, None),
    ("user_memory_blocks", "12_user_memory_blocks.json", False, False, None),
    ("agent_context_transfers", "13_agent_context_transfers.json", False, False, None),
    ("pagination_contexts", "14_pagination_contexts.json", False, False, None),
]

if not DATABASE_URL:
    logger.error("DATABASE_URL not in .env")
    sys.exit(1)


def load_json(table_name: str) -> List[Dict]:
    """Load JSON data for table."""
    for name, file, _, _, _ in TABLES:
        if name == table_name:
            path = DATA_DIR / file
            if not path.exists():
                logger.warning(f"File not found: {path}")
                return []

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                return []

            logger.info(f"Loaded {len(data)} records from {file}")
            return data

    return []


def build_semantic_text(product: Dict) -> str:
    """Build semantic text for embedding from product fields."""
    fields = [
        product.get("name", ""),
        product.get("description", ""),
        product.get("brand", ""),
        product.get("category", ""),
        " ".join(product.get("tags", []) or []),
    ]
    return " | ".join([f for f in fields if f])


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
def make_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using Google Gemini API with retries."""
    if not GENAI_AVAILABLE or not GOOGLE_API_KEY:
        logger.warning("Google Gemini not available, skipping embedding")
        return None

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        res = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=OUTPUT_DIMENSIONALITY),
        )

        if hasattr(res, "embeddings"):
            embedding = res.embeddings[0].values
        elif hasattr(res, "embedding"):
            embedding = res.embedding
        else:
            return None

        return embedding if len(embedding) == OUTPUT_DIMENSIONALITY else None

    except Exception as e:
        logger.exception(f"Error generating embedding: {e}")
        return None


def insert_to_db(table_name: str, records: List[Dict]):
    """Insert records to database."""
    if not PSYCOPG2_AVAILABLE:
        raise ImportError('psycopg2 required')

    if not records:
        logger.info(f"No records for {table_name}")
        return

    conn = psycopg2.connect(DATABASE_URL)
    try:
        register_vector(conn)
    except Exception:
        pass  # pgvector may not be needed for all tables

    try:
        # Build column names from first record
        columns = list(records[0].keys())

        # For products table, use specific column order
        if table_name == "products":
            columns = ["sku", "name", "description", "category", "brand", "tags", "color", "size", "price", "embedding"]

        sql = f"""
        INSERT INTO {SCHEMA_NAME}.{table_name} ({','.join(columns)})
        VALUES %s
        ON CONFLICT DO NOTHING
        """

        tuples = [tuple(r.get(c) for c in columns) for r in records]

        with conn.cursor() as cur:
            execute_values(cur, sql, tuples, page_size=100)
            conn.commit()

        logger.info(f"✅ Inserted {len(tuples)} records to {table_name}")

    finally:
        conn.close()


def records_to_sql(table_name: str, records: List[Dict]) -> str:
    """Convert records to SQL INSERT statement."""
    if not records:
        return f"-- No data for {table_name}\n"

    columns = list(records[0].keys())

    # For products table with embeddings, use special format
    if table_name == "products":
        return generate_products_sql(records, columns)

    sql_lines = [
        f"-- {table_name.upper()}",
        f"INSERT INTO {SCHEMA_NAME}.{table_name} ({','.join(columns)}) VALUES",
    ]

    for i, record in enumerate(records):
        values = []
        for col in columns:
            val = record.get(col)
            if val is None:
                values.append("NULL")
            elif isinstance(val, str):
                values.append(f"'{val.replace(chr(39), chr(39)*2)}'")
            elif isinstance(val, bool):
                values.append("TRUE" if val else "FALSE")
            elif isinstance(val, (list, dict)):
                json_str = json.dumps(val)
                values.append(f"'{json_str.replace(chr(39), chr(39)*2)}'")
            else:
                values.append(str(val))

        sql_lines.append(f"({','.join(values)})" + ("," if i < len(records) - 1 else ";"))

    sql_lines.append("")
    return "\n".join(sql_lines)


def generate_products_sql(products: List[Dict], columns: List[str]) -> str:
    """Generate SQL INSERT for products with vector embeddings."""
    logger.info("Generating SQL INSERT for products with embeddings...")

    sql_lines = [
        "-- ============================================================================",
        "-- SEED DATA: Products with Vector Embeddings (DML)",
        "-- ============================================================================",
        f"-- Total: {len(products)} products",
        "-- Generated by populate.py",
        "--",
        "",
        "-- Disable triggers for faster insertion",
        f"ALTER TABLE {SCHEMA_NAME}.products DISABLE TRIGGER ALL;",
        "",
        f"INSERT INTO {SCHEMA_NAME}.products (sku, name, description, category, brand, tags, color, size, price, embedding)",
        "VALUES",
    ]

    products_with_embeddings = [p for p in products if p.get("embedding")]

    for i, prod in enumerate(products_with_embeddings):
        sku = prod["sku"].replace("'", "''")
        name = prod["name"].replace("'", "''")
        description = prod.get("description", "").replace("'", "''")
        category = prod.get("category", "").replace("'", "''")
        brand = prod.get("brand", "").replace("'", "''")
        tags = prod.get("tags", [])
        color = prod.get("color", "").replace("'", "''")
        size = prod.get("size", "").replace("'", "''")
        price = prod["price"]
        embedding = prod["embedding"]

        tags_str = "'{" + ",".join(tags) + "}'" if tags else "NULL"
        # Convert embedding list to PostgreSQL vector format
        if isinstance(embedding, list):
            embedding_values = ",".join([str(float(x)) for x in embedding])
            embedding_str = f"'[{embedding_values}]'::vector"
        elif isinstance(embedding, str):
            embedding_str = f"'{embedding}'::vector"
        else:
            embedding_str = str(embedding)

        values = (
            f"('{sku}', '{name}', '{description}', '{category}', "
            f"'{brand}', {tags_str}, '{color}', '{size}', {price}, {embedding_str})"
        )

        is_last = i == len(products_with_embeddings) - 1
        sql_lines.append(values + (';' if is_last else ','))

    sql_lines.extend([
        "",
        "-- Re-enable triggers",
        f"ALTER TABLE {SCHEMA_NAME}.products ENABLE TRIGGER ALL;",
        "",
        f"-- Verification: {len(products_with_embeddings)} products inserted",
    ])

    return "\n".join(sql_lines)


def process_products_with_embeddings(records: List[Dict]) -> List[Dict]:
    """
    Process products and generate embeddings on-the-fly.
    This is the key difference for products table.
    """
    logger.info(f"Processing {len(records)} products for embeddings...")
    logger.info(f"Embedding model: {EMBEDDING_MODEL}, Batch size: {BATCH_SIZE}")

    enriched = []

    for i, product in enumerate(records):
        # Build semantic text if not already present
        if not product.get("semantic_text"):
            semantic_text = build_semantic_text(product)
            product["semantic_text"] = semantic_text

        # Generate embedding on-the-fly
        if not product.get("embedding"):
            semantic_text = product.get("semantic_text", build_semantic_text(product))
            embedding = make_embedding(semantic_text)
            product["embedding"] = embedding
            time.sleep(0.05)  # Slight delay between API calls

            if (i + 1) % BATCH_SIZE == 0:
                logger.info(f"Generated embeddings for {i+1}/{len(records)} products")

        enriched.append(product)

    logger.info(f"✅ All {len(enriched)} products processed")
    return enriched


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Unified data loader for Lab01-MCP")
    parser.add_argument("--db", action="store_true", help="Insert to database")
    parser.add_argument(
        "--output-sql-dir",
        help="Generate SQL files in directory"
    )
    parser.add_argument("--embeddings", action="store_true", help="Generate embeddings (products only)")
    parser.add_argument("--table", help="Load specific table only")

    args = parser.parse_args()

    if not args.db and not args.output_sql_dir:
        logger.error("Use --db or --output-sql-dir")
        sys.exit(1)

    logger.info(f"Loading data from {DATA_DIR}")

    for table_name, json_file, has_embeddings, needs_api, _ in TABLES:
        if args.table and table_name != args.table:
            continue

        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {table_name}")
        logger.info(f"{'='*80}")

        records = load_json(table_name)

        if not records:
            logger.info(f"No data for {table_name}")
            continue

        # Special handling for products: generate embeddings on-the-fly
        if table_name == "products":
            if args.db or args.embeddings:
                records = process_products_with_embeddings(records)

        # Insert or generate SQL
        if args.db:
            insert_to_db(table_name, records)
        else:
            sql = records_to_sql(table_name, records)
            output_dir = Path(args.output_sql_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"{table_name}.sql"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(sql)

            logger.info(f"✅ SQL generated to {output_file}")

    logger.info(f"\n{'='*80}")
    logger.info("✅ All data processed successfully!")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    main()
