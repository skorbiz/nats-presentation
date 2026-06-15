"""Pydantic models implementing the AsyncAPI specification.

These models are hand-crafted to match the schemas defined in asyncapi.yaml.
They provide runtime validation of message payloads and are tested against
the spec using contract tests in tests/test_contract.py.

Note: These are NOT auto-generated. The AsyncAPI model generator has limited
support for AsyncAPI 3.x specs. Manual maintenance ensures proper validation.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DemoMessagePayload(BaseModel):
    """Payload for simple pub/sub messages."""

    text: str = Field(..., description="The message text content")
    timestamp: datetime = Field(..., description="When the message was created")


# class DemoMessagePayload(BaseModel):
#   text: str = Field(description='''The message text content''')
#   timestamp: str = Field(description='''When the message was created''')
#   additional_properties: Optional[dict[str, Any]] = Field(default=None, exclude=True)


class RequestPayload(BaseModel):
    """Payload for request messages."""

    request_id: str = Field(..., description="Unique identifier for the request")
    data: str = Field(..., description="Request data to be processed")
    timestamp: datetime = Field(..., description="When the request was created")


# class RequestPayload(BaseModel):
#   request_id: str = Field(description='''Unique identifier for the request''')
#   data: str = Field(description='''Request data to be processed''')
#   timestamp: str = Field(description='''When the request was created''')
#   additional_properties: Optional[dict[str, Any]] = Field(default=None, exclude=True)


class ResponsePayload(BaseModel):
    """Payload for response messages."""

    request_id: str = Field(..., description="ID of the request being responded to")
    result: str = Field(..., description="Processing result")
    timestamp: datetime = Field(..., description="When the response was created")


class Priority(StrEnum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


# class AnonymousSchema13(Enum):
#   LOW = "low"
#   NORMAL = "normal"
#   HIGH = "high"


class MessageMetadata(BaseModel):
    """Additional metadata for stream messages."""

    source: str = Field(..., description="Source of the message")
    priority: Priority = Field(default=Priority.NORMAL, description="Message priority")


# class AnonymousSchema11(BaseModel):
#   source: str = Field(description='''Source of the message''')
#   priority: Optional[AnonymousSchema13] = Field(description='''Message priority''', default=None)
#   additional_properties: Optional[dict[str, Any]] = Field(default=None, exclude=True)


class StreamMessagePayload(BaseModel):
    """Payload for JetStream persistent messages."""

    message_id: str = Field(..., description="Unique identifier for the message")
    data: str = Field(..., description="Message data")
    metadata: MessageMetadata = Field(..., description="Additional metadata")
    timestamp: datetime = Field(..., description="When the message was created")


# class StreamMessagePayload(BaseModel):
#   message_id: str = Field(description='''Unique identifier for the message''')
#   data: str = Field(description='''Message data''')
#   metadata: Optional[AnonymousSchema11] = Field(description='''Additional metadata''', default=None)
#   timestamp: str = Field(description='''When the message was created''')
#   additional_properties: Optional[dict[str, Any]] = Field(default=None, exclude=True)
