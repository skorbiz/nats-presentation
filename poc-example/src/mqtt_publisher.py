"""MQTT publisher demonstrating NATS MQTT bridge.

This publisher uses standard MQTT protocol to publish messages to NATS subjects.
NATS Server automatically converts MQTT topics to NATS subjects:
  MQTT topic: "demo/messages" → NATS subject: "demo.messages"
"""

import json
import time
from datetime import UTC, datetime

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        print("✅ Connected to NATS MQTT bridge")
    else:
        print(f"❌ Connection failed with code {rc}")


def on_publish(client, userdata, mid, reason_code=None, properties=None):
    """Callback when message is published."""
    print(f"✅ Published message {mid}")


def main():
    """Publish demo messages via MQTT to NATS."""
    # Create MQTT client (connects to NATS MQTT bridge)
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id="mqtt-publisher",
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Connect to NATS MQTT bridge
    # Use environment variable for host (Docker: nats, local: localhost)
    import os

    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    print(f"Connecting to NATS MQTT bridge at {mqtt_host}:1883...")
    client.connect(mqtt_host, 1883, 60)
    client.loop_start()

    # Give connection time to establish
    time.sleep(1)

    # Publish 5 messages
    # MQTT topic "demo/messages" → NATS subject "demo.messages"
    for i in range(1, 6):
        payload = {
            "text": f"Hello from MQTT client - Message {i}",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        _ = client.publish(  # noqa: F841
            topic="demo/messages",  # Maps to NATS subject "demo.messages"
            payload=json.dumps(payload),
            qos=0,  # Fire and forget (NATS core-like)
        )

        print(f"📤 Published to demo/messages: {payload['text']}")
        time.sleep(1)

    # Clean up
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("\n✅ MQTT publisher completed")


if __name__ == "__main__":
    main()
