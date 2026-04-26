from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .planetterp_server import PLANETTERP_MCP_SERVER

app = FastAPI(title="PlanetTerp MCP Server")

# Schema for invoking a tool
class InvokeRequest(BaseModel):
    tool_name: str
    arguments: dict | None = None


@app.get("/mcp/list_tools")
def list_tools():
    return {"tools": PLANETTERP_MCP_SERVER.list_tools()}


@app.post("/mcp/invoke")
async def invoke_tool(req: InvokeRequest):
    if req.tool_name not in PLANETTERP_MCP_SERVER.tools:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found")

    tool_func = PLANETTERP_MCP_SERVER.tools[req.tool_name]
    args = req.arguments or {}
    try:
        result = tool_func(**args)
        # Await coroutines from async tool functions
        import inspect
        if inspect.isawaitable(result):
            result = await result
        # Handle ToolResult object or raw dict
        if hasattr(result, "content"):
            return {"result": result.content}
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "tools_registered": PLANETTERP_MCP_SERVER.list_tools()}
