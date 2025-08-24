import asyncio
import json
import socket
import threading
import time

import pytest

from api import mcp_server

HOST = "127.0.0.1"
PORT = 8766  # Use a test port


@pytest.fixture(scope="module")
def server_thread():
    """Start MCP server in a background thread for testing."""

    def run():
        asyncio.run(mcp_server.MCPServer(host=HOST, port=PORT).start())

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(1.0)  # Wait longer for server to start with all tools
    yield
    # No explicit shutdown; daemon thread will exit


def send_recv(msg):
    """Send a message to the MCP server and receive response."""
    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.sendall((json.dumps(msg) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.decode().strip())


def test_tool_discovery(server_thread):
    """Test tool discovery returns all registered tools."""
    resp = send_recv({"type": "tool_discovery"})
    assert resp["type"] == "tool_list"
    assert isinstance(resp["tools"], list)
    assert len(resp["tools"]) > 0

    # Check that we have the expected core tools
    tool_names = [tool["name"] for tool in resp["tools"]]
    expected_tools = [
        "process_content",
        "get_entities",
        "get_entity",
        "get_due_cards",
        "generate_cards",
        "health_check",
    ]
    for expected_tool in expected_tools:
        assert expected_tool in tool_names


def test_tool_metadata(server_thread):
    """Test that tools have proper metadata."""
    resp = send_recv({"type": "tool_discovery"})
    tools = resp["tools"]

    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert isinstance(tool["name"], str)
        assert isinstance(tool["description"], str)
        assert isinstance(tool["parameters"], dict)


def test_unknown_message_type(server_thread):
    """Test handling of unknown message types."""
    resp = send_recv({"type": "unknown_type"})
    assert "error" in resp
    assert "unknown message type" in resp["error"]


def test_invoke_missing_tool(server_thread):
    """Test invocation of non-existent tool."""
    resp = send_recv({"type": "invoke_tool", "tool": "not_exist"})
    assert "error" in resp
    assert "not found" in resp["error"]


def test_invoke_tool_missing_name(server_thread):
    """Test tool invocation without tool name."""
    resp = send_recv({"type": "invoke_tool"})
    assert "error" in resp
    assert "missing tool name" in resp["error"]


def test_health_check_tool(server_thread):
    """Test the health check tool."""
    resp = send_recv({"type": "invoke_tool", "tool": "health_check", "args": {}})
    assert resp["type"] == "tool_result"
    result = resp["result"]
    assert result["status"] == "ok"
    assert "version" in result


def test_process_content_tool(server_thread):
    """Test the process content tool (placeholder implementation)."""
    resp = send_recv(
        {
            "type": "invoke_tool",
            "tool": "process_content",
            "args": {"content": "Test content", "source_type": "text"},
        }
    )
    assert resp["type"] == "tool_result"
    result = resp["result"]
    assert "success" in result
    assert "entities_created" in result
    assert "relations_created" in result


def test_get_entities_tool(server_thread):
    """Test the get entities tool."""
    resp = send_recv({"type": "invoke_tool", "tool": "get_entities", "args": {}})
    assert resp["type"] == "tool_result"
    result = resp["result"]
    assert "entities" in result
    assert isinstance(result["entities"], list)


def test_get_entity_tool(server_thread):
    """Test the get entity tool."""
    resp = send_recv(
        {"type": "invoke_tool", "tool": "get_entity", "args": {"entity_id": 1}}
    )
    assert resp["type"] == "tool_result"
    result = resp["result"]
    assert "entity" in result
    entity = result["entity"]
    assert "id" in entity
    assert "name" in entity
    assert "observations" in entity
    assert "relations" in entity


def test_invalid_json(server_thread):
    """Test handling of invalid JSON."""
    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.sendall(b"invalid json\n")
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        resp = json.loads(data.decode().strip())
        assert "error" in resp
        assert "invalid json" in resp["error"]


def test_tool_with_args(server_thread):
    """Test tool invocation with arguments."""
    resp = send_recv(
        {
            "type": "invoke_tool",
            "tool": "generate_cards",
            "args": {"entity_ids": [1, 2, 3], "card_types": ["definition", "socratic"]},
        }
    )
    assert resp["type"] == "tool_result"
    result = resp["result"]
    assert "cards_created" in result
    assert "cards" in result
