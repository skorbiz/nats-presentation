# NATS AsyncAPI POC

This is a POC for learning NATS and NATS JetStream with contract-first development using AsyncAPI.

**AsyncAPI** is to event-driven/asynchronous APIs what OpenAPI (Swagger) is to REST APIs. It provides a machine-readable specification for defining channels, messages, schemas, and enables auto-generated documentation and runtime validation.

This project uses **uv** for dependency management, following the Mezcada codebase conventions.

## Project Structure

```ls
nats-asyncapi-poc/
├── asyncapi.yaml              # AsyncAPI 3.1.0 specification
├── README.md                  # This file
├── Makefile                  # Common commands
├── pyproject.toml            # Project configuration
├── uv.lock                   # Locked dependencies
├── docker-compose.yml        # Multi-pattern demo setup
├── Dockerfile                # Container image for Python services
├── nats.conf                 # NATS server configuration
├── asyncapi-tools.sh         # Validation and doc generation script
├── src/                      # Source code
│   ├── __init__.py
│   ├── subjects.py           # Subject constants from AsyncAPI
│   ├── models.py             # Pydantic models from AsyncAPI schemas
│   ├── publisher.py          # Simple pub/sub publisher
│   ├── subscriber.py         # Simple pub/sub subscriber
│   ├── publisher_validated.py   # Publisher with schema validation
│   ├── subscriber_validated.py  # Subscriber with schema validation
│   ├── request.py            # Request-reply client
│   ├── reply.py              # Request-reply service
│   ├── jetstream_publisher.py   # JetStream publisher
│   └── jetstream_consumer.py    # JetStream consumer
├── tests/                    # Test suite
│   ├── __init__.py
│   └── test_contract.py      # AsyncAPI contract tests
```

## Docker Compose Setup

This POC includes a Docker Compose setup with multiple NATS patterns:

### Core Infrastructure

- **NATS Server**: Running with JetStream enabled, configured via [nats.conf](nats.conf)
  - Client connections: `localhost:4222`
  - HTTP monitoring: `localhost:8222`
  - Persistent JetStream data storage

### Pub/Sub Pattern

- **Subscriber** (CLI): Listens to `demo.messages` subject using nats-box CLI
- **Publisher** (CLI): Publishes 5 messages to `demo.messages` subject using nats-box CLI
- **Python Subscriber**: Listens to `demo.messages` subject using nats-py Python client
- **Python Publisher**: Publishes 5 messages to `demo.messages` subject using nats-py Python client

### Request-Reply Pattern

- **Reply Service**: Listens for requests on `demo.requests` and sends replies
- **Request Client**: Sends 5 requests and waits for replies

### JetStream Pattern (Persistent Messaging)

- **JetStream Publisher**: Creates a stream `DEMO_STREAM` and publishes persistent messages
- **JetStream Consumer**: Python-based durable consumer using `nats-py`

### Debezium CDC to JetStream

This POC now includes an optional **CDC profile** that streams PostgreSQL row changes into NATS JetStream by using **Debezium Server**.

- **Postgres CDC**: A small PostgreSQL 16 instance with logical replication enabled
- **Persistent Storage**: PostgreSQL data and Debezium offsets are stored in Docker volumes
- **Postgres Bootstrap**: Creates `public.inventory_items` and inserts one starter row
- **Postgres Writer**: Continuously inserts demo rows so Debezium always has changes to capture
- **Debezium Server**: Captures changes from PostgreSQL and publishes them to JetStream subjects under `demo_cdc.>`
- **JetStream CDC Consumer**: Long-running Python consumer with environment-driven stream and subject settings
- **JetStream CDC CLI Consumer**: Long-running Bash/CLI consumer using `nats-box` and `nats consumer next`

Run the CDC demo with:

```bash
docker compose --profile cdc up --build
```

If you want a clean rerun of the CDC demo, remove the CDC volumes first:

```bash
docker compose --profile cdc down -v
```

That clears both the PostgreSQL data volume and the Debezium offset volume, so the demo starts from a fresh snapshot again.

The CDC-specific services are:

