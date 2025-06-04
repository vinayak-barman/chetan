import json
from typing import Literal
from chetan.lm import BaseModelType, LanguageModel
from chetan.tools import AgentToolCall


from chetan.types.context.agent import AgentResponse, LMLegibleMessage
from groq.types.chat.chat_completion import ChatCompletion
from groq.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from groq.types.shared.function_definition import FunctionDefinition
import groq

from collections import OrderedDict


class LMGroq(LanguageModel):
    def __init__(
        self,
        client=None,
        model: Literal[
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "deepseek-r1-distill-llama-70b",
            "qwen-qwq-32b",
        ] = "meta-llama/llama-4-scout-17b-16e-instruct",
    ):
        """Initialize the LMGroq model.

        Args:
            client (_type_, optional): Groq client. Defaults to None
            model (Literal[ &quot;qwen, optional): One of the supported (and tested) Groq models. Defaults to "qwen-qwq-32b".
        """
        self.client = client
        if self.client is None:
            self.client = groq.Groq()
        self.model = model

        self.chat_context = OrderedDict()
        self.chat_context_list = []  # Maintain a side-by-side list of values
        self.generation_context = ""
        super().__init__()

    async def chat(self, ctx, tools, **kwargs):
        tools = self.translate_tools(*tools)

        output: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=ctx,
            tools=tools,
            **kwargs,
        )

        return AgentResponse(
            content=output.choices[0].message.content,
            tool_calls=(
                [
                    AgentToolCall(
                        id=call.id,
                        tool_name=call.function.name,
                        tool_args=json.loads(call.function.arguments),
                    )
                    for call in output.choices[0].message.tool_calls
                ]
            )
            if output.choices[0].message.tool_calls
            else [],
        )

    # TODO: Validate this
    async def chat_structured(self, ctx, response_model: BaseModelType, **kwargs):
        output = self.client.chat.completions.create(
            model=self.model,
            messages=ctx,
            response_format=response_model,
            **kwargs,
        )
        return output.choices[0].message.content

    def clone(self):
        """Create a deep copy of the language model instance."""
        return LMGroq(client=self.client, model=self.model)

    def translate_from_legible_message(self, item, type):
        if type == "tool_call_result":
            return {
                "role": "tool",
                "tool_call_id": item.tool_call_id,
                "content": item.content,
            }

        if type == "agent_response":
            tool_calls = (
                (
                    [
                        {
                            "id": call.id,
                            "function": {
                                "name": call.tool_name,
                                "arguments": json.dumps(call.tool_args),
                            },
                            "type": "function",
                        }
                        for call in item.tool_calls
                    ]
                )
                if item.tool_calls
                else None
            )

            return (
                {
                    "role": "assistant",
                    "content": item.content,
                    "tool_calls": tool_calls,
                }
                if tool_calls
                else {
                    "role": "assistant",
                    "content": item.content,
                }
            )

        if type == "default":
            return {
                "role": item.role,
                "content": item.content,
            }

    def clear_context_but_system(self):
        # Keep only the first item if it has role 'system', else clear all
        if self.chat_context:
            first_key = next(iter(self.chat_context))
            first_item = self.chat_context[first_key]
            if first_item.get("role") == "system":
                self.chat_context = OrderedDict([(first_key, first_item)])
            else:
                self.chat_context = OrderedDict()
        else:
            self.chat_context = OrderedDict()

        if self.chat_context_list:
            first_item = self.chat_context_list[0]
            if first_item.get("role") == "system":
                self.chat_context_list = [first_item]
            else:
                self.chat_context_list = []
        else:
            self.chat_context_list = []

    def load_chat_context(self, ctx):
        # TODO: Implement this method to load context from Agent Context
        pass

    def translate_tools(self, *toolfunctions):
        """Translate AgentToolCall to OpenAI tool format."""

        if not toolfunctions:
            return []

        return [
            ChatCompletionToolParam(
                function=FunctionDefinition(
                    name=fn.name,
                    description=fn.description,
                    parameters=fn.input.model_json_schema(),
                ),
                type="function",
            )
            for fn in list(toolfunctions)
        ]
