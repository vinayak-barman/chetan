import json
from typing import Any
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue


class StringRef:
    def __init__(self, value=""):
        self._value = str(value)

    def __str__(self):
        return self._value

    def __repr__(self):
        return f"StringRef('{self._value}')"

    # Automatic casting/conversion
    def __eq__(self, other):
        return self._value == str(other)

    def __ne__(self, other):
        return self._value != str(other)

    def __lt__(self, other):
        return self._value < str(other)

    def __le__(self, other):
        return self._value <= str(other)

    def __gt__(self, other):
        return self._value > str(other)

    def __ge__(self, other):
        return self._value >= str(other)

    def __hash__(self):
        return hash(self._value)

    # String operations
    def __add__(self, other):
        return StringRef(self._value + str(other))

    def __radd__(self, other):
        return StringRef(str(other) + self._value)

    def __iadd__(self, other):
        self._value += str(other)
        return self

    def __mul__(self, other):
        return StringRef(self._value * other)

    def __rmul__(self, other):
        return StringRef(other * self._value)

    def __len__(self):
        return len(self._value)

    def __getitem__(self, key):
        return self._value[key]

    def __contains__(self, item):
        return str(item) in self._value

    # String methods delegation
    def __getattr__(self, name):
        attr = getattr(self._value, name)
        if callable(attr):

            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                if isinstance(result, str):
                    return StringRef(result)
                return result

            return wrapper
        return attr

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = str(new_value)

    # JSON serialization support
    def __json__(self):
        """For orjson and other JSON libraries that check for this method"""
        return self._value

    def to_json(self):
        """Alternative JSON serialization method"""
        return self._value

    def __dict__(self):
        """For dict conversion"""
        return {"value": self._value}

    # For compatibility with various serializers
    def __reduce__(self):
        return (self.__class__, (self._value,))

    # Pydantic v2 support
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls),
                    core_schema.str_schema(),
                    core_schema.int_schema(),
                    core_schema.float_schema(),
                    core_schema.bytes_schema(),
                ]
            ),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, value: Any) -> "StringRef":
        if isinstance(value, cls):
            return value
        return cls(value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GenerateJsonSchema
    ) -> JsonSchemaValue:
        return {"type": "string", "title": "StringRef"}


# Custom JSON Encoder for StringRef
class StringRefJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, StringRef):
            return str(obj)
        return super().default(obj)


# Monkey patch the default JSON encoder to handle StringRef
_original_default = json.JSONEncoder.default


def _stringref_json_default(self, obj):
    if isinstance(obj, StringRef):
        return str(obj)
    return _original_default(self, obj)


json.JSONEncoder.default = _stringref_json_default


# Alternative: Custom dumps function that handles StringRef
def dumps_with_stringref(obj, **kwargs):
    """JSON dumps that handles StringRef objects"""
    return json.dumps(obj, cls=StringRefJSONEncoder, **kwargs)
