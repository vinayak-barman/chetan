from typing import List
from asq import query
from chetan.lm import BaseModelType, LanguageModel
from chetan.tools import AgentToolCall

import anthropic
from anthropic.resources.messages.messages import Message
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock

from chetan.types.context.agent import AgentResponse


from collections import OrderedDict


class LMAnthropic(LanguageModel):
    def __init__(
        self,
        client: anthropic.Anthropic = None,
        model: str = "claude-3-7-sonnet-latest",
    ):
        self.client = client
        if self.client is None:
            self.client = anthropic.Anthropic()
        self.model = model

        self.chat_context = OrderedDict()
        self.chat_context_list = []  # Maintain a side-by-side list of values
        self.generation_context = ""

        self.tool_translation_table = {}

        self.system_prompt = None
        super().__init__()


    async def chat(self, ctx, tools, **kwargs):
        tools = self.translate_tools(*tools)

        output: Message = self.client.messages.create(
            model=self.model,
            messages=ctx,
            tools=tools,
            max_tokens=kwargs.get("max_tokens", 128),
            system=self.system_prompt,
            **kwargs,
        )

        text_content: TextBlock = (
            query(output.content)
            .where(lambda m: isinstance(m, TextBlock))
            .first_or_default(default=None)
        )
        tool_calls: List[ToolUseBlock] = (
            query(output.content)
            .where(lambda m: isinstance(m, ToolUseBlock))
            .select(
                lambda m: ToolUseBlock(
                    id=m.id,
                    name=self.tool_translation_table.get(m.name, m.name),
                    input=m.input,
                    type="tool_use",
                )
            )
            .to_list()
        )

        return AgentResponse(
            content=text_content.text.strip() if text_content else None,
            tool_calls=(
                [
                    AgentToolCall(
                        id=call.id, tool_name=call.name, tool_args=dict(call.input)
                    )
                    for call in tool_calls
                ]
            )
            if tool_calls
            else None,
        )

    # TODO: Validate this
    async def chat_structured(self, ctx, response_model: BaseModelType, **kwargs):
        raise NotImplementedError(
            "Chat with structured output is not yet implemented in Anthropic API."
        )

    def clone(self):
        """Create a deep copy of the language model instance."""
        return LMAnthropic(client=self.client, model=self.model)

    def translate_from_legible_message(self, item, type):
        # ? Tool Call Results
        if type == "tool_call_result":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": item.tool_call_id,
                        "content": item.content,
                    }
                ],
            }

        # ? AgentResponse
        if type == "agent_response":
            tool_calls = (
                (
                    [
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": call.tool_name,
                            "input": call.tool_args,
                        }
                        for call in item.tool_calls
                    ]
                )
                if item.tool_calls
                else None
            )

            if not item.content and tool_calls:
                return {"role": "assistant", "content": tool_calls}

            if item.content and tool_calls:
                # If both content and tool calls are present, return them together
                return {
                    "role": "assistant",
                    "content": [{"type": "text", "text": item.content}] + tool_calls,
                }

            if item.content and not tool_calls:
                return {
                    "role": "assistant",
                    "content": [{"type": "text", "text": item.content}],
                }

        # ? Anthropic Messages API doesn't support separate system role
        # * Setting it up as the `system_prompt` is the only solution
        if item.role == "system":
            self.system_prompt = item.content

            return None
        
        # ? Default
        if type == "default":
            return {
                "role": item.role,
                "content": item.content,
            }

    def clear_context_but_system(self):
        # ? We can safely remove all items, since Anthropic does not support separate system role
        # ? Instead directly uses system prompt
        self.chat_context = OrderedDict()
        self.chat_context_list = []

    def load_chat_context(self, ctx):
        # TODO: Implement this method to load context from Agent Context
        pass

    def transform_tool_name(self, tool_name: str) -> str:
        return tool_name.replace(".", "-")

    def translate_tools(self, *toolfunctions):
        """Translate AgentToolCall to OpenAI tool format."""

        if not toolfunctions:
            return []

        toolfunctions = list(toolfunctions)

        for fn in toolfunctions:
            # Transform the tool name to replace '.' with '-' and store in translation table
            self.tool_translation_table[self.transform_tool_name(fn.name)] = fn.name

        return [
            {
                "name": self.transform_tool_name(fn.name),
                "description": fn.description,
                "input_schema": fn.input.model_json_schema(),
            }
            for fn in toolfunctions
        ]
