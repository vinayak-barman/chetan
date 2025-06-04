from .zep import ZepMemoryModule
from .smriti import SmritiMemoryModule

__all__ = ["ZepMemoryModule", "SmritiMemoryModule"]

# from typing import Union
# from pydantic import BaseModel
# from chetan.modules import AgentModule, tool_method, prologue


# class KVItem(BaseModel):
#     key: str
#     value: Union[int, float, bool, str]


# class SimpleKVMemory(AgentModule):
#     DESCRIPTION = "Simple key-value pair memory with read/write access"

#     def __init__(self, k: int = 10):
#         """Provides a simple key-value store for agent to store information

#         Args:
#             k (int): Maximum top-most item capacity
#         """
#         self._items = {}
#         self.k = k

#     @tool_method
#     def write(self, items: list[KVItem]):
#         """Adds an item to the key-value memory

#         Args:
#             key (str): The key to store the value at
#             item (Union[int, float, bool, str]): The item to add
#         """
#         for item in items:

#             if len(self._items) < self.k:
#                 self._items[item.key] = item.value
#             raise IndexError("Maximum item limit reached")

#     @tool_method
#     def clear(self):
#         """Clears the memory"""
#         self._items.clear()

#     @prologue
#     def show_memory(self):
#         return

# class SmritiMemory(AgentModule):
#     # TODO: Remember facts, relations, graphs, etc.
#     pass
