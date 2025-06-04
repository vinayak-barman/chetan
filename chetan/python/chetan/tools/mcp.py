from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
import humps
from loguru import logger

from typing import Dict, Union

from chetan.tools import Tool, ToolFunction
from pydantic import create_model


def create_model_from_json_schema(schema_name, schema_json):
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        # Add other mappings as needed
    }
    fields = {}
    for field_name, field_schema in schema_json.get("properties", {}).items():
        field_type = field_schema.get("type")
        if field_type and field_type in type_mapping:
            fields[field_name] = (type_mapping[field_type], ...)
    return create_model(schema_name, **fields)


def check_remote(path: Union[str, StdioServerParameters]):
    """Check whether a given URL is local or remote.

    Args:
        path (str): The path to check.

    Returns:
        bool: True if the path is remote, False if local.
    """
    if isinstance(path, StdioServerParameters):
        return False
    return path.startswith(("http://", "https://"))


class MCPTool(Tool):
    session: ClientSession

    def __init__(self, session):
        self.session = session
        super().__init__()

    async def __call__(self, mcp_toolfn: str, **kwargs):
        return await self.tool_functions[mcp_toolfn].fn(self, **kwargs)


def handle_mcp_tool_call(name: str):
    async def tool_call(self: MCPTool, **kwargs):
        return (
            (await self.session.call_tool(name=name, arguments=kwargs)).content[0].text
        )

    return tool_call


def redact_env(
    item: Union[StdioServerParameters, str],
) -> Union[StdioServerParameters, str]:
    """Redact sensitive information from StdioServerParameters."""
    if isinstance(item, StdioServerParameters):
        if not item.env:
            return item
        
        redacted_env = {
            k: (v[:5] + "*" * (len(v) - 5) if isinstance(v, str) and len(v) > 5 else v)
            for k, v in item.env.items()
        }
        return StdioServerParameters(
            command=item.command,
            args=item.args,
            env=redacted_env,
            cwd=item.cwd,
        )
    return item


class MCPLoader:
    @classmethod
    async def load_from_paths(
        cls, mcp_tool_paths: Dict[str, Union[str, StdioServerParameters]], **kwargs
    ) -> Dict[str, Tool]:
        """
        Load tools from the specified MCP tool paths.

        Args:
            mcp_tool_paths (list[str]): List of paths to MCP tool files.

        Returns:
            List[Tool]: List of loaded tools.
        """
        tools = {}
        logger.info(
            f"Starting to load MCP tools from paths: {list(mcp_tool_paths.keys())}"
        )
        for name, item in mcp_tool_paths.items():
            logger.info(f"Loading MCP tool '{name}' from: {redact_env(item)}")
            try:
                tool = await cls.load(name, item, remote=check_remote(item), **kwargs)
                tools[name] = tool
                logger.success(
                    f"Successfully loaded MCP tool '{name}' from: {redact_env(item)}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to load MCP tool '{name}' from: {redact_env(item)}. Error: {e}"
                )
        logger.info(f"Finished loading MCP tools. Loaded: {list(tools.keys())}")
        return tools

    @classmethod
    async def load(
        cls,
        name: str,
        target: Union[str, StdioServerParameters],
        remote: bool = False,
        python_default="python",
        js_default="node",
    ) -> MCPTool:
        logger.info(
            f"Initializing MCP tool. Target: {redact_env(target)}, Remote: {remote}"
        )
        if not remote:
            params = target
            if not isinstance(target, StdioServerParameters):
                is_python = target.endswith(".py")
                is_js = target.endswith(".js")
                if not (is_python or is_js):
                    logger.error(f"Server script must be a .py or .js file: {target}")
                    raise ValueError("Server script must be a .py or .js file")

                command = python_default if is_python else js_default
                params = StdioServerParameters(command=command, args=target.split(" "))
                logger.debug(f"Using command '{command}' for target '{target}'")
            client_ctx = stdio_client(params)
            anonymized_env = redact_env(params)
            logger.debug(f"Created stdio client context for: {anonymized_env}")
        else:
            client_ctx = sse_client(target)
            anonymized_env = redact_env(target)
            logger.debug(f"Created SSE client context for: {anonymized_env}")

        # Instead of using context managers, manually create and keep streams/session open
        streams = (
            await client_ctx.__aenter__()
        )  # Correct way to enter async context manager
        logger.debug(f"Streams opened for target: {anonymized_env}")
        session = await ClientSession(
            streams[0], streams[1]
        ).__aenter__()  # Also enter session context manually
        logger.debug(f"ClientSession started for target: {anonymized_env}")
        await session.initialize()
        logger.info(f"Session initialized for target: {anonymized_env}")
        tool_functions = await session.list_tools()
        logger.info(
            f"Discovered {len(tool_functions.tools)} tool functions for target: {anonymized_env}"
        )
        tool = MCPTool(session=session)
        tool._streams = streams  # Store streams for later use if needed
        tool._client_ctx = client_ctx  # Store client_ctx for later use if needed
        tool._session_ctx = (
            session  # Store session context for manual cleanup if needed
        )

        for t in tool_functions.tools:
            logger.info(f"Registering tool function: {t.name}")
            tool.tool_functions[t.name] = ToolFunction(
                name=t.name,
                description=t.description,
                input=create_model_from_json_schema(
                    f"{humps.pascalize(t.name)}Input", t.inputSchema
                ),
                output=None,
                fn=handle_mcp_tool_call(t.name),
            )

        logger.success(f"MCP tool ready for target: {anonymized_env}")
        return tool
