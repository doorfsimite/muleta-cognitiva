#!/usr/bin/env python3
"""
Simple HTTP server to serve the web interface for testing.
Serves the index.html file and provides CORS support for API calls.
"""

import http.server
import socketserver
import os
from pathlib import Path


class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support."""
    
    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.end_headers()


def serve_web_interface(port=3000):
    """
    Serve the web interface on the specified port.
    
    Args:
        port (int): Port to serve on (default: 3000)
    """
    # Change to the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Create HTTP server
    handler = CORSHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"✅ Serving web interface at http://localhost:{port}")
            print(f"📁 Serving from: {project_root}")
            print(f"🌐 Open http://localhost:{port} in your browser")
            print("Press Ctrl+C to stop the server")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"   python scripts/serve_web.py --port {port + 1}")
        else:
            print(f"❌ Error starting server: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Serve the Muleta Cognitiva web interface")
    parser.add_argument("--port", "-p", type=int, default=3000, 
                       help="Port to serve on (default: 3000)")
    
    args = parser.parse_args()
    serve_web_interface(args.port)
