"""WebSocket publisher demonstrating NATS WebSocket support.

This publisher connects to NATS Server via WebSocket protocol.
Useful for browser-based applications that need to publish NATS messages.

The NATS protocol runs over WebSocket, so you get full NATS functionality.
"""

import asyncio
import json
import os
from datetime import UTC, datetime

from nats.aio.client import Client as NATS


async def main():
    """Publish demo messages via WebSocket to NATS."""
    nc = NATS()

    try:
        # Connect to NATS via WebSocket
        # Use environment variable for host (Docker: nats, local: localhost)
        ws_host = os.getenv("WS_HOST", "localhost")
        print(f"Connecting to NATS WebSocket at ws://{ws_host}:8080...")
        await nc.connect(servers=[f"ws://{ws_host}:8080"])
        print("✅ Connected to NATS via WebSocket\n")

        # Publish 5 messages
        for i in range(1, 6):
            payload = {
                "text": f"Hello from WebSocket client - Message {i}",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            await nc.publish("demo.messages", json.dumps(payload).encode())
            print(f"📤 Published to demo.messages: {payload['text']}")
            await asyncio.sleep(1)

        print("\n✅ WebSocket publisher completed")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if nc.is_connected:
            await nc.drain()
            await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
