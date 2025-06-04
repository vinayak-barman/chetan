from typing import Callable, Dict, List, Self
from chetan.agent.module import AgentLoopModule

from chetan.lm import LanguageModel
from chetan.tools import AgentToolCall, Tool
from chetan.tools.toolbox import Toolbox
from chetan.types.context.agent import (
    AgentResponse,
    AgentToolCallResult,
    AgentToolCallResults,
)

import asyncio
from concurrent.futures import ThreadPoolExecutor

from asq import query
from chetan.types.context.agent.iteration import AgentContext
from loguru import logger
import copy

from rich.console import Console
from whenever import Instant

console = Console()
console.is_jupyter = False


class ProcessFunctionContext:
    def __init__(
        self,
        lm: LanguageModel,
        context: AgentContext,
        tools: List[Tool] = None,
        toolbox: Toolbox = None,
        iteration_context: dict = None,
        **kwargs,
    ):
        self.lm = lm
        self.context = context
        self.tools = tools
        self.toolbox = toolbox
        self.iteration_context = iteration_context

        self.kwargs = kwargs

    async def generate(self):
        """Generate a textual response from the language model."""
        pass

    async def tool_call(self):
        """Generate only tool calls from the language model."""
        pass

    async def generate_with_tool_call(self):
        """Generate a response from the language model, including tool calls."""
        ctx = self.lm.chat_context_list
        start_time = Instant.now()
        if self.tools:
            res = await self.lm.chat(ctx, self.tools, **self.kwargs)
        else:
            res = await self.lm.chat(ctx, **self.kwargs)

        if res.content or res.tool_calls:
            if res.content:
                # ! TODO: Possible adversarial input, this token can be misused to exit the agent loop
                # Check if the response contains the end agent loop marker
                if "<|stop|>" in res.content:
                    self.iteration_context["exit"] = True

                    # Remove the <|stop|> marker from the response content
                    cleaned_content = res.content.replace("<|stop|>", "")

                    self.context.add_item(
                        AgentResponse(
                            start_time=start_time,
                            end_time=Instant.now(),
                            content=cleaned_content,
                        ),
                        section="process",
                    )
                    return

            self.context.add_item(
                AgentResponse(
                    start_time=start_time,
                    end_time=Instant.now(),
                    content=res.content,
                    tool_calls=(
                        [
                            AgentToolCall(
                                id=item.id,
                                tool_name=item.tool_name,
                                tool_args=item.tool_args,
                            )
                            for item in res.tool_calls
                        ]
                        if res.tool_calls
                        else None
                    ),
                ),
                section="process",
            )

            return

        # No content or tool calls, so exit the loop
        self.iteration_context["exit"] = True

    async def stream_generate(self):
        """Stream a textual response from the language model."""
        pass

    async def stream_tool_call(self):
        """Stream tool calls from the language model."""
        pass

    async def stream_generate_with_tool_call(self):
        """Stream a response from the language model, including tool calls."""
        pass

    # TODO
    async def execute_tool_calls(self):
        """Execute tool calls specified in the context."""
        tool_calls: AgentResponse = (
            query(self.context.latest().process)
            .where(lambda x: isinstance(x, AgentResponse))
            .first_or_default(default=None)
        )

        if not tool_calls or not tool_calls.tool_calls:
            return

        self.iteration_context["tool_call_results"] = []
        # Ask for approval for all tool calls first and store the approvals
        approvals = {}
        for call in tool_calls.tool_calls:
            approval = input(
                f"Tool call: {call.id} {call.tool_name}({', '.join(f'{k}={repr(v)}' for k, v in call.tool_args.items())}). Do you want to execute it? (Y/n): "
            )
            approvals[call.id] = (
                (approval.lower() == "y")
                or (approval.lower() == "yes")
                or (approval == "")
            )

        # Execute only approved tool calls in parallel and wait for all to finish
        async def execute_call(call):
            if not approvals.get(call.id, False):
                return AgentToolCallResult(
                    id=call.id,
                    results="**THE USER REFUSED TO EXECUTE THIS TOOL CALL**",
                )
            res = await self.toolbox.call(call.tool_name, **call.tool_args)
            return AgentToolCallResult(id=call.id, results=str(res))

        start_time = Instant.now()
        tasks = [execute_call(call) for call in tool_calls.tool_calls]
        results = await asyncio.gather(*tasks)
        self.iteration_context["tool_call_results"].extend(results)

        self.context.add_item(
            AgentToolCallResults(
                start_time=start_time,
                end_time=Instant.now(),
                tool_call_results=self.iteration_context["tool_call_results"],
            ),
            section="process",
        )

    async def execute_streaming_tool_calls(self):
        """Execute tool calls streaming from `stream_tool_call` or `stream_generate_with_tool_call`."""
        pass


