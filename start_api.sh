#!/usr/bin/env bash
"""
Start the Muleta Cognitiva API server.
"""

cd "$(dirname "$0")"

echo "Starting Muleta Cognitiva API server..."
echo "Server will be available at: http://127.0.0.1:8000"
echo "API documentation at: http://127.0.0.1:8000/docs"
echo "Health check at: http://127.0.0.1:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uv run python -m src.api.main
