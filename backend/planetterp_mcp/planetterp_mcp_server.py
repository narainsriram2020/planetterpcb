from backend.planetterp_mcp.mcp_stub import MCPServer, ToolResult
from backend.planetterp_mcp.qdrant_tools import QdrantTools
from backend.planetterp_core import get_course, get_professor

PLANETTERP_MCP_SERVER = MCPServer(
    name="planet-terp",
    description="PlanetTerp data MCP (semantic + API tools)"
)

# Register Qdrant semantic tools
PLANETTERP_MCP_SERVER.register_toolset(QdrantTools())

@PLANETTERP_MCP_SERVER.tool()
def get_course_details(course_id: str):
    return {"course": get_course(course_id)}

@PLANETTERP_MCP_SERVER.tool()
def get_professor_info(name: str):
    return {"professor": get_professor(name)}

if __name__ == "__main__":
    PLANETTERP_MCP_SERVER.run(port=8001)
