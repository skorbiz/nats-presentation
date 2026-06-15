"""NATS publisher using Python nats-py client."""

import asyncio
import os

import nats

from .subjects import DEMO_MESSAGES


async def main():
    """Publish messages to demo.messages subject."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"Python Publisher: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("Python Publisher: Connected!")

    # Publish 5 messages
    for i in range(1, 60000):
        message = f"Hello from Python - Message {i}"
        print(f"Python Publisher: Publishing message {i}")
        await nc.publish(DEMO_MESSAGES, message.encode())
        await asyncio.sleep(2)

    print("Python Publisher: Done publishing. Keeping container alive...")
    await nc.close()

    # Keep container alive
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("Python Publisher: Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
