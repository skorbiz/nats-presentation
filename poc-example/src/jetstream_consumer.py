"""NATS JetStream consumer example."""

import asyncio
import json
import os
import time
from pathlib import Path

import nats
from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy

from .subjects import DEMO_CONSUMER_NAME, DEMO_STREAM_NAME, DEMO_STREAM_WILDCARD


def write_stats(
    stats_path: Path,
    received_messages: int,
    acknowledged_messages: int,
    last_stream_sequence: int | None,
) -> None:
    stats_path.write_text(
        json.dumps(
            {
                "received_messages": received_messages,
                "acknowledged_messages": acknowledged_messages,
                "last_stream_sequence": last_stream_sequence,
                "updated_at_epoch_seconds": time.time(),
            }
        ),
        encoding="utf-8",
    )


async def main():
    """Consume messages from a JetStream stream."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    stream_name = os.getenv("JETSTREAM_STREAM_NAME", DEMO_STREAM_NAME)
    consumer_name = os.getenv("JETSTREAM_CONSUMER_NAME", DEMO_CONSUMER_NAME)
    subject_pattern = os.getenv("JETSTREAM_SUBJECT_PATTERN", DEMO_STREAM_WILDCARD)
    max_messages_raw = os.getenv("JETSTREAM_MAX_MESSAGES", "10")
    max_messages = int(max_messages_raw) if max_messages_raw else 10
    keep_running = os.getenv("JETSTREAM_KEEP_RUNNING", "false").lower() == "true"
    wait_for_stream = os.getenv("JETSTREAM_WAIT_FOR_STREAM", "true").lower() == "true"
    stats_path = Path(os.getenv("JETSTREAM_CONSUMER_STATS_FILE", "/tmp/jetstream_consumer_stats.json"))

    print(f"JetStream Consumer: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("JetStream Consumer: Connected!")

    # Get JetStream context
    js = nc.jetstream()

    if wait_for_stream:
        print(f"JetStream Consumer: Waiting for stream '{stream_name}' to exist...")
        while True:
            try:
                await js.stream_info(stream_name)
                print(f"JetStream Consumer: Stream '{stream_name}' is available")
                break
            except Exception:
                await asyncio.sleep(1)

    print(f"JetStream Consumer: Subscribing to subject '{subject_pattern}' on stream '{stream_name}'...")
    subscription = await js.pull_subscribe(
        subject_pattern,
        durable=consumer_name,
        stream=stream_name,
        config=ConsumerConfig(
            durable_name=consumer_name,
            ack_policy=AckPolicy.EXPLICIT,
            deliver_policy=DeliverPolicy.ALL,
            filter_subject=subject_pattern,
        ),
    )

    # Process messages
    message_count = 0
    acknowledged_count = 0
    last_stream_sequence: int | None = None
    write_stats(stats_path, message_count, acknowledged_count, last_stream_sequence)

    try:
        while keep_running or message_count < max_messages:
            try:
                # Fetch messages (batch of 1, wait up to 5 seconds)
                messages = await subscription.fetch(batch=1, timeout=5)

                for msg in messages:
                    message_count += 1
                    last_stream_sequence = msg.metadata.sequence.stream
                    data = msg.data.decode()
                    print(f"JetStream Consumer: Received message {message_count} on '{msg.subject}'")
                    try:
                        print(json.dumps(json.loads(data), indent=2, sort_keys=True))
                    except json.JSONDecodeError:
                        print(data)
                    print(f"  - Stream sequence: {msg.metadata.sequence.stream}")
                    print(f"  - Consumer sequence: {msg.metadata.sequence.consumer}")

                    # Acknowledge the message
                    await msg.ack()
                    acknowledged_count += 1
                    print("  - Acknowledged")
                    write_stats(
                        stats_path,
                        message_count,
                        acknowledged_count,
                        last_stream_sequence,
                    )

            except TimeoutError:
                print("JetStream Consumer: No messages available (timeout)")
                write_stats(
                    stats_path,
                    message_count,
                    acknowledged_count,
                    last_stream_sequence,
                )
                if keep_running:
                    await asyncio.sleep(1)
                    continue
                break

    except KeyboardInterrupt:
        print("JetStream Consumer: Interrupted")

    write_stats(stats_path, message_count, acknowledged_count, last_stream_sequence)
    print("JetStream Consumer: Closing connection...")
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
