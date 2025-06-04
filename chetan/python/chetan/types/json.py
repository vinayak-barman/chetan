from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class JsonSchema(BaseModel):
    # Core schema properties
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[Union[str, List[str]]] = None  # e.g., "object", "array", etc.
    properties: Optional[Dict[str, "JsonSchema"]] = None
    required: Optional[List[str]] = None
    items: Optional[Union["JsonSchema", List["JsonSchema"]]] = None
    enum: Optional[List[Any]] = None
    const: Optional[Any] = None
    default: Optional[Any] = None

    # Numeric validation
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    exclusiveMinimum: Optional[float] = None
    exclusiveMaximum: Optional[float] = None
    multipleOf: Optional[float] = None

    # String validation
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    pattern: Optional[str] = None

    # Array validation
    minItems: Optional[int] = None
    maxItems: Optional[int] = None
    uniqueItems: Optional[bool] = None

    # Object validation
    minProperties: Optional[int] = None
    maxProperties: Optional[int] = None
    additionalProperties: Optional[Union[bool, "JsonSchema"]] = None

    # Schema composition
    allOf: Optional[List["JsonSchema"]] = None
    anyOf: Optional[List["JsonSchema"]] = None
    oneOf: Optional[List["JsonSchema"]] = None
    not_: Optional["JsonSchema"] = Field(None, alias="not")

    # Reference
    ref: Optional[str] = Field(None, alias="$ref")

    # Meta
    definitions: Optional[Dict[str, "JsonSchema"]] = None
    examples: Optional[List[Any]] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        extra = "allow"


# For recursive models, rebuild the model to handle forward references
JsonSchema.model_rebuild()