- `postgres-cdc`
- `postgres-bootstrap`
- `postgres-writer`
- `debezium-server`
- `jetstream-consumer-cdc`
- `jetstream-consumer-cli`

The Debezium configuration is defined directly on the `debezium-server` service in [docker-compose.yml](/workspaces/mezcada/poc/johl-nats/docker-compose.yml:257). The old `application.properties` approach is no longer used.

### Performance Profiling

For this POC, the most practical first measurements are:

- **Container CPU**: `docker stats` for `nats`, `debezium-server`, `postgres-cdc`, and the consumers
- **Container memory**: resident memory and percentage from `docker stats`
- **Container network I/O**: bytes sent and received per container from `docker stats`
- **NATS internals**: connection, JetStream, and server stats from the built-in HTTP monitoring endpoint on `localhost:8222`

Run the included capture script from [scripts/profile_cdc.py](scripts/profile_cdc.py):

```bash
python3 ./scripts/profile_cdc.py 60 5
```

That captures:

- `docker-stats.csv`: point-in-time CPU, memory, network, block I/O, and PID counts
- `nats-varz.ndjson`: NATS server counters and memory info
- `nats-connz.ndjson`: NATS connection snapshots
- `nats-jsz.ndjson`: JetStream stream and consumer snapshots

By default, the script:

- starts the CDC profile with `docker compose --profile cdc up -d --build`
- samples for `60` seconds
- records one sample every `5` seconds
- stores the output under `profiles/<timestamp>/`

### Increasing Transmitted Data

The `postgres-writer` service is now parameterized, and the profiler script sets those values for you directly in [scripts/profile_cdc.py](scripts/profile_cdc.py).

The main load settings are:

- `WRITER_INSERT_INTERVAL_SECONDS`: seconds between batches
- `WRITER_BATCH_SIZE`: number of rows inserted per loop
- `WRITER_PAYLOAD_BYTES`: extra payload bytes written into each row
- `WRITER_START_DELAY_SECONDS`: initial delay before writing begins

The writer now uses a persistent Python/PostgreSQL connection with one batched insert per loop, which is much more realistic for throughput testing than spawning `psql` for every row.

Suggested baseline and higher-load values now live as comments in the script itself, right next to the active settings, so it is easier to tweak and re-run in one place.

### Protocol Bridges (MQTT & WebSocket)

NATS Server has **built-in protocol bridges** that allow external systems to interact with NATS using other protocols:

#### MQTT Bridge (Port 1883)

- **Native MQTT 3.1.1 support** built into NATS Server
- **Bidirectional** - MQTT clients can publish and subscribe to NATS subjects
- **Automatic topic mapping**: MQTT topics (`demo/messages`) → NATS subjects (`demo.messages`)
- **Examples**:
  - [src/mqtt_publisher.py](src/mqtt_publisher.py) - Publish via MQTT to NATS
  - [src/mqtt_subscriber.py](src/mqtt_subscriber.py) - Subscribe via MQTT to NATS messages

#### WebSocket Bridge (Port 8080)

- **Full NATS protocol over WebSocket** - not just a subset
- **Browser-compatible** - JavaScript clients can use full NATS features
- **nats-py supports WebSocket** - `ws://localhost:8080`
- **Examples**:
  - [src/websocket_publisher.py](src/websocket_publisher.py) - Publish via WebSocket
  - [src/websocket_subscriber.py](src/websocket_subscriber.py) - Subscribe via WebSocket

**Why this matters:**

- IoT devices using MQTT can publish to NATS without code changes
- Browser applications can consume NATS messages via WebSocket
- External systems don't need NATS-specific clients
- All protocols share the same message stream (publish MQTT → receive on NATS native, or vice versa)

#### Protocols NOT Natively Supported

The following protocols require **separate adapter/bridge services** (not included in this POC):

- **REST/HTTP**: Would need a REST API service (e.g., FastAPI) that subscribes to NATS and exposes HTTP endpoints
- **RabbitMQ**: Requires a separate message bridge service (different broker, not a protocol)
- **OPC-UA**: Needs an industrial protocol gateway
- **Kafka**: Requires a bridge service (e.g., nats-kafka-connector)

