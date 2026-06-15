"""Publisher with AsyncAPI contract validation using Pydantic models."""

import asyncio
import os
from datetime import UTC, datetime

import nats

from .models import DemoMessagePayload
from .subjects import DEMO_MESSAGES


async def main():
    """Publish validated messages to demo.messages subject."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"Validated Publisher: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("Validated Publisher: Connected!")

    # Publish 5 validated messages
    for i in range(1, 6):
        # Create a validated message using Pydantic model
        message = DemoMessagePayload(text=f"Hello from Validated Publisher - Message {i}", timestamp=datetime.now(UTC))

        # Serialize to JSON
        message_json = message.model_dump_json()

        print(f"Validated Publisher: Publishing validated message {i}")
        await nc.publish(DEMO_MESSAGES, message_json.encode())
        await asyncio.sleep(2)

    print("Validated Publisher: Done publishing. Keeping container alive...")
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
