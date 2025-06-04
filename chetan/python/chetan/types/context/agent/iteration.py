import importlib
import json
import pickle
from typing import List, Optional

from chetan.types.context.agent import (
    AgentResponse,
    EpilogueItem,
    ItemTypes,
    ProcessItem,
    PrologueItem,
    StartToEndObject,
    AgentToolCallResults,
    SystemMessage,
    EntityMessage,
    LMLegibleMessage,
)
from chetan.types.stringref import StringRef
from pydantic import BaseModel, Field, SerializeAsAny

import uuid

from chetan.lm import LanguageModel

from rich.console import Console

from whenever import Instant

console = Console()
console.is_jupyter = False


def to_dict_with_class(obj: StartToEndObject):
    d = obj.model_dump()
    d["__class__"] = obj.__class__.__module__ + "." + obj.__class__.__name__
    return d


def from_dict_with_class(d):
    class_path = d.pop("__class__")
    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls.model_validate(d)


class ContextIteration(StartToEndObject):
    index: int = -1

    prologue: List[SerializeAsAny[PrologueItem]] = Field(default_factory=list)
    process: List[SerializeAsAny[ProcessItem]] = Field(default_factory=list)
    epilogue: List[SerializeAsAny[EpilogueItem]] = Field(default_factory=list)

    _lm: LanguageModel = None

    def __init__(self, index: int, *args, _lm: LanguageModel = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._lm = _lm
        self.index = index

    def items(self) -> List[StartToEndObject]:
        """Return all items across all sections."""
        return self.prologue + self.process + self.epilogue

    def __getitem__(self, section: ItemTypes) -> List[StartToEndObject]:
        if section == "prologue":
            return self.prologue
        elif section == "process":
            return self.process
        elif section == "epilogue":
            return self.epilogue
        else:
            raise ValueError(f"Invalid section: {section}")

    def _log_item(self, item: StartToEndObject, section: ItemTypes):
        def trim_content(content, max_length=100):
            if content is None:
                return ""
            return content[:max_length] + "…" if len(content) > max_length else content

        def print_item(title: str, content: str, color: str = "white"):
            console.print(f"[{color}]{title.upper()}[/]: {content}", justify="left")
            pass

        if isinstance(item, EntityMessage):
            print_item(
                f"{item.role.upper()}{item.name and f' ({item.name})' or ''}",
                item.content,
                color="dodger_blue2" if item.role == "user" else "green1",
            )
        elif isinstance(item, AgentResponse):
            print_item("self", item.to_lm_legible().content, color="orange_red1")

            if item.tool_calls:
                tool_calls = "\n".join(
                    f"{call.id} {call.tool_name}({', '.join(f'{k}={repr(v)}' for k, v in call.tool_args.items())})"
                    for call in item.tool_calls
                )
                print_item("tool-calls", tool_calls, color="magenta3")
        elif isinstance(item, AgentToolCallResults):
            tool_results = "\n".join(
                f"{res.id}: {trim_content(res.results)}"
                for res in item.tool_call_results
            )
            print_item("tool-call-results", tool_results, color="cyan2")
        elif isinstance(item, SystemMessage):
            print_item(
                "system",
                trim_content(item.to_lm_legible().content),
                color="dark_goldenrod",
            )
        else:
            print_item(
                title=f"{section.upper()}",
                content=trim_content(
                    item.to_lm_legible().content
                    if hasattr(item, "to_lm_legible")
                    else str(item)
                )
                if isinstance(item, StartToEndObject)
                else str(item),
                color="white",
            )

    def add_item(
        self,
        item: StartToEndObject,
        section: ItemTypes,
        lm: LanguageModel = None,
    ):
        # Assign unique context_id
        item.context_id = StringRef(str(uuid.uuid4()))
        getattr(self, section).append(item)
        # Always use self.lm (or provided lm) to add to context
        lm_to_use = lm or getattr(self, "_lm", None)
        if lm_to_use is not None:
            lm_to_use.add_to_context(item.to_lm_legible(), item.context_id)
        self._log_item(item, section)
        return item.context_id

    def remove_item(
        self,
        context_id,
        section: ItemTypes,
        lm: LanguageModel = None,
    ):
        section_list = getattr(self, section)
        for i, item in enumerate(section_list):
            if getattr(item, "context_id", None) == context_id:
                del section_list[i]
                lm_to_use = lm or getattr(self, "_lm", None)
                if lm_to_use is not None:
                    lm_to_use.remove_from_context(context_id)
                return True
        return False

    def to_lm_legible(self):
        """Convert the entire iteration for LM context."""
        messages: List[LMLegibleMessage] = []
        for item in self.prologue:
            messages.append(item.to_lm_legible())
        for item in self.process:
            messages.append(item.to_lm_legible())
        for item in self.epilogue:
            messages.append(item.to_lm_legible())
        return messages

    def flatten(self) -> str:
        """Flatten the iteration into a single string for LM context."""
        return "\n".join(
            f"{item.role}{(item.name and f' ({item.name})' or '')}: {item.content}"
            for item in self.to_lm_legible()
        )

    def __getstate__(self):
        state = self.__dict__.copy()
        # Exclude any non-serializable fields (e.g., _lm)
        state.pop("_lm", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lm = None  # or restore as needed

    def to_dict_with_class(self):
        d = self.model_dump(exclude={"prologue", "process", "epilogue"})
        d["__class__"] = self.__class__.__module__ + "." + self.__class__.__name__
        # Recursively convert prologue, process, epilogue items
        d["prologue"] = [to_dict_with_class(item) for item in self.prologue]
        d["process"] = [to_dict_with_class(item) for item in self.process]
        d["epilogue"] = [to_dict_with_class(item) for item in self.epilogue]
        return d

    @classmethod
    def from_dict_with_class(cls, d):
        d = d.copy()
        prologue = [from_dict_with_class(item) for item in d.get("prologue", [])]
        process = [from_dict_with_class(item) for item in d.get("process", [])]
        epilogue = [from_dict_with_class(item) for item in d.get("epilogue", [])]
        index = d.get("index", -1)
        start_time = d.get("start_time")
        end_time = d.get("end_time")
        return cls(
            index=index,
            prologue=prologue,
            process=process,
            epilogue=epilogue,
            start_time=start_time,
            end_time=end_time,
        )


class AgentContext(BaseModel):
    iterations: List[ContextIteration] = []
    _lm: LanguageModel = None

    def __init__(self, _lm: LanguageModel = None, **kwargs):
        super().__init__(**kwargs)
        self._lm = _lm
        self.iterations = []

    def save_pickled(self, file_path: str):
        """Save the context to a pickle file (only iterations)."""
        # Only serialize iterations (as dicts)
        ...
        with open(file_path, "wb") as f:
            pickle.dump(self.iterations, f)

    def load_pickled(self, file_path: str):
        """Load the context from a pickle file (only iterations)."""
        with open(file_path, "rb") as f:
            self.iterations = pickle.load(f)

    def save_json(self, file_path: str) -> str:
        with open(file_path, "w") as f:
            json.dump({"iterations":[it.to_dict_with_class() for it in self.iterations]}, f, indent=4, default=str)

    def load_json(self, file_path: str):
        with open(file_path, "r") as f:
            raw_list = json.load(f)
            self.iterations = [
                ContextIteration.from_dict_with_class(item) for item in raw_list["iterations"]
            ]
            for iteration in self.iterations:
                iteration._lm = self._lm

    def get(self, idx: str):
        parts = idx.split(":")
        obj = self
        for part in parts:
            if part.isdigit():
                obj = obj[int(part)]
            else:
                obj = obj[part]
        return obj

    def __getitem__(self, idx: int) -> ContextIteration:
        return self.iterations[idx]

    def __len__(self) -> int:
        return len(self.iterations)

    def add_iteration(self, iteration: ContextIteration) -> int:
        self.iterations.append(iteration)
        return len(self.iterations) - 1

    def new(self) -> ContextIteration:
        if self.iterations:
            self.latest().end_time = Instant.now()
        iteration = ContextIteration(index=len(self.iterations), _lm=self._lm)
        iteration.start_time = Instant.now()
        self.iterations.append(iteration)
        return iteration

    def latest(self) -> ContextIteration:
        try:
            return self.iterations[-1]
        except IndexError:
            return None

    def latest_complete_iteration(self) -> Optional[ContextIteration]:
        for iteration in reversed(self.iterations):
            if iteration.is_complete():
                return iteration
        return None

    def clear(self, retain_system_prompt: bool = False):
        """Clear the context, optionally retaining the system prompt."""
        if retain_system_prompt:
            first_iteration = self.get("0")
            self.iterations.clear()
            first_iteration.process.clear()
            first_iteration.epilogue.clear()
            first_iteration.prologue = [
                item
                for item in first_iteration.prologue
                if isinstance(item, SystemMessage)
            ]
            self.iterations.append(first_iteration)

        if self._lm is not None:
            self._lm.clear_context(retain_system_prompt=retain_system_prompt)

    def add_item(
        self,
        item,
        section: ItemTypes,
        lm: LanguageModel = None,
    ):
        lm_to_use = lm or getattr(self, "lm", None)
        return self.latest().add_item(item, section, lm=lm_to_use)

    def remove_item(
        self,
        context_id,
        section: ItemTypes,
        lm: LanguageModel = None,
    ):
        lm_to_use = lm or getattr(self, "lm", None)
        return self.latest().remove_item(context_id, section, lm=lm_to_use)

    def remove_iteration(self, start: int, stop: Optional[int] = None):
        """Remove an iteration by index."""
        if stop is None:
            stop = start + 1

        if stop == -1:
            stop = len(self.iterations) + 1

        def remove_single_iteration(idx: int):
            if idx < len(self.iterations):
                for item in ["prologue", "process", "epilogue"]:
                    for sub_item in self.get(f"{idx}:{item}"):
                        sub_item: StartToEndObject
                        self.remove_item(sub_item.context_id, item)
                del self.iterations[idx]
                return True
            return False

        for i in range(start, stop):
            remove_single_iteration(i)

    def flatten(self) -> str:
        """Flatten the entire context into a single string for LM context."""
        return "\n".join(iteration.flatten() for iteration in self.iterations)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Exclude any non-serializable fields (e.g., _lm)
        state.pop("_lm", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lm = None  # or restore as needed
