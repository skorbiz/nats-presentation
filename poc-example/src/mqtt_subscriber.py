"""MQTT subscriber demonstrating NATS MQTT bridge.

This subscriber uses standard MQTT protocol to subscribe to NATS subjects.
NATS Server automatically converts between MQTT topics and NATS subjects:
  MQTT topic: "demo/messages" ← NATS subject: "demo.messages"

This subscriber will receive messages from:
- NATS native publishers (using demo.messages subject)
- MQTT publishers (using demo/messages topic)
- Python publishers (using nats-py on demo.messages)
"""

import json

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        print("✅ Connected to NATS MQTT bridge")
        # Subscribe to MQTT topic (maps to NATS subject "demo.messages")
        client.subscribe("demo/messages", qos=0)
        print("📥 Subscribed to demo/messages (NATS subject: demo.messages)")
        print("Waiting for messages... (Ctrl+C to exit)\n")
    else:
        print(f"❌ Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Callback when message is received."""
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📨 Received from {msg.topic}:")
        print(f"   Text: {payload.get('text', 'N/A')}")
        print(f"   Timestamp: {payload.get('timestamp', 'N/A')}")
        print()
    except json.JSONDecodeError:
        print(f"📨 Received raw message from {msg.topic}: {msg.payload.decode()}")
        print()


def main():
    """Subscribe to demo messages via MQTT from NATS."""
    # Create MQTT client (connects to NATS MQTT bridge)
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id="mqtt-subscriber",
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to NATS MQTT bridge
    # Use environment variable for host (Docker: nats, local: localhost)
    import os

    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    print(f"Connecting to NATS MQTT bridge at {mqtt_host}:1883...")
    client.connect(mqtt_host, 1883, 60)

    # Block and process messages
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n✅ MQTT subscriber stopped")
        client.disconnect()


if __name__ == "__main__":
    main()
