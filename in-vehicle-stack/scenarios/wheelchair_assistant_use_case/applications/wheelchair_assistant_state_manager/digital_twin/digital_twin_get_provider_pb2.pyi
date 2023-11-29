from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetRequest(_message.Message):
    __slots__ = ["entity_id"]
    ENTITY_ID_FIELD_NUMBER: _ClassVar[int]
    entity_id: str
    def __init__(self, entity_id: _Optional[str] = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ["property_value"]
    PROPERTY_VALUE_FIELD_NUMBER: _ClassVar[int]
    property_value: bool
    def __init__(self, property_value: bool = ...) -> None: ...
