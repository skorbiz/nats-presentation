"""Subscriber with AsyncAPI contract validation using Pydantic models."""

import asyncio
import json
import os

import nats
from pydantic import ValidationError

from .models import DemoMessagePayload
from .subjects import DEMO_MESSAGES


async def main():
    """Subscribe to demo.messages with payload validation."""
    nats_server = os.getenv("NATS_SERVER", "nats://localhost:4222")
    print(f"Validated Subscriber: Connecting to NATS server at {nats_server}...")
    nc = await nats.connect(nats_server)
    print("Validated Subscriber: Connected!")

    async def message_handler(msg):
        subject = msg.subject
        data = msg.data.decode()

        try:
            # Parse and validate the message against the AsyncAPI schema
            payload_dict = json.loads(data)
            validated_message = DemoMessagePayload.model_validate(payload_dict)

            print(f"Validated Subscriber: ✓ Valid message on '{subject}':")
            print(f"  - Text: {validated_message.text}")
            print(f"  - Timestamp: {validated_message.timestamp}")
        except json.JSONDecodeError as e:
            print(f"Validated Subscriber: ✗ Invalid JSON: {e}")
        except ValidationError as e:
            print("Validated Subscriber: ✗ Schema validation failed:")
            for error in e.errors():
                print(f"  - {error['loc']}: {error['msg']}")

    # Subscribe to the subject
    await nc.subscribe(DEMO_MESSAGES, cb=message_handler)
    print(f"Validated Subscriber: Subscribed to '{DEMO_MESSAGES}' with validation")

    # Keep the subscriber running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("Validated Subscriber: Shutting down...")
    finally:
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
