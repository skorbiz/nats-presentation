"""NATS subscriber using Python nats-py client."""

import asyncio
import os

import nats

from .subjects import DEMO_MESSAGES


async def main():
    """Subscribe to demo.messages subject."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"Python Subscriber: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("Python Subscriber: Connected!")

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data.decode()
        print(f"Python Subscriber: Received message on '{subject}': {data}")

    # Subscribe to the subject
    await nc.subscribe(DEMO_MESSAGES, cb=message_handler)
    print(f"Python Subscriber: Subscribed to '{DEMO_MESSAGES}'")

    # Keep the subscriber running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("Python Subscriber: Shutting down...")
    finally:
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
