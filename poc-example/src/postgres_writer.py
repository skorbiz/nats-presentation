"""High-throughput PostgreSQL writer for the CDC demo.

Uses one persistent connection and one batched INSERT per loop iteration so
the benchmark measures PostgreSQL/CDC throughput rather than shell overhead.
"""

from __future__ import annotations

import os
import time

import psycopg


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def main() -> None:
    conninfo = os.getenv(
        "POSTGRES_WRITER_DSN",
        "postgresql://postgres:postgres@postgres-cdc:5432/inventory",
    )
    start_delay_seconds = env_float("WRITER_START_DELAY_SECONDS", 8)
    insert_interval_seconds = env_float("WRITER_INSERT_INTERVAL_SECONDS", 5)
    batch_size = env_int("WRITER_BATCH_SIZE", 1)
    payload_bytes = env_int("WRITER_PAYLOAD_BYTES", 0)

    print("Waiting for Debezium snapshot to finish...")
    time.sleep(start_delay_seconds)

    with psycopg.connect(conninfo, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(
                    MAX(CAST(SUBSTRING(sku FROM 5) AS INTEGER)),
                    0
                ) + 1
                FROM public.inventory_items
                WHERE sku ~ '^SKU-[0-9]+$'
                """
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to read next SKU index from inventory_items")
            next_index = row[0]
            print(f"Starting writer from SKU index {next_index}")

            while True:
                end_index = next_index + batch_size - 1
                print(f"Writing batch {next_index}..{end_index} (payload bytes: {payload_bytes})")
                cur.execute(
                    """
                    INSERT INTO public.inventory_items (
                        sku,
                        quantity,
                        unit_price,
                        payload
                    )
                    SELECT
                        concat('SKU-', lpad(gs::text, 6, '0')),
                        10 * gs,
                        (mod(gs - 1, 9) + 1)::numeric + 0.99,
                        repeat('x', %s)
                    FROM generate_series(%s::integer, %s::integer) AS gs
                    """,
                    (payload_bytes, next_index, end_index),
                )
                next_index += batch_size

                if insert_interval_seconds > 0:
                    time.sleep(insert_interval_seconds)


if __name__ == "__main__":
    main()
