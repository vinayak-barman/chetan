from typing import Callable, Dict, List, Optional, Type, Any
from functools import wraps

from pydantic import BaseModel, Field
import inspect
from typing import get_type_hints
from docstring_parser import parse


class AgentToolCall(BaseModel):
    id: str
    tool_name: str
    tool_args: dict


class ToolInformation(BaseModel):
    id: str
    description: str
    tags: List[str]

    matchers: List[str] = []


def toolfn(fn: Callable) -> Callable:
    """
    Decorator to register a function as a tool function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.is_tool = True
    wrapper.__doc__ = fn.__doc__ or ""
    return wrapper


def get_tool_type_hints(func: Callable, attr: str, self_type: type) -> dict:
    """Get type hints for a tool function, handling unbound/bound methods and fallback to __annotations__."""
    unbound_func = getattr(self_type, attr, None)
    if unbound_func is not None:
        try:
            return get_type_hints(unbound_func)
        except Exception:
            return getattr(unbound_func, "__annotations__", {})
    else:
        try:
            return get_type_hints(func)
        except Exception:
            return getattr(func, "__annotations__", {})


def build_input_model(
    sig: inspect.Signature, type_hints: dict, func: Callable, attr: str
) -> Type[BaseModel]:
    """Build a Pydantic input model for a tool function from its signature and type hints."""
    from docstring_parser import parse as parse_docstring

    fields: dict = {}
    # Parse docstring for parameter descriptions
    docstring = func.__doc__ or ""
    param_docs = {}
    try:
        parsed = parse_docstring(docstring)
        for param in parsed.params:
            param_docs[param.arg_name] = param.description or ""
    except Exception:
        pass
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        # Skip *args and **kwargs
        if (
            param.kind == inspect.Parameter.VAR_POSITIONAL
            or param.kind == inspect.Parameter.VAR_KEYWORD
        ):
            continue
        # Get type hint or default to Any, fallback to __annotations__
        if param_name in type_hints:
            field_type = type_hints[param_name]
        else:
            field_type = getattr(func, "__annotations__", {}).get(param_name, Any)
        # Get description from docstring if available
        field_desc = param_docs.get(param_name, "")
        # Handle default values
        if param.default is not param.empty:
            fields[param_name] = (
                field_type,
                Field(default=param.default, description=field_desc),
            )
        else:
            fields[param_name] = (field_type, Field(..., description=field_desc))
    from pydantic import create_model

    return create_model(f"{attr}Input", **fields)


def get_return_type(type_hints: dict) -> Optional[Type]:
    """Get the return type for a tool function, defaulting to str if Any."""
    return_type = type_hints.get("return", None)
    if return_type is Any:
        return str
    return return_type


class ToolFunction(BaseModel):
    """
    Represents a tool function with its name and arguments.
    """

    name: str
    description: str
    input: Type[BaseModel]
    output: Optional[Type]
    fn: Callable = Field(default=None, exclude=True)


class Tool:
    tool_info: ToolInformation = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the tool with any necessary arguments.
        """
        self.tool_functions: Dict[str, ToolFunction] = {}
        self._register_tool_functions()

    def _register_tool_functions(self):
        for attr in dir(self):
            func = getattr(self, attr)
            if hasattr(func, "is_tool") and callable(func):
                docstring = func.__doc__ or ""
                sig = inspect.signature(func)
                type_hints = get_tool_type_hints(func, attr, type(self))
                input_model = build_input_model(sig, type_hints, func, attr)
                return_type = get_return_type(type_hints)
                self.tool_functions[attr] = ToolFunction(
                    name=attr,
                    description=parse(docstring).description,
                    input=input_model,
                    output=return_type,
                    fn=getattr(self, attr),
                )

    async def __call__(self, mcp_toolfunction_name: str, **kwargs):
        return await self.tool_functions[mcp_toolfunction_name].fn(self, **kwargs)
