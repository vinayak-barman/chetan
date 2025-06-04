from ..tools.toolbox import Toolbox
from pydantic import BaseModel, Field
from ..tools import Tool, ToolFunction, ToolInformation, toolfn

class SampleTool(Tool):
    tool_info = ToolInformation(
        id="sample_tool",
        description="A sample tool for testing.",
        tags="test, sample",
        matchers=["sample", "test"],
    )

    @toolfn
    def uppercasify(self, input: str) -> str:
        """Convert input string to uppercase.

        Args:
            input (str): The input string to convert.

        Returns:
            str: The converted uppercase string.
        """
        return input.upper()
def test_tool_function():
    @toolfn
    def sample_tool_function(input: str) -> str:
        return input.upper()

    assert sample_tool_function.is_tool
    assert sample_tool_function("test") == "TEST"


def test_tool():
    

    tool = SampleTool()
    assert isinstance(tool, Tool)
    assert len(tool.tool_functions) == 1
    assert tool.tool_functions[0].name == "uppercasify"

    class InputModel(BaseModel):
        input: str = Field(..., description="The input string to convert.")

    assert (
        tool.tool_functions[0].input.model_json_schema()["properties"]
        == InputModel.model_json_schema()["properties"]
    )
    assert tool.tool_functions[0].output is str
    assert tool.tool_functions[0].fn("test") == "TEST"
