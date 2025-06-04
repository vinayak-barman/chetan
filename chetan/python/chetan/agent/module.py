from abc import ABC, abstractmethod
from typing import Callable, Dict
import functools
import inspect

# Add imports for tool registration
from chetan.tools import Tool

from loguru import logger


# Updated prologue decorator to preserve signature and async status
def prologue(fn):
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)

    else:

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

    wrapper.__agentloop_item_type__ = "prologue"
    return wrapper


# Updated epilogue decorator to preserve signature and async status
def epilogue(fn):
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)

    else:

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

    wrapper.__agentloop_item_type__ = "epilogue"
    return wrapper


class AgentLoopModule(ABC, Tool):
    functions: Dict[str, Dict[str, Callable]]

    def __init__(self, *args, **kwargs):
        # Create dictionaries to store prologue and epilogue functions
        self.functions = {"prologue": {}, "epilogue": {}}
        self.tool_fns = {}
        self.tool_functions = {}

        # Inspect class attributes to find decorated functions
        for attr_name in dir(self.__class__):
            if attr_name.startswith("__") and attr_name.endswith("__"):
                continue  # Skip magic methods

            attr = getattr(self.__class__, attr_name)
            if callable(attr):
                # Check if it's a decorated function
                if hasattr(attr, "__agentloop_item_type__"):
                    agent_type = attr.__agentloop_item_type__

                    if agent_type in ["prologue", "epilogue"]:
                        self.functions[agent_type][attr_name] = attr

        super().__init__(*args, **kwargs)

        self.args = args
        self.kwargs = kwargs

    def log(self, message: str, level: str = "info"):
        """Log a message."""
        logger.log(level.upper(), f"{self.__class__.__name__}: {message}")

    @abstractmethod
    def setup(self):
        """Setup the module. This method should be overridden by subclasses."""
        ...
