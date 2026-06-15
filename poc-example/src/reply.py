"""NATS request-reply pattern: Reply service."""

import asyncio
import os

import nats

from .subjects import DEMO_REQUESTS


async def main():
    """Listen for requests and send replies."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"Reply Service: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("Reply Service: Connected!")

    async def request_handler(msg):
        """Handle incoming requests."""
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print(f"Reply Service: Received request on '{subject}': {data}")

        # Process the request and send a reply
        response = f"Processed: {data}"
        await nc.publish(reply, response.encode())
        print(f"Reply Service: Sent reply: {response}")

    # Subscribe to the request subject
    await nc.subscribe(DEMO_REQUESTS, cb=request_handler)
    print(f"Reply Service: Listening for requests on '{DEMO_REQUESTS}'")

    # Keep the service running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("Reply Service: Shutting down...")
    finally:
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