NATS Server only includes MQTT and WebSocket natively. For other protocols, you'd build microservices that:

1. Subscribe to NATS subjects
2. Expose data via the desired protocol (REST, OPC-UA, etc.)

#### Testing the Protocol Bridges

**MQTT Bridge** — Successfully tested ✅

- NATS Server listening on `mqtt://0.0.0.0:1883`
- MQTT clients connect using standard MQTT 3.1.1 protocol
- Topic mapping: `demo/messages` (MQTT) ↔ `demo.messages` (NATS)
- Cross-protocol: MQTT publisher → NATS subscriber works perfectly
- See [src/mqtt_publisher.py](src/mqtt_publisher.py) and [src/mqtt_subscriber.py](src/mqtt_subscriber.py)

**WebSocket Bridge** — Enabled ✅

- NATS Server listening on `ws://0.0.0.0:8080`
- Full NATS protocol over WebSocket (not just pub/sub)
- Browser-compatible for JavaScript clients
- nats-py supports WebSocket via `ws://` URL scheme
- See [src/websocket_publisher.py](src/websocket_publisher.py) and [src/websocket_subscriber.py](src/websocket_subscriber.py)
- Browser client available: [websocket-client.html](websocket-client.html) — open in browser to test

**Test Results:**

```txt
✅ MQTT → NATS: Published 5 messages successfully
✅ NATS → MQTT: Subscriber received all messages
✅ WebSocket enabled and listening on port 8080
✅ Cross-protocol communication verified
```

### AsyncAPI Contract-First Development

This POC includes an **AsyncAPI specification** that defines the message contracts for all NATS patterns.

- **[asyncapi.yaml](asyncapi.yaml)**: Complete API specification for all channels, messages, and schemas
- **[src/models.py](src/models.py)**: Pydantic models generated from the AsyncAPI spec for runtime validation
- **[src/subjects.py](src/subjects.py)**: Subject constants matching the AsyncAPI spec
- **[src/publisher_validated.py](src/publisher_validated.py)**: Publisher that validates messages against the schema
- **[src/subscriber_validated.py](src/subscriber_validated.py)**: Subscriber that validates received messages
- **[tests/test_contract.py](tests/test_contract.py)**: Pytest tests for payload validation

**Benefits:**

- 📝 **Documentation**: Auto-generated HTML docs from the spec, always in sync with code
- ✅ **Validation**: Runtime payload validation using Pydantic
- 🔒 **Type Safety**: Strong typing with full IDE support and type checking
- 🧪 **Testing**: Contract testing to ensure producer/consumer compatibility

## AsyncAPI Workflow

### What is Included

The [asyncapi.yaml](asyncapi.yaml) specification defines:

- **Servers**: Development (localhost) and Docker (nats:4222)
- **Channels**: `demo.messages`, `demo.requests`, `demo.stream.data`
- **Messages**: DemoMessage, Request, Response, StreamMessage with JSON Schema definitions
- **Operations**: publish, subscribe, send, receive actions

From this specification, we generate:

- **[src/models.py](src/models.py)**: Pydantic models with automatic validation and JSON serialization
- **[src/subjects.py](src/subjects.py)**: Subject name constants ensuring consistency
- **HTML Documentation**: Via AsyncAPI Studio (live preview or web export)

### Development Workflow

**1. Define the Contract:**

Edit [asyncapi.yaml](asyncapi.yaml) to add new messages or channels:

```yaml
components:
  messages:
    MyNewMessage:
      payload:
        type: object
        properties:
          field1:
            type: string
          field2:
            type: integer
        required:
          - field1
```

**2. Validate the Spec:**

```bash
./asyncapi-tools.sh
# or
make validate
```

**3. Update Models:**

Update [src/models.py](src/models.py) to match the spec:

```python
class MyNewMessagePayload(BaseModel):
    field1: str
    field2: int | None = None
```

**4. Write Tests:**

Add tests in [tests/test_contract.py](tests/test_contract.py):

```python
def test_my_new_message():
    payload = MyNewMessagePayload(field1="test", field2=42)
    assert payload.field1 == "test"
```

