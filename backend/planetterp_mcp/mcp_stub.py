import asyncio
import inspect


class ToolResult:
    def __init__(self, content):
        self.content = content


class MCPServer:
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tools = {}

    async def call_tool(self, name: str, arguments: dict):
        """Mimics the async call interface of the real MCPServer."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found in MCPServer.")
        tool_func = self.tools[name]
        if callable(tool_func):
            result = tool_func(**arguments) if arguments else tool_func()
            # Await coroutines from async tool functions
            if inspect.isawaitable(result):
                result = await result
            return result
        return None

    def tool(self, **kwargs):
        def decorator(func):
            name = kwargs.get("name") or func.__name__
            self.tools[name] = func
            return func
        return decorator

    def register_toolset(self, toolset):
        for attr in dir(toolset):
            method = getattr(toolset, attr)
            if callable(method) and not attr.startswith("_"):
                self.tools[attr] = method

    def list_tools(self):
        return list(self.tools.keys())

    def run(self, port: int = 8001):
        print(f"🧩 MCP mock server running on port {port}")
        print("Available tools:")
        for name in self.list_tools():
            print(" -", name)


def Tool(**kwargs):
    """No-op decorator stub so @Tool(...) works without real MCP SDK."""
    def decorator(func):
        return func
    return decorator