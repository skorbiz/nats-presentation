"""Tests for message payload validation against AsyncAPI spec."""

from datetime import UTC, datetime

import pytest
from models import (
    DemoMessagePayload,
    MessageMetadata,
    Priority,
    RequestPayload,
    ResponsePayload,
    StreamMessagePayload,
)
from pydantic import ValidationError


class TestDemoMessagePayload:
    """Test DemoMessagePayload validation."""

    def test_valid_message(self):
        """Valid message should pass validation."""
        payload = DemoMessagePayload(text="Hello NATS", timestamp=datetime.now(UTC))

        assert payload.text == "Hello NATS"
        assert isinstance(payload.timestamp, datetime)

    def test_missing_text(self):
        """Missing required text field should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DemoMessagePayload.model_validate({"timestamp": datetime.now(UTC)})

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("text",) for error in errors)

    def test_missing_timestamp(self):
        """Missing required timestamp field should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DemoMessagePayload.model_validate({"text": "Hello"})

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp",) for error in errors)

    def test_invalid_timestamp(self):
        """Invalid timestamp format should fail."""
        with pytest.raises(ValidationError) as exc_info:
            DemoMessagePayload(text="Hello", timestamp="not-a-date")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp",) for error in errors)


class TestRequestResponsePayload:
    """Test Request and Response payload validation."""

    def test_valid_request(self):
        """Valid request should pass validation."""
        payload = RequestPayload(request_id="req-001", data="Process this", timestamp=datetime.now(UTC))

        assert payload.request_id == "req-001"
        assert payload.data == "Process this"

    def test_valid_response(self):
        """Valid response should pass validation."""
        payload = ResponsePayload(request_id="req-001", result="Done", timestamp=datetime.now(UTC))

        assert payload.request_id == "req-001"
        assert payload.result == "Done"

    def test_request_missing_id(self):
        """Request without ID should fail."""
        with pytest.raises(ValidationError) as exc_info:
            RequestPayload.model_validate({"data": "Process this", "timestamp": datetime.now(UTC)})

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("request_id",) for error in errors)


class TestStreamMessagePayload:
    """Test StreamMessagePayload validation."""

    def test_valid_stream_message(self):
        """Valid stream message should pass validation."""
        metadata = MessageMetadata(source="publisher-1", priority=Priority.NORMAL)
        payload = StreamMessagePayload(
            message_id="msg-001", data="Stream data", metadata=metadata, timestamp=datetime.now(UTC)
        )

        assert payload.message_id == "msg-001"
        assert payload.metadata.source == "publisher-1"
        assert payload.metadata.priority == Priority.NORMAL

    def test_invalid_priority(self):
        """Invalid priority value should fail."""
        with pytest.raises(ValidationError) as exc_info:
            MessageMetadata(source="publisher-1", priority="invalid")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("priority",) for error in errors)

    def test_default_priority(self):
        """Priority should default to NORMAL if not specified."""
        metadata = MessageMetadata(source="publisher-1")

        assert metadata.priority == Priority.NORMAL

    def test_missing_metadata(self):
        """Missing metadata should fail."""
        with pytest.raises(ValidationError) as exc_info:
            StreamMessagePayload.model_validate(
                {"message_id": "msg-001", "data": "Stream data", "timestamp": datetime.now(UTC)}
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("metadata",) for error in errors)


class TestJsonSerialization:
    """Test JSON serialization and deserialization."""

    def test_serialize_deserialize_demo_message(self):
        """Message should survive JSON round-trip."""
        original = DemoMessagePayload(text="Hello", timestamp=datetime.now(UTC))

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize from JSON
        restored = DemoMessagePayload.model_validate_json(json_str)

        assert restored.text == original.text
        assert restored.timestamp == original.timestamp

    def test_validate_from_dict(self):
        """Should validate from dictionary (simulating JSON parse)."""
        data = {"text": "Hello", "timestamp": "2026-06-02T10:30:00Z"}

        payload = DemoMessagePayload.model_validate(data)

        assert payload.text == "Hello"
