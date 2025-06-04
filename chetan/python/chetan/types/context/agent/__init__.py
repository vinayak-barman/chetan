from abc import ABC, abstractmethod
from typing import List, Literal, Optional, TypeVar, Union
from chetan.tools import AgentToolCall
from chetan.types.stringref import StringRef
from pydantic import BaseModel, Field

from whenever import Instant


class LMLegibleMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"] = "user"
    content: Optional[StringRef] = None

    name: Optional[StringRef] = None

    tool_calls: Optional[List[AgentToolCall]] = None
    tool_call_id: Optional[StringRef] = None


class StartToEndObject(BaseModel, ABC):
    start_time: Optional[Instant] = None
    end_time: Optional[Instant] = None

    metadata: Optional[dict] = None
    context_id: Optional[StringRef] = None  # Unique id for LM sync

    def is_complete(self) -> bool:
        """Check if the object has a complete start and end time."""
        return self.start_time is not None and self.end_time is not None

    @abstractmethod
    def to_lm_legible(self) -> Union[LMLegibleMessage, List[LMLegibleMessage]]:
        """Convert this item to LM context format. Override in subclasses as needed."""
        ...


class PrologueItem(StartToEndObject, ABC):
    module: Optional[StringRef] = None

    @abstractmethod
    def to_lm_legible(self): ...


class EntityMessage(PrologueItem):
    item_type: Literal["entity_message"] = "entity_message"
    name: Optional[StringRef] = None
    role: Literal["user", "assistant"] = "user"
    content: StringRef

    def to_lm_legible(self):
        return LMLegibleMessage(role=self.role, content=self.content, name=self.name)


class SystemMessage(PrologueItem):
    item_type: Literal["system_message"] = "system_message"
    content: StringRef

    def to_lm_legible(self):
        return LMLegibleMessage(role="system", content=self.content)
    
class ProcessItem(StartToEndObject, ABC):
    @abstractmethod
    def to_lm_legible(self): ...


class AgentResponse(ProcessItem):
    item_type: Literal["agent_response"] = "agent_response"
    
    thinking: Optional[StringRef] = None
    content: Optional[StringRef] = None
    tool_calls: Optional[List[AgentToolCall]] = None

    def to_lm_legible(self):
        if self.tool_calls:
            return LMLegibleMessage(
                role="assistant",
                content=self.content,
                tool_calls=self.tool_calls,
            )
        else:
            return LMLegibleMessage(role="assistant", content=self.content)


class AgentToolCallResult(BaseModel):
    id: str
    results: Optional[StringRef] = None


class AgentToolCallResults(ProcessItem):
    item_type: Literal["agent_tool_call_results"] = "agent_tool_call_results"
    tool_call_results: List[AgentToolCallResult] = Field(
        default_factory=list
    )  # List of tool call results

    def to_lm_legible(self):
        return [
            LMLegibleMessage(role="tool", tool_call_id=res.id, content=res.results)
            for res in self.tool_call_results
        ]


class EpilogueItem(StartToEndObject, ABC):
    @abstractmethod
    def to_lm_legible(self): ...


ItemTypes = TypeVar("ItemTypes", bound=Literal["prologue", "process", "epilogue"])

StartToEndObject.model_rebuild()
