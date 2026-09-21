"""Verify the MCP server registers its tools correctly (no backend needed).

Run with the mcp_server/.venv python so FastMCP is importable.
"""
import asyncio
from fastmcp import Client

SERVER = "D:/工作/ww/personal_work/study_trace/mcp_server/study_trace_mcp.py"


async def main():
    async with Client(SERVER) as c:
        tools = await c.list_tools()
        print("REGISTERED TOOLS:", [t.name for t in tools])
        # get_meta calls the backend, so it may fail if 28000 is unreachable
        # here we only check tool discovery which is independent of the API.


asyncio.run(main())