class AgentLoop:
    _process_fn: Callable[[ProcessFunctionContext], "asyncio.Future"]
    _retrigger_fn: Callable

    _prologue_fns: Dict[str, Dict[str, Callable]] = {}
    _epilogue_fns: Dict[str, Dict[str, Callable]] = {}

    modules: Dict[str, AgentLoopModule] = {}
    lm: LanguageModel

    def __init__(self, mgr, *args, **kwargs):
        self.mgr = mgr

    async def _async_function_executor_base(
        self,
        functions: Dict[str, Dict[str, Callable]],
        name: str,
        context: AgentContext,
        iteration_context: dict = None,
    ):
        async def run_in_executor(fn, module_name, fn_name, *args, **kwargs):
            loop = asyncio.get_running_loop()

            with ThreadPoolExecutor() as executor:
                return await loop.run_in_executor(
                    executor, lambda: fn(self.modules[module_name], *args, **kwargs)
                )

        tasks = []
        for module_name, fns in functions.items():
            for fn_name, fn in fns.items():
                tasks.append(
                    run_in_executor(
                        fn,
                        module_name,
                        fn_name,
                        context=context,
                        iteration_context=iteration_context,
                    )
                )
        if tasks:
            await asyncio.gather(*tasks)

    async def prologue_stage(
        self, context: AgentContext, iteration_context: dict = None
    ):
        await self._async_function_executor_base(
            self._prologue_fns,
            "prologue",
            context=context,
            iteration_context=iteration_context,
        )

    async def epilogue_stage(
        self, context: AgentContext, iteration_context: dict = None
    ):
        await self._async_function_executor_base(
            self._epilogue_fns,
            "epilogue",
            context=context,
            iteration_context=iteration_context,
        )

    async def __call__(
        self,
        context: AgentContext,
        *args,
        loop: bool = True,
        **kwargs,
    ):
        """Run the agent loop with the provided context.

        Args:
            context (AgentContext): The context for the agent loop.
            loop (bool, optional): Whether to loop the agent. Defaults to True.
        """

        exited = False

        iteration: int = context.latest().index + 1

        # % TODO: Handle a way for the user to pause/resume the loop
        # % TODO: Handle a way for the user to add messages to the context during the loop

        # % TODO: Make it dynamic and adaptive, so that it adapts to the changes in its modules, tools, etc.

        while not exited:
            console.print(
                f"[bold green]******************** Iteration {iteration:03d} ********************[/bold green]"
            )

            # This is storing temporary items like optimized tool calls, etc.
            iteration_context = {
                "best_tools": self.mgr.tools.flatten(),
            }

            await self.prologue_stage(
                context=context, iteration_context=iteration_context
            )

            await self._process_fn(
                ProcessFunctionContext(
                    self.lm,
                    context,
                    tools=iteration_context.get("best_tools", []),
                    toolbox=self.mgr.tools,
                    iteration_context=iteration_context,
                    **kwargs,
                )
            )

            if "exit" in iteration_context:
                exited = iteration_context["exit"]
                logger.debug("Exit condition met, exiting the loop.")

            # TODO: Add options to exit before or after epilogue
            await self.epilogue_stage(
                context=context, iteration_context=iteration_context
            )

            if exited or not loop:
                # ? Redundant, since exit tool is replaced by <|stop|> marker
                # # # Remove the exit tool call, if it exists
                # # # Because, it will cause openai to complain about no-results provided
                # tool_calls_obj: Optional[AgentResponse] = (
                #     query(context.latest().process)
                #     .where(lambda x: isinstance(x, AgentResponse))
                #     .first_or_default(default=None)
                # )

                # if tool_calls_obj is not None:
                #     # Find the exit tool call and remove it
                #     for call in tool_calls_obj.tool_calls:
                #         if call.tool_name == "exit":
                #             context.remove_item(
                #                 tool_calls_obj.context_id, section="process"
                #             )

                context.latest().end_time = Instant.now()

                logger.debug("Exiting agent loop.")
                break

            context.new()
            iteration += 1

    def process(self, fn: Callable[[ProcessFunctionContext], "asyncio.Future"]):
        self._process_fn = fn
        return self._process_fn

    def retrigger(self, fn):
        self._retrigger_fn = fn
        return self._retrigger_fn

    def use(self, *modules: AgentLoopModule) -> Self:
        """Register modules to the agent loop.

        Returns:
            Self: The current instance of the agent loop.
        """
        for module in modules:
            self.modules[module.__class__.__name__] = module

            # register prologue items
            self._prologue_fns[module.__class__.__name__] = module.functions["prologue"]
            # register epilogue items
            self._epilogue_fns[module.__class__.__name__] = module.functions["epilogue"]
            self.modules[module.__class__.__name__] = module

            # Log the names of prologue and epilogue functions
            prologue_keys = list(module.functions["prologue"].keys())
            epilogue_keys = list(module.functions["epilogue"].keys())

            if len(prologue_keys) == 0 and len(epilogue_keys) == 0:
                logger.warning(
                    f"Module `{module.__class__.__name__}` has no prologue or epilogue functions in it"
                )

            else:
                logger.debug(
                    f"Module `{module.__class__.__name__}`: {len(prologue_keys)} prologue, {len(epilogue_keys)} epilogue functions"
                )

            # register tools
            if hasattr(module, "tool_namespace"):
                self.mgr.tools.add(module.tool_namespace, module)
                logger.debug(
                    f"Module `{module.__class__.__name__}`: namespace `{module.tool_namespace}` with {len(module.tool_functions.keys())} tools registered"
                )

        return self

    def clone(self) -> "AgentLoop":
        """Create a deep copy of the AgentLoop instance."""
        return copy.deepcopy(self)
