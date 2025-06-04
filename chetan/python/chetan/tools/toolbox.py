from typing import Dict, List, Union, Optional, TYPE_CHECKING
from chetan.tools import Tool, ToolFunction
import inspect

if TYPE_CHECKING:
    ToolNamespaceType = 'ToolNamespace'
else:
    ToolNamespaceType = object


class ToolNamespace:
    """
    Represents a namespace that can contain tools, tool functions, and/or other namespaces.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        max_depth: Optional[int] = None,
        depth: int = 0,
    ):
        self.name = name
        self.children: Dict[str, Union[Tool, 'ToolNamespace', ToolFunction]] = {}
        self.max_depth = max_depth
        self.depth = depth

    def register(self, name: str, obj: Union[Tool, 'ToolNamespace', ToolFunction]):
        if self.max_depth is not None and self.depth >= self.max_depth:
            raise ValueError(
                f"Max namespace depth {self.max_depth} exceeded at '{name}'"
            )
        self.children[name] = obj

    def get(self, path: str) -> Union[Tool, 'ToolNamespace', ToolFunction, None]:
        parts = path.split(".")
        node = self
        for i, part in enumerate(parts):
            if part not in node.children:
                return None
            node = node.children[part]
            if isinstance(node, Tool) and i < len(parts) - 1:
                # If we hit a Tool before the end, check if next part is a tool function
                next_part = parts[i + 1]
                if hasattr(node, "tool_functions") and next_part in node.tool_functions:
                    return node.tool_functions[next_part]
                else:
                    return None
        return node

    def __getitem__(self, key):
        return self.children[key]

    def __contains__(self, key):
        return key in self.children

    def print_tree(self, indent: str = "", is_last: bool = True):
        """
        Print an ASCII tree representation of the namespace and its children, with vertical bars for siblings.
        """
        if self.name is None:
            # Root node
            print("<root>")
            children_items = list(self.children.items())
            for idx, (key, child) in enumerate(children_items):
                last = idx == len(children_items) - 1
                if isinstance(child, ToolNamespace):
                    child.print_tree(indent, is_last=last)
                elif isinstance(child, Tool):
                    branch = "└─" if last else "├─"
                    print(f"{indent}{branch}{key} [Tool]")
                    tool_functions = list(child.tool_functions)
                    for fn_idx, fn in enumerate(tool_functions):
                        fn_last = fn_idx == len(tool_functions) - 1
                        fn_branch = "└─" if fn_last else "├─"
                        fn_indent = indent + ("   " if last else "│  ")
                        print(f"{fn_indent}{fn_branch}{fn}()")
                elif isinstance(child, ToolFunction):
                    branch = "└─" if last else "├─"
                    print(f"{indent}{branch}{key}()")
            return

        branch = "└─" if is_last else "├─"
        print(f"{indent}{branch}{self.name}")
        new_indent = indent + ("   " if is_last else "│  ")
        children_items = list(self.children.items())
        for idx, (key, child) in enumerate(children_items):
            last = idx == len(children_items) - 1
            if isinstance(child, ToolNamespace):
                child.print_tree(new_indent, is_last=last)
            elif isinstance(child, Tool):
                tool_branch = "└─" if last else "├─"
                print(f"{new_indent}{tool_branch}{key} [Tool]")
                tool_functions = list(child.tool_functions)
                for fn_idx, fn in enumerate(tool_functions):
                    fn_last = fn_idx == len(tool_functions) - 1
                    fn_branch = "└─" if fn_last else "├─"
                    fn_indent = new_indent + ("   " if last else "│  ")
                    print(f"{fn_indent}{fn_branch}{fn}()")
            elif isinstance(child, ToolFunction):
                branch = "└─" if last else "├─"
                print(f"{new_indent}{branch}{key}()")

    def flatten(self, prefix: str = "", delimeter: str = ".") -> List[ToolFunction]:
        """
        Flatten the namespace into a list of all ToolFunctions contained within it,
        renaming each ToolFunction's name to its fully qualified path (dot-separated).
        """
        tools = []
        for key, child in self.children.items():
            if isinstance(child, ToolNamespace):
                # Recurse with full path
                new_prefix = f"{prefix}{delimeter}{key}" if prefix else key
                tools.extend(child.flatten(prefix=new_prefix, delimeter=delimeter))
            elif isinstance(child, Tool):
                tool_prefix = f"{prefix}{delimeter}{key}" if prefix else key
                for fn_name, fn in child.tool_functions.items():
                    fn.name = f"{tool_prefix}{delimeter}{fn_name}"
                    tools.append(fn)
            elif isinstance(child, ToolFunction):
                if prefix:
                    child.name = f"{prefix}{delimeter}{key}"
                else:
                    child.name = key
                tools.append(child)
        return tools


class Toolbox(ToolNamespace):
    """
    A tree of tools, in a namespace-like hierarchy.
    Root namespace for all tools.
    """

    def __init__(self, max_depth: Optional[int] = None):
        super().__init__(name=None, max_depth=max_depth, depth=0)

    def register(self, path: str, obj: Union[Tool, ToolNamespace, ToolFunction]):
        """
        Register a tool, tool function, or namespace at the given dot-separated path.
        """
        if path == "":
            # Add to root
            if isinstance(obj, ToolFunction):
                super().register(obj.name, obj)
                return
            # If it's a Tool with a single function, add the ToolFunction directly
            if isinstance(obj, Tool) and len(obj.tool_functions) == 1:
                fn = next(iter(obj.tool_functions.values()))
                super().register(fn.name, fn)
                return
            # Otherwise, add as a Tool (for multi-function tools)
            name = obj.__class__.__name__.lower()
            super().register(name, obj)
            return
        parts = path.split(".")
        if len(parts) == 1:
            super().register(parts[0], obj)
            return
        node = self
        for i, part in enumerate(parts[:-1]):
            if part not in node.children or not isinstance(
                node.children[part], ToolNamespace
            ):
                # Create intermediate namespaces as needed
                node.children[part] = ToolNamespace(
                    name=part, max_depth=self.max_depth, depth=node.depth + 1
                )
            node = node.children[part]
        node.register(parts[-1], obj)

    def get(self, path: str):
        parts = path.split(".")
        node = self
        for i, part in enumerate(parts):
            if part not in node.children:
                return None
            node = node.children[part]
            if isinstance(node, Tool) and i < len(parts) - 1:
                # If we hit a Tool before the end, check if next part is a tool function
                next_part = parts[i + 1]
                if hasattr(node, "tool_functions") and next_part in node.tool_functions:
                    return node.tool_functions[next_part]
                else:
                    return None
        return node

    async def call(self, path: str, **kwargs):
        """
        Call a tool function by dot-separated path, e.g. 'utility.terminal.execute'.
        """
        parts = path.split(".")
        tool_path = ".".join(parts[:-1])
        func_name = parts[-1]
        tool = self.get(tool_path)
        if isinstance(tool, Tool):
            if func_name not in tool.tool_functions:
                raise ValueError(f"Function '{func_name}' not found in tool '{tool_path}'")
            fn = tool.tool_functions[func_name].fn
            # If fn is a bound method, __self__ is set; otherwise, it's unbound and needs self
            if hasattr(fn, "__self__") and fn.__self__ is not None:
                result = fn(**kwargs)
            else:
                result = fn(tool, **kwargs)
            if inspect.iscoroutine(result):
                return await result
            else:
                return result
        elif isinstance(tool, ToolFunction):
            fn = tool.fn
            result = fn(**kwargs)
            if inspect.iscoroutine(result):
                return await result
            else:
                return result
        else:
            raise ValueError(f"Tool not found at path: {tool_path}")
