#!/usr/bin/env python3
"""
Simple HTTP server to serve the HTML site locally for testing.
Run with: python serve_html.py [port]
Default port is 8000.
"""

import http.server
import socketserver
import sys
import os
from pathlib import Path

def main():
    # Default port
    PORT = 8000

    # Allow custom port from command line
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            print(f"Error: Invalid port number '{sys.argv[1]}'")
            sys.exit(1)

    # Change to the HTML site directory (go up to project root first)
    html_dir = Path(__file__).parent.parent / "output" / "html_site"

    if not html_dir.exists():
        print(f"Error: HTML site directory not found at {html_dir}")
        print("Run the HTML export first with:")
        print("  python sfs_processor.py --formats html")
        sys.exit(1)

    os.chdir(html_dir)

    # Create server
    Handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving HTML site at http://localhost:{PORT}")
        print(f"Directory: {html_dir}")
        print("Press Ctrl+C to stop")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    main()
