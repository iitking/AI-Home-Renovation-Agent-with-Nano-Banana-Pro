#!/usr/bin/env python3
"""Run the AI Home Renovation Agent Web UI Server."""
import argparse
import sys
from pathlib import Path

# Ensure src is on python path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from renovation_agent.server import start_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Home Renovation Agent Web UI")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    start_server(port=args.port, open_browser=not args.no_browser)
