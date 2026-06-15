"""Raw JetStream publisher for comparing broker load without Postgres/Debezium."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import nats
from nats.js.api import RetentionPolicy, StorageType


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def write_stats(stats_path: Path, published_messages: int) -> None:
    stats_path.write_text(
        json.dumps(
            {
                "published_messages": published_messages,
                "updated_at_epoch_seconds": time.time(),
            }
        ),
        encoding="utf-8",
    )


async def main() -> None:
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    stream_name = os.getenv("RAW_JETSTREAM_STREAM_NAME", "DEMO_RAW_STREAM")
    subject = os.getenv("RAW_JETSTREAM_SUBJECT", "demo_raw.data")
    subject_wildcard = os.getenv("RAW_JETSTREAM_SUBJECT_WILDCARD", "demo_raw.>")
    stats_file = Path(os.getenv("RAW_PUBLISHER_STATS_FILE", "/tmp/raw_publisher_stats.json"))

    start_delay_seconds = env_float("RAW_PUBLISHER_START_DELAY_SECONDS", 8)
    publish_interval_seconds = env_float("RAW_PUBLISHER_INTERVAL_SECONDS", 5)
    publish_batch_size = env_int("RAW_PUBLISHER_BATCH_SIZE", 1)
    payload_bytes = env_int("RAW_PUBLISHER_PAYLOAD_BYTES", 0)

    print("Raw JetStream Publisher: Waiting before publishing...")
    await asyncio.sleep(start_delay_seconds)

    print(f"Raw JetStream Publisher: Connecting to {nats_server}...")
    nc = await nats.connect(nats_server)
    js = nc.jetstream()
    await js.add_stream(
        name=stream_name,
        subjects=[subject_wildcard],
        retention=RetentionPolicy.LIMITS,
        storage=StorageType.MEMORY,
    )
    print(f"Raw JetStream Publisher: Ready on stream {stream_name}")

    published_messages = 0
    write_stats(stats_file, published_messages)

    next_index = 1
    payload_text = "x" * payload_bytes

    try:
        while True:
            batch_end = next_index + publish_batch_size - 1
            print(
                f"Raw JetStream Publisher: Publishing batch {next_index}..{batch_end} (payload bytes: {payload_bytes})"
            )
            for message_id in range(next_index, batch_end + 1):
                message = {
                    "id": message_id,
                    "sku": f"SKU-{message_id:06d}",
                    "quantity": 10 * message_id,
                    "unit_price": float((message_id - 1) % 9 + 1) + 0.99,
                    "payload": payload_text,
                    "__op": "c",
                    "__table": "inventory_items",
                    "__source_ts_ms": int(time.time() * 1000),
                }
                await js.publish(subject, json.dumps(message, separators=(",", ":")).encode())
                published_messages += 1

            write_stats(stats_file, published_messages)
            next_index += publish_batch_size

            if publish_interval_seconds > 0:
                await asyncio.sleep(publish_interval_seconds)
    finally:
        write_stats(stats_file, published_messages)
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
