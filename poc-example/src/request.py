"""NATS request-reply pattern: Request client."""

import asyncio
import os

import nats

from .subjects import DEMO_REQUESTS


async def main():
    """Send requests and wait for replies."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"Request Client: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("Request Client: Connected!")

    # Send 5 requests
    for i in range(1, 6):
        message = f"Request {i}"
        print(f"Request Client: Sending request: {message}")

        try:
            # Request with 2 second timeout
            response = await nc.request(DEMO_REQUESTS, message.encode(), timeout=2.0)
            response_data = response.data.decode()
            print(f"Request Client: Received response: {response_data}")
        except TimeoutError:
            print(f"Request Client: Request {i} timed out")

        await asyncio.sleep(1)

    print("Request Client: Done sending requests. Closing connection...")
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
