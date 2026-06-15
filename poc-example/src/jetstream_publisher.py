"""NATS JetStream publisher example."""

import asyncio
import os

import nats
from nats.js.api import RetentionPolicy, StorageType

from .subjects import DEMO_STREAM_DATA, DEMO_STREAM_NAME, DEMO_STREAM_WILDCARD


async def main():
    """Publish messages to a JetStream stream."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"JetStream Publisher: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("JetStream Publisher: Connected!")

    # Get JetStream context
    js = nc.jetstream()

    # Create or update stream
    stream_name = DEMO_STREAM_NAME
    try:
        await js.add_stream(
            name=stream_name,
            subjects=[DEMO_STREAM_WILDCARD],
            retention=RetentionPolicy.LIMITS,  # Delete old messages based on limits
            storage=StorageType.FILE,  # Persist to disk
            max_msgs=1000,  # Maximum number of messages
            max_bytes=1024 * 1024,  # 1MB max size
            max_age=3600,  # Keep messages for 1 hour (in seconds)
        )
        print(f"JetStream Publisher: Created stream '{stream_name}'")
    except Exception as e:
        print(f"JetStream Publisher: Stream might already exist: {e}")

    # Publish messages to the stream
    for i in range(1, 6):
        message = f"JetStream message {i}"
        print(f"JetStream Publisher: Publishing: {message}")

        # Publish and wait for acknowledgment
        ack = await js.publish(DEMO_STREAM_DATA, message.encode())
        print(f"JetStream Publisher: Published with sequence {ack.seq}")

        await asyncio.sleep(1)

    print("JetStream Publisher: Done publishing. Closing connection...")
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
