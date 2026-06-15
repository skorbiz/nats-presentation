"""WebSocket subscriber demonstrating NATS WebSocket support.

This subscriber connects to NATS Server via WebSocket protocol.
Useful for browser-based applications that need to consume NATS messages.

The NATS protocol runs over WebSocket, so you get full NATS functionality
(subjects, wildcards, etc.) from a browser or any WebSocket client.
"""

import asyncio
import json
import os

from nats.aio.client import Client as NATS


async def main():
    """Subscribe to demo messages via WebSocket from NATS."""
    nc = NATS()

    async def message_handler(msg):
        """Handle incoming messages."""
        try:
            payload = json.loads(msg.data.decode())
            print(f"📨 Received from {msg.subject}:")
            print(f"   Text: {payload.get('text', 'N/A')}")
            print(f"   Timestamp: {payload.get('timestamp', 'N/A')}")
            print()
        except json.JSONDecodeError:
            print(f"📨 Received raw message from {msg.subject}: {msg.data.decode()}")
            print()

    try:
        # Connect to NATS via WebSocket
        # Use environment variable for host (Docker: nats, local: localhost)
        ws_host = os.getenv("WS_HOST", "localhost")
        print(f"Connecting to NATS WebSocket at ws://{ws_host}:8080...")
        await nc.connect(servers=[f"ws://{ws_host}:8080"])
        print("✅ Connected to NATS via WebSocket")

        # Subscribe to demo messages
        await nc.subscribe("demo.messages", cb=message_handler)
        print("📥 Subscribed to demo.messages")
        print("Waiting for messages... (Ctrl+C to exit)\n")

        # Keep alive
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n✅ WebSocket subscriber stopped")
    finally:
        if nc.is_connected:
            await nc.drain()
            await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
