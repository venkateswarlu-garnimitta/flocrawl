"""
Entry point for running the Flocrawl MCP Server.

Usage:
    python -m flocrawl
"""

import asyncio

from flocrawl.server import main

if __name__ == "__main__":
    asyncio.run(main())
