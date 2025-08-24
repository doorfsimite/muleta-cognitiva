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
    def run():
        asyncio.run(mcp_server.MCPServer(host=HOST, port=PORT).start())

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.5)  # Wait for server to start
    yield
    # No explicit shutdown; daemon thread will exit


def send_recv(msg):
    with socket.create_connection((HOST, PORT), timeout=2) as sock:
        sock.sendall((json.dumps(msg) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            data += sock.recv(4096)
        return json.loads(data.decode())


def test_tool_discovery(server_thread):
    resp = send_recv({"type": "tool_discovery"})
    assert resp["type"] == "tool_list"
    assert isinstance(resp["tools"], list)


def test_unknown_message_type(server_thread):
    resp = send_recv({"type": "unknown_type"})
    assert "error" in resp
    assert resp["error"] == "unknown message type"


def test_invoke_missing_tool(server_thread):
    resp = send_recv({"type": "invoke_tool", "tool": "not_exist"})
    assert "error" in resp
    assert resp["error"] == "tool not found"
