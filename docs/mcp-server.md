# MCP Server Implementation

## Overview

The MCP server (`api/mcp_server.py`) implements the Model Context Protocol (MCP) for tool discovery and invocation. It supports:
- Tool registration and listing
- Handling of tool discovery and invocation messages
- Basic protocol compliance

## Usage

To start the server:
```sh
python api/mcp_server.py
```

## Protocol
- `tool_discovery`: Returns a list of registered tools
- `invoke_tool`: Invokes a registered tool (currently empty registry)

## Testing

- Protocol and compliance tests in `api/tests/test_mcp_server.py`
- Tests cover tool discovery, unknown message types, and missing tool invocation

## Extending
- Register new tools using the `ToolRegistry` in `mcp_server.py`
