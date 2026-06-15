.PHONY: help install validate docs test clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync

validate:  ## Validate AsyncAPI spec (native CLI)
	@$(MAKE) validate-native

validate-native:  ## Validate AsyncAPI spec using native asyncapi CLI
	asyncapi validate asyncapi.yaml

validate-docker:  ## Validate AsyncAPI spec using Docker
	docker run --rm -v /home/jsl/mezcada/poc/johl-nats:/app asyncapi/cli validate /app/asyncapi.yaml

docs-preview:  ## View AsyncAPI documentation with live reload (native CLI)
	@$(MAKE) docs-preview-native

docs-preview-native:  ## View AsyncAPI docs with live reload (native asyncapi CLI)
	@echo "Starting AsyncAPI Studio with live reload (native CLI)..."
	@echo ""
	@echo "Open this URL in your browser:"
	@echo "  http://localhost:3001?liveServer=3001&studio-version=1.2.0"
	@echo ""
	@echo "Edit asyncapi.yaml in VS Code - changes auto-reload in browser!"
	@echo "Press Ctrl+C to stop the server"
	@echo ""
	asyncapi start studio asyncapi.yaml --port 3001

docs-preview-docker:  ## View AsyncAPI docs with live reload (Docker)
	@echo "Starting AsyncAPI Studio with live reload (Docker)..."
	@echo ""
	@echo "Open this URL in your browser:"
	@echo "  http://localhost:3001?liveServer=3001&studio-version=1.2.0"
	@echo ""
	@echo "Edit asyncapi.yaml in VS Code - changes auto-reload in browser!"
	@echo "Press Ctrl+C to stop the server"
	@echo ""
	docker run --rm -it --user=root -p 3001:3001 -v /home/jsl/mezcada/poc/johl-nats:/app -w /app asyncapi/cli start studio /app/asyncapi.yaml --port 3001

docs-generate:  ## Generate static HTML documentation (native CLI)
	@$(MAKE) docs-generate-native

docs-generate-native:  ## Generate static HTML using native asyncapi CLI (requires sudo)
	@echo "Generating HTML documentation with native AsyncAPI CLI..."
	@echo "Note: Requires sudo for template installation"
	@echo ""
	sudo asyncapi generate fromTemplate asyncapi.yaml @asyncapi/html-template -o docs
	@echo ""
	@if [ -f "docs/index.html" ]; then \
		echo "✅ HTML documentation generated at: docs/index.html"; \
	else \
		echo "❌ Generation failed"; \
		exit 1; \
	fi

docs-generate-docker:  ## Generate static HTML using Docker (DEPRECATED - doesn't work with v3)
	@echo "⚠️  Static HTML generation via Docker is currently broken:"
	@echo "  - Generator doesn't support AsyncAPI 3.1.0 yet (only 3.0.0)"
	@echo "  - Template installation fails in Docker environment"
	@echo ""
	@echo "Workaround: Use AsyncAPI Studio web interface"
	@echo "  1. Visit: https://studio.asyncapi.com/"
	@echo "  2. Import asyncapi.yaml"
	@echo "  3. Use File -> Export -> HTML to generate static docs"
	@echo ""
	@echo "Or use 'make docs-generate-native' instead (requires sudo)"
	@exit 1

models-generate:  ## Generate Python Pydantic models from AsyncAPI spec (native CLI)
	@$(MAKE) models-generate-native

models-generate-native:  ## Generate Python Pydantic models using native asyncapi CLI (requires sudo)
	@echo "Generating Python Pydantic models with native AsyncAPI CLI..."
	@echo "✅ Note: Model generation works with AsyncAPI 3.0.0"
	@echo "⚠️  If spec is upgraded to 3.1.0, generation will fail (not yet supported)"
	@echo "Note: Requires sudo for package installation"
	@echo ""
	sudo asyncapi generate models python asyncapi.yaml --packageName=generated_models --pyDantic --output gen_model
	@echo ""
	@if [ -d "gen_model" ] && [ -n "$$(ls -A gen_model 2>/dev/null)" ]; then \
		echo "✅ Python models generated at: gen_model/"; \
		echo "📝 Note: These are auto-generated. Compare with hand-crafted src/models.py"; \
	else \
		echo "⚠️  Model generation failed or produced no output"; \
		echo "Make sure asyncapi.yaml is version 3.0.0 (not 3.1.0)"; \
		echo "Continue using hand-crafted models in src/models.py"; \
	fi

