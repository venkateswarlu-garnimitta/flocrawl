#!/usr/bin/env python3
"""
Flocrawl MCP Server.

Exposes web search, scraping, link discovery, and recursive crawl tools via FastMCP.
"""

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import httpx
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

load_dotenv()
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from flocrawl.config import get_request_timeout, get_user_agent
from flocrawl.scraper import (
    list_links_async,
    scrape_links_async,
    scrape_url_async,
    scrape_urls_async,
)
from flocrawl.search import search_web

logging.basicConfig(
    format="[%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(fn, *args, **kwargs):
    """Run sync blocking function in thread pool (used for search_web)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, lambda: fn(*args, **kwargs))


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        follow_redirects=True,
        timeout=get_request_timeout(),
        headers={"User-Agent": get_user_agent()},
    )


mcp = FastMCP(
    "Flocrawl",
    instructions=(
        "Flocrawl MCP Server: Web search, scraping, link discovery, "
        "and recursive crawling. Use search_web for web search, scrape_url for "
        "single-page content, list_links to discover links, scrape_links to "
        "crawl and scrape multiple pages from a starting URL, and scrape_urls "
        "to scrape a list of URLs in parallel when you already have the links."
    ),
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    stateless_http=True,
)


async def _run_sync(fn, *args, **kwargs):
    """Run sync blocking function in thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, lambda: fn(*args, **kwargs))


@mcp.custom_route("/.well-known/flocrawl-mcp", methods=["GET"])
async def discovery(_request: Request) -> JSONResponse:
    """Discovery endpoint for transport detection."""
    return JSONResponse({
        "transport": "HTTP_STREAMABLE",
        "protocol": "streamable-http",
        "message": "Flocrawl MCP Server - Set transport to HTTP_STREAMABLE",
    })


@mcp.tool()
async def search_web_tool(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
) -> str:
    """
    Perform a web search and return results with titles, URLs, and snippets.

    Uses DuckDuckGo. No API keys required.

    Args:
        query: Search query string.
        max_results: Maximum number of results (default 10).
        region: Region for search, e.g. wt-wt (global), us-en, uk-en.

    Returns:
        JSON string with list of {title, url, snippet}.
    """
    try:
        results = await _run_sync(search_web, query, max_results, region)
        return json.dumps({"results": results}, indent=2)
    except Exception as e:
        logger.exception("search_web failed")
        return json.dumps({"error": str(e), "results": []})


@mcp.tool()
async def scrape_url_tool(url: str) -> str:
    """
    Scrape a single URL and extract main text content.

    Fetches the page, removes scripts/styles, and returns cleaned text.

    Args:
        url: Full URL to scrape (e.g. https://example.com/page).

    Returns:
        JSON with url, title, text, and optional error.
    """
    try:
        async with _make_client() as client:
            result = await scrape_url_async(url, client)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.exception("scrape_url failed")
        return json.dumps({"url": url, "title": "", "text": "", "error": str(e)})


@mcp.tool()
async def list_links_tool(url: str, same_domain_only: bool = True) -> str:
    """
    List all links found on a webpage.

    Fetches the URL and extracts anchor tags with href. Optionally filters
    to links on the same domain only.

    Args:
        url: Full URL to fetch and analyze.
        same_domain_only: If true, only return links on the same domain (default).

    Returns:
        JSON with url, links (list of {href, text}), and optional error.
    """
    try:
        async with _make_client() as client:
            result = await list_links_async(url, same_domain_only, client)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.exception("list_links failed")
        return json.dumps({"url": url, "links": [], "error": str(e)})


@mcp.tool()
async def scrape_links_tool(
    url: str,
    same_domain_only: bool = True,
    max_pages: int = 20,
) -> str:
    """
    Crawl a page: list its links, then scrape each linked page in parallel.

    Combines list_links and scrape_url. Fetches the starting URL, discovers
    links, then scrapes all links concurrently (up to max_pages) for fast
    response times.

    Args:
        url: Starting URL.
        same_domain_only: Only follow links on the same domain (default).
        max_pages: Maximum number of linked pages to scrape (default 20).

    Returns:
        JSON with base_url, pages (list of {url, title, text}), and errors.
    """
    try:
        result = await scrape_links_async(url, same_domain_only, max_pages)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.exception("scrape_links failed")
        return json.dumps({
            "base_url": url,
            "pages": [],
            "errors": [str(e)],
        })


@mcp.tool()
async def scrape_urls_tool(urls: list[str]) -> str:
    """
    Scrape multiple URLs in parallel.

    Use when you already have a list of URLs (e.g. from list_links) and want
    to fetch all content in one fast call. Processes all URLs concurrently.

    Args:
        urls: List of full URLs to scrape (e.g. ["https://a.com/1", "https://a.com/2"]).

    Returns:
        JSON with pages (list of {url, title, text}) and errors.
    """
    try:
        result = await scrape_urls_async(urls)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.exception("scrape_urls failed")
        return json.dumps({"pages": [], "errors": [str(e)]})


async def main() -> None:
    """Run the MCP server."""
    port = int(os.getenv("PORT", 8081))
    host = os.getenv("HOST", "0.0.0.0")

    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.log_level = "INFO"

    logger.info(
        f"Flocrawl MCP Server starting on http://{host}:{port}\n"
        "Streamable HTTP at / | Discovery at /.well-known/flocrawl-mcp"
    )

    await mcp.run_streamable_http_async()


if __name__ == "__main__":
    asyncio.run(main())