**5. Implement Publishers/Subscribers:**

Use the validated models:

```python
from src.models import MyNewMessagePayload
from src.subjects import MY_SUBJECT

# In publisher
msg = MyNewMessagePayload(field1="data")
await nc.publish(MY_SUBJECT, msg.model_dump_json().encode())

# In subscriber
payload_dict = json.loads(msg.data.decode())
validated = MyNewMessagePayload.model_validate(payload_dict)
```

### Example Usage

```python
from src.models import DemoMessagePayload
from datetime import datetime, UTC

# Create and validate
msg = DemoMessagePayload(
    text="Hello",
    timestamp=datetime.now(UTC)
)

# Serialize to JSON
json_str = msg.model_dump_json()

# Deserialize and validate
validated = DemoMessagePayload.model_validate_json(json_str)
```

### Best Practices

1. **Version your spec**: Use semantic versioning in `info.version`
2. **Document everything**: Add descriptions to all channels, messages, and fields
3. **Provide examples**: Include example payloads in the spec
4. **Test the contract**: Write tests that validate against the schema
5. **Keep models in sync**: Regenerate models when the spec changes
6. **Use validation**: Always validate payloads in production code

**AsyncAPI Tooling:**

Install AsyncAPI CLI (requires Node.js):

View interactive documentation:

**Option 1: Native AsyncAPI CLI (recommended if installed):**

Install AsyncAPI CLI:

```bash
# Using npm
npm install -g @asyncapi/cli

# Or using Debian packages (if available)
# apt-get install asyncapi
```

Then run:

```bash
make docs-preview-native
# Or just: make docs-preview (defaults to native)
# Opens at http://localhost:3001?liveServer=3001&studio-version=1.2.0
# Edit asyncapi.yaml in VS Code for live updates!
```

**Option 2: Docker (no local installation needed):**

```bash
make docs-preview-docker
# Opens at http://localhost:3001?liveServer=3001&studio-version=1.2.0
# Edit asyncapi.yaml in VS Code for live updates!
```

**Generate Static HTML:**

```bash
# Using native AsyncAPI CLI (requires sudo for template installation)
make docs-generate-native
# Generates HTML at docs/index.html

# Or use the default (calls native version)
make docs-generate

# Docker version is broken for AsyncAPI 3.1.0
# make docs-generate-docker  # Currently doesn't work
```

