"""
Entry point for running the Flocrawl MCP Server.

Usage:
    python -m flotorch_crawl
"""

import asyncio

from flotorch_crawl.server import main

if __name__ == "__main__":
    asyncio.run(main())
