import json
from typing import List, Literal
from chetan.lm import BaseModelType, LanguageModel
from asq import query
from chetan.tools import AgentToolCall
from chetan.types.context.agent import AgentResponse

from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared.function_definition import FunctionDefinition
import openai as oai

from collections import OrderedDict


class LMOpenAI(LanguageModel):
    def __init__(
        self,
        client=None,
        model: str = "gpt-4o-mini",
        api: Literal["chat", "responses"] = "chat",
    ):
        self.oai_client = client
        if self.oai_client is None:
            self.oai_client = oai.OpenAI()
        self.model = model
        self.api = api

        self.chat_context: OrderedDict[str, ChatCompletionMessageParam] = OrderedDict()
        self.chat_context_list: List[
            ChatCompletionMessageParam
        ] = []  # Maintain a side-by-side list of values
        self.generation_context = ""
        super().__init__()

    async def chat(self, ctx, tools, **kwargs):
        tools = self.translate_tools(*tools)

        output: ChatCompletion = self.oai_client.chat.completions.create(
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
        output = self.oai_client.chat.completions.create(
            model=self.model,
            messages=ctx,
            response_format=response_model,
            **kwargs,
        )
        return output.choices[0].message.content

    def clone(self):
        """Create a deep copy of the language model instance."""
        return LMOpenAI(client=self.oai_client, model=self.model)

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


class LMOpenAIResponses(LanguageModel):
    def __init__(
        self,
        client=None,
        model: str = "gpt-4o-mini",
    ):
        self.oai_client = client
        if self.oai_client is None:
            self.oai_client = oai.OpenAI()
        self.model = model

        self.chat_context = OrderedDict()
        self.chat_context_list = []  # Maintain a side-by-side list of values
        self.generation_context = ""
        super().__init__()

    async def chat(self, ctx, tools, **kwargs):
        tools = self.translate_tools(*tools)

        output = self.oai_client.responses.create(
            model=self.model, input=ctx, tools=tools, **kwargs
        )

        if isinstance(output, ChatCompletion):
            return AgentResponse(
                content=output.output_text,
                tool_calls=[
                    AgentToolCall(
                        id=call.call_id,
                        tool_name=call.name,
                        tool_args=json.loads(call.arguments),
                    )
                    for call in query(output.output)
                    .where(lambda x: isinstance(x, ResponseFunctionToolCall))
                    .to_list()
                ],
            )

    # TODO: Validate this
    async def chat_structured(self, ctx, response_model: BaseModelType, **kwargs):
        output = self.oai_client.responses.parse(
            model=self.model,
            text_format=response_model,
            input=ctx,
            **kwargs,
        )
        return output.output_parsed

    def clone(self):
        """Create a deep copy of the language model instance."""
        return LMOpenAI(client=self.oai_client, model=self.model)

    def translate_from_legible_message(self, item):
        if item.tool_call_id:
            return {
                "type": "function_call_output",
                "call_id": item.tool_call_id,
                "output": item.content,
            }

        # Add AgentResponse
        if (
            (item.tool_calls or item.content)
            and not item.tool_call_id
            and item.role == "assistant"
        ):
            # TODO: Implement this for responses API
            raise NotImplementedError(
                "Tool calls are not yet implemented in responses API."
            )

        if item.content is not None:
            return {
                "role": item.role,
                "content": item.content,
            }

    def load_chat_context(self, ctx):
        # TODO: Implement this method to load context from Agent Context
        pass

    def translate_tools(self, *toolfunctions):
        """Translate AgentToolCall to OpenAI tool format."""

        if not toolfunctions:
            return []
        return [
            {
                "type": "function",
                "name": fn.name,
                "description": fn.description or "",
                "parameters": fn.input.model_json_schema(),
            }
            for fn in list(toolfunctions)
        ]