**Alternative: AsyncAPI Studio (web-based)**  
Visit [https://studio.asyncapi.com/](https://studio.asyncapi.com/) and paste your spec content, then export as HTML.

**Generate Python Pydantic Models:**

**✅ Recommended Approach: Extract schemas → Generate models:**

This two-step workflow produces high-quality Pydantic models:

```bash
# Step 1: Extract JSON schemas from AsyncAPI spec
make schemas-extract
# Creates gen_schemas/ directory with JSON schema files

# Step 2: Generate Pydantic models from JSON schemas
make models-from-schemas
# Creates gen_pydantic_models.py with properly-typed models

# Or run both steps at once:
make models-generate-better
```

**Why this is better than `make models-generate`:**

- ✅ Uses `AwareDatetime` instead of `str` for timestamps (proper type safety!)
- ✅ Clean code without serializer/validator boilerplate
- ✅ Named classes (`Priority`, `Metadata`) instead of `AnonymousSchema11`
- ✅ Proper required vs optional field handling
- ✅ Works consistently, no experimental warnings

**Alternative: Direct AsyncAPI model generation (not recommended):**

```bash
# Using native AsyncAPI CLI (requires sudo for package installation)
make models-generate-native
# Generates models in gen_model/

# Or using Docker
make models-generate-docker
```

**Note:** AsyncAPI's built-in Python model generator produces lower-quality code with anonymous schemas, string timestamps, and verbose boilerplate. Use the schema extraction approach above instead.

**✅ Note about Model Generation:**
Model generation **works with AsyncAPI 3.0.0** (current spec version). The recommended workflow extracts JSON schemas first, then uses `datamodel-code-generator` to produce clean, properly-typed Pydantic models.

**⚠️ Important:** If you upgrade the spec to AsyncAPI 3.1.0, the direct AsyncAPI model generation will fail (generator doesn't support 3.1.0 yet). The schema extraction workflow should continue to work.

**Generate Python Client (Experimental, Not NATS-Compatible):**

```bash
# Using native AsyncAPI CLI (requires sudo)
make client-generate-native
# Generates client in gen_client/

# Or use the default (calls native version)
make client-generate

# Or using Docker (uses 'docker' server instead of 'development')
make client-generate-docker
```

**⚠️ CRITICAL LIMITATION:**
The AsyncAPI Python client generator creates **WebSocket clients only**, not NATS clients. The generated code attempts to connect using `websocket` library to `nats://localhost:4222`, which **will not work** because NATS uses its own binary protocol.

**For actual NATS usage:** Use the hand-crafted code in `src/` which properly uses `nats-py`. The generated client is only useful as a reference to see what AsyncAPI client generation produces.

**AsyncAPI CLI Commands:**

```bash
# Validate spec (native CLI)
make validate-native

# Validate spec (Docker)
make validate-docker

# Preview with live reload (native CLI)
make docs-preview-native

# Preview with live reload (Docker)
make docs-preview-docker

# Generate static HTML (native CLI with sudo)
make docs-generate-native

# Generate Python models (native CLI with sudo)
make models-generate-native

# Default targets use native CLI
make validate
make docs-preview
make docs-generate
make models-generate
```

## Quick Commands (Makefile)

Common tasks are available via `make`:

```bash
make help                   # Show all available commands
make install                # Install dependencies with uv
make test                   # Run tests
make validate               # Validate AsyncAPI spec (native CLI)
make validate-native        # Validate with native asyncapi CLI
make validate-docker        # Validate with Docker
make docs-preview           # View docs with live reload (native CLI)
make docs-preview-native    # View docs with live reload (native CLI)
make docs-preview-docker    # View docs with live reload (Docker)
make docs-generate          # Generate static HTML (native CLI, requires sudo)
make docs-generate-native   # Generate static HTML (native CLI, requires sudo)
make schemas-extract        # Extract JSON schemas from AsyncAPI spec
make models-from-schemas    # Generate Pydantic models from JSON schemas
make models-generate-better # Extract schemas + generate models (RECOMMENDED)
make models-generate        # Generate Python Pydantic models (native CLI, requires sudo)
make models-generate-native # Generate Python models (native CLI, requires sudo)
make models-generate-docker # Generate Python models (Docker)
make client-generate        # Generate Python client - WebSocket only! (native CLI, requires sudo)
make client-generate-native # Generate Python client - WebSocket only! (native CLI, requires sudo)
make client-generate-docker # Generate Python client - WebSocket only! (Docker)
make docker-up              # Start all services
make docker-nats            # Start only NATS server
make docker-validated       # Start validated pub/sub
make docker-mqtt            # Start MQTT bridge example
make docker-websocket       # Start WebSocket bridge example
make docker-bridges         # Start all protocol bridge examples
```

### Running the POC

Start all services (including protocol bridges):

```bash
docker-compose up
```

You'll see:

- **Pub/Sub**: Both CLI and Python subscribers receiving messages from publishers
- **Request-Reply**: Request client sending requests and receiving replies
- **JetStream**: Publisher creating a stream and consumer processing persistent messages
- **MQTT Bridge**: MQTT subscriber receiving messages from MQTT publisher
- **WebSocket Bridge**: WebSocket subscriber receiving messages from WebSocket publisher

#### Run specific patterns

```bash
# Only MQTT bridge
make docker-mqtt

# Only WebSocket bridge
make docker-websocket

# All protocol bridges
make docker-bridges
```

#### Cross-Protocol Communication

The protocol bridges allow **cross-protocol pub/sub**. For example:

1. Start MQTT subscriber: `docker-compose up nats mqtt-subscriber`
2. In another terminal, publish via native NATS: `uv run python src/publisher.py`
3. The MQTT subscriber will receive messages from the native NATS publisher!

This works in any combination:

- MQTT publish → NATS subscribe
- NATS publish → WebSocket subscribe
- WebSocket publish → MQTT subscribe
- etc.

Run specific patterns:

```bash
# Only pub/sub pattern
docker-compose up nats subscriber publisher python-subscriber python-publisher

# Pub/sub with validation
docker-compose up nats python-subscriber-validated python-publisher-validated

# Only request-reply pattern
docker-compose up nats reply-service request-client

# Only JetStream pattern
docker-compose up nats jetstream-publisher jetstream-consumer
```

### Python Scripts

**Pub/Sub Pattern:**

- **[src/subscriber.py](src/subscriber.py)**: Async subscriber using nats-py
- **[src/publisher.py](src/publisher.py)**: Async publisher using nats-py
- **[src/subscriber_validated.py](src/subscriber_validated.py)**: Subscriber with AsyncAPI schema validation
- **[src/publisher_validated.py](src/publisher_validated.py)**: Publisher with AsyncAPI schema validation

**Request-Reply Pattern:**

- **[src/reply.py](src/reply.py)**: Reply service that processes requests
- **[src/request.py](src/request.py)**: Request client that sends requests and waits for replies

**JetStream Pattern:**

- **[src/jetstream_publisher.py](src/jetstream_publisher.py)**: Creates a stream and publishes persistent messages
- **[src/jetstream_consumer.py](src/jetstream_consumer.py)**: Durable consumer that processes stream messages

**AsyncAPI & Models:**

- **[asyncapi.yaml](asyncapi.yaml)**: AsyncAPI 3.0 specification defining all message contracts
- **[src/models.py](src/models.py)**: Pydantic models for runtime validation
- **[src/subjects.py](src/subjects.py)**: Subject name constants from AsyncAPI spec
- **[tests/test_contract.py](tests/test_contract.py)**: Pytest tests for payload validation
- **[asyncapi-tools.sh](asyncapi-tools.sh)**: Script to validate spec and generate docs

**Configuration:**

- **[pyproject.toml](pyproject.toml)**: Project configuration and dependencies
- **[uv.lock](uv.lock)**: Locked dependencies for reproducible builds
- **[nats.conf](nats.conf)**: NATS server configuration (JetStream, limits, monitoring)

### Local Development

Install dependencies using uv:

```bash
uv sync
```

Start just the NATS server:

```bash
docker-compose up nats
```

Run examples locally (requires NATS server running on localhost:4222):

**Pub/Sub:**

```bash
uv run python src/subscriber.py # Terminal 1
uv run python src/publisher.py  # Terminal 2

# Or with validation:
uv run python src/subscriber_validated.py # Terminal 1
uv run python src/publisher_validated.py  # Terminal 2
```

**Request-Reply:**

```bash
uv run python src/reply.py   # Terminal 1
uv run python src/request.py # Terminal 2
```

**JetStream:**

```bash
uv run python src/jetstream_publisher.py # Terminal 1
uv run python src/jetstream_consumer.py  # Terminal 2
```

**Run Tests:**

```bash
uv run pytest tests/ -v
# or
make test
```

### Monitoring

Access the NATS monitoring interface at [http://localhost:8222](http://localhost:8222)

### Manual Testing

Publish a message using CLI:

```bash
docker-compose exec publisher nats pub demo.messages "Manual test message"
```

Subscribe using CLI in a new terminal:

```bash
docker-compose exec subscriber nats sub demo.messages
```

Run Python publisher manually:

```bash
docker-compose exec python-publisher python publisher.py
```

Run Python subscriber in interactive mode:

```bash
doc

## Resources

- [AsyncAPI Specification](https://www.asyncapi.com/docs/reference/specification/v3.0.0)
- [AsyncAPI CLI Documentation](https://www.asyncapi.com/docs/tools/cli)
- [NATS Documentation](https://docs.nats.io/)
- [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [nats.py Client](https://github.com/nats-io/nats.py)ker-compose run --rm python-subscriber python -c "
import asyncio
from subscriber import main
asyncio.run(main())
"
```

### Cleanup

```bash
docker-compose down
```
