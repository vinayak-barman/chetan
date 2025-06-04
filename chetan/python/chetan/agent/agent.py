from typing import Optional
from chetan.agent.loop import AgentLoop
from chetan.entity import Entity
from chetan.lm import LanguageModel
from chetan.types.context.agent import EntityMessage, SystemMessage
from chetan.types.context.agent.iteration import AgentContext
from whenever import Instant


class Agent(Entity):
    # This will not be part of validation or serialization
    _loop: Optional[AgentLoop] = None
    _lm: Optional[LanguageModel] = None
    context: AgentContext = None

    role: str

    system_prompt: str

    _system_prompt_injected: bool = False

    async def __call__(self, *args, new_iteration=True, **kwargs):
        """Run the agent loop with the provided context."""
        if new_iteration:
            self.context.new()
        await self._loop(self.context, *args, **kwargs)

    def apply_system_prompt(self):
        """Set the system prompt for the agent."""

        # TODO: System Prompt Formatting with different sections
        if not self._system_prompt_injected:
            self.context.new().add_item(
                SystemMessage(
                    content=self.system_prompt,
                    start_time=Instant.now(),
                    end_time=Instant.now(),
                ),
                "prologue",
            )
            self._system_prompt_injected = True

    async def prompt(self, prompt: str, **kwargs):
        """Set the prompt for the agent."""
        if len(self.context) == 0:
            self.apply_system_prompt()

        if len(self.context) == 1 and (
            self.context.latest().process == [] and self.context.latest().epilogue == []
        ):
            ctx = self.context.latest()
        else:
            ctx = self.context.new()

        ctx.add_item(
            EntityMessage(
                content=prompt, start_time=Instant.now(), end_time=Instant.now()
            ),
            "prologue",
        )
        return await self(new_iteration=False, **kwargs)
