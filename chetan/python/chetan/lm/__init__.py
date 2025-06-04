from abc import ABC, abstractmethod
from typing import Any, List, Literal, Optional, OrderedDict, Type, TypeVar, Union

from chetan.tools import Tool, ToolFunction
from chetan.types.context.agent import AgentResponse, LMLegibleMessage
from pydantic import BaseModel

BaseModelType = TypeVar("BaseModelType", bound=[BaseModel, Type[BaseModel]])


def detect_message_type(item: LMLegibleMessage):
    if item.tool_call_id:
        return "tool_call_result"

    if (
        (item.tool_calls or item.content)
        and not item.tool_call_id
        and item.role == "assistant"
    ):
        return "agent_response"
    
    if item.content:
        return "default"
    
    return "unknown"


class LanguageModel(ABC):
    generation_context: str = ""
    chat_context: OrderedDict[str, Any] = OrderedDict[str, Any]()
    chat_context_list: List = []

    async def invoke(
        self,
        *args,
        input: Union[str, list],
        response_model: Optional[BaseModelType] = None,
        add_to_context=True,
        **kwargs,
    ):
        if isinstance(input, str):
            output = (
                await self.generate_structured(input, response_model, *args, **kwargs)
                if response_model
                else await self.generate(input, *args, **kwargs)
            )
        elif isinstance(input, list):
            output = (
                await self.chat_structured(input, response_model, *args, **kwargs)
                if response_model
                else await self.chat(input, *args, **kwargs)
            )
        else:
            raise TypeError(f"Input must be str or list, got {type(input).__name__}")

        if add_to_context:
            self.add_to_context(input)
        return output

    @abstractmethod
    def clone(self):
        """Create a deep copy of the language model instance."""
        ...

    # region Generation
    # * Chat Method
    @abstractmethod
    async def chat(
        self, ctx: list, *args, tools: List[Tool] = [], **kwargs
    ) -> AgentResponse: ...

    # * Chat Method
    @abstractmethod
    async def chat_structured(
        self, ctx: list, response_model: BaseModelType, *args, **kwargs
    ) -> BaseModelType: ...

    # endregion

    # region Context

    def add_to_context(
        self, item: Union[LMLegibleMessage, List[LMLegibleMessage]], id: str
    ):
        if isinstance(item, LMLegibleMessage):
            value = self.translate_from_legible_message(item, detect_message_type(item))
            if value:
                self.chat_context[id] = value
                self.chat_context_list.append(value)
        elif isinstance(item, list):
            # Accept a list of LMLegibleMessage
            for i, msg in enumerate(item):
                key = f"{id}:{i}"
                value = self.translate_from_legible_message(msg, detect_message_type(msg))
                if value:
                    self.chat_context[key] = value
                    self.chat_context_list.append(value)
        else:
            raise TypeError(
                f"Expected `LMLegibleMessage` or list of it. Got {type(item).__name__} instead."
            )

    def remove_from_context(self, id: str):
        # Remove all keys that match id or id:*
        keys_to_remove_with_index = [
            (k, idx)
            for idx, k in enumerate(self.chat_context)
            if k == id or k.startswith(f"{id}:")
        ]
        for k, idx in reversed(keys_to_remove_with_index):
            del self.chat_context[k]
            del self.chat_context_list[idx]

        return keys_to_remove_with_index

    def clear_context(self, retain_system_prompt: bool = False):
        """Clear the chat context."""
        if retain_system_prompt:
            self.clear_context_but_system()
        else:
            self.chat_context.clear()
            self.chat_context_list.clear()
    
    @abstractmethod
    def clear_context_but_system(self):
        ...

    @abstractmethod
    def translate_from_legible_message(self, item: LMLegibleMessage, type: Literal["tool_call_result", "agent_response", "default", "unknown"]) -> Any: ...

    # * Chat Method
    @abstractmethod
    def load_chat_context(self, ctx): ...

    @abstractmethod
    def translate_tools(self, *toolfunctions: ToolFunction): ...

    # endregion