models-generate-docker:  ## Generate Python Pydantic models using Docker
	@echo "Generating Python Pydantic models with Docker..."
	@echo "✅ Note: Model generation works with AsyncAPI 3.0.0"
	@echo "⚠️  If spec is upgraded to 3.1.0, generation will fail (not yet supported)"
	@echo ""
	docker run --rm -v /home/jsl/mezcada/poc/johl-nats:/app -w /app asyncapi/cli generate models python /app/asyncapi.yaml --packageName=generated_models --pyDantic --output /app/gen_model
	@echo ""
	@if [ -d "gen_model" ] && [ -n "$$(ls -A gen_model 2>/dev/null)" ]; then \
		echo "✅ Python models generated at: gen_model/"; \
		echo "📝 Note: These are auto-generated. Compare with hand-crafted src/models.py"; \
	else \
		echo "⚠️  Model generation failed or produced no output"; \
		echo "Make sure asyncapi.yaml is version 3.0.0 (not 3.1.0)"; \
		echo "Continue using hand-crafted models in src/models.py"; \
	fi

client-generate:  ## Generate Python client from AsyncAPI spec (native CLI)
	@$(MAKE) client-generate-native

client-generate-native:  ## Generate Python client using native asyncapi CLI (requires sudo)
	@echo "Generating Python client with native AsyncAPI CLI..."
	@echo "⚠️  WARNING: AsyncAPI Python client generator creates WebSocket clients!"
	@echo "⚠️  This will NOT work for NATS (which uses its own binary protocol)"
	@echo "⚠️  Use hand-crafted code with nats-py instead (see src/)"
	@echo ""
	@echo "Generating anyway for reference (using 'development' server)..."
	@echo "Note: Requires sudo for package installation"
	@echo ""
	sudo asyncapi generate client python asyncapi.yaml --output gen_client --force-write --param server=development
	@echo ""
	@if [ -f "gen_client/client.py" ]; then \
		echo "✅ Python client generated at: gen_client/"; \
		echo "⚠️  NOTE: This is a WebSocket client, not a NATS client!"; \
		echo "📝 For actual NATS usage, see hand-crafted code in src/"; \
	else \
		echo "❌ Client generation failed"; \
		exit 1; \
	fi

client-generate-docker:  ## Generate Python client using Docker (for docker server)
	@echo "Generating Python client with Docker..."
	@echo "⚠️  WARNING: AsyncAPI Python client generator creates WebSocket clients!"
	@echo "⚠️  This will NOT work for NATS (which uses its own binary protocol)"
	@echo "⚠️  Use hand-crafted code with nats-py instead (see src/)"
	@echo ""
	@echo "Generating anyway for reference (using 'docker' server)..."
	@echo ""
	docker run --rm -v /home/jsl/mezcada/poc/johl-nats:/app -w /app asyncapi/cli generate client python /app/asyncapi.yaml --output /app/gen_client --force-write --param server=docker
	@echo ""
	@if [ -f "gen_client/client.py" ]; then \
		echo "✅ Python client generated at: gen_client/"; \
		echo "⚠️  NOTE: This is a WebSocket client, not a NATS client!"; \
		echo "📝 For actual NATS usage, see hand-crafted code in src/"; \
	else \
		echo "❌ Client generation failed"; \
		exit 1; \
	fi


test:  ## Run tests
	uv run pytest tests/ -v

test-cov:  ## Run tests with coverage
	uv run pytest tests/ -v --cov=src --cov-report=term-missing

clean:  ## Clean generated files
	rm -rf docs/ docs_generated/ gen_model/ gen_client/ generated_models/ __pycache__/ .pytest_cache/ *.egg-info/ .venv/ asyncapi-*.0.0.yaml

docker-up:  ## Start all services
	docker-compose up

docker-down:  ## Stop all services
	docker-compose down -v

docker-nats:  ## Start only NATS server
	docker-compose up nats

docker-pubsub:  ## Start pub/sub pattern
	docker-compose up nats subscriber publisher python-subscriber python-publisher

docker-validated:  ## Start validated pub/sub
	docker-compose up nats python-subscriber-validated python-publisher-validated

docker-reqrep:  ## Start request-reply pattern
	docker-compose up nats reply-service request-client

docker-jetstream:  ## Start JetStream pattern
	docker-compose up nats jetstream-publisher jetstream-consumer

docker-mqtt:  ## Start MQTT bridge example
	docker-compose up nats mqtt-subscriber mqtt-publisher

docker-websocket:  ## Start WebSocket bridge example
	docker-compose up nats websocket-subscriber websocket-publisher

docker-bridges:  ## Start all protocol bridge examples
	docker-compose up nats mqtt-subscriber mqtt-publisher websocket-subscriber websocket-publisher
