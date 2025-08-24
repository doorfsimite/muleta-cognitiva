"""
Basic MCP server implementation for Muleta Cognitiva.
"""
import asyncio
import json
from typing import Any, Callable, Dict


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self.tools[name] = func

    def get(self, name: str):
        return self.tools.get(name)

    def list_tools(self):
        return list(self.tools.keys())

class MCPServer:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.registry = ToolRegistry()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"Connection from {addr}")
        while True:
            data = await reader.readline()
            if not data:
                break
            try:
                msg = json.loads(data.decode())
            except Exception as e:
                writer.write(b'{"error": "invalid json"}\n')
                await writer.drain()
                continue
            response = await self.handle_message(msg)
            writer.write((json.dumps(response) + "\n").encode())
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def handle_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        if msg.get("type") == "tool_discovery":
            return {"type": "tool_list", "tools": self.registry.list_tools()}
        elif msg.get("type") == "invoke_tool":
            tool = self.registry.get(msg.get("tool"))
            if not tool:
                return {"error": "tool not found"}
            try:
                result = await tool(msg.get("args", {}))
                return {"type": "tool_result", "result": result}
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": "unknown message type"}

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"MCP server running on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(MCPServer().start())
