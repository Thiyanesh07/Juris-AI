"""
Windows-compatible uvicorn launcher.

On Windows, uvicorn uses ProactorEventLoop by default which is incompatible
with psycopg3 async mode. This launcher forces SelectorEventLoop before
uvicorn creates its event loop, so PostgreSQL connections work correctly.

Usage:
    python run_server.py [--port 8000] [--host 0.0.0.0] [--reload]
"""
import asyncio
import selectors
import sys

# MUST be set before any uvicorn import to take effect
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import argparse
import uvicorn

parser = argparse.ArgumentParser(description="Start the Juris AI API server")
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--reload", action="store_true")
parser.add_argument("--log-level", default="info")
args = parser.parse_args()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        # Explicitly use asyncio loop to avoid Proactor
        loop="asyncio",
    )
