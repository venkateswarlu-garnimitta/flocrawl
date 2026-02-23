"""
Web scraping module for Flocrawl.

Async-only: fetches pages, extracts text, and discovers links using httpx
+ BeautifulSoup. Parallel link scraping via asyncio for low latency.
"""

import asyncio
import logging
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from flocrawl.config import (
    get_max_concurrent_requests,
    get_max_links_per_page,
    get_max_pages_to_scrape,
    get_max_scrape_size,
    get_request_timeout,
    get_user_agent,
)

logger = logging.getLogger(__name__)


def _extract_text_from_html(html: str, url: str, max_text: int = 50000) -> dict:
    """Parse HTML and extract title + main text. Returns dict for scrape result."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        main = soup.find("main") or soup.find("article") or soup.find("body")
        text = main.get_text(separator="\n", strip=True) if main else ""
        if not text:
            text = soup.get_text(separator="\n", strip=True)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return {"url": url, "title": title, "text": text[:max_text], "error": None}
    except Exception as e:
        return {"url": url, "title": "", "text": "", "error": str(e)}


async def scrape_url_async(url: str, client: httpx.AsyncClient) -> dict:
    """
    Async: fetch a URL and extract main text content.
    Uses shared client for connection pooling; intended for parallel use.
    """
    max_size = get_max_scrape_size()
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content
        if len(content) > max_size:
            content = content[:max_size]
        encoding = resp.charset_encoding or "utf-8"
        try:
            html = content.decode(encoding, errors="replace")
        except Exception:
            html = content.decode("utf-8", errors="replace")
    except httpx.HTTPStatusError as e:
        return {"url": url, "title": "", "text": "", "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"url": url, "title": "", "text": "", "error": str(e)}
    return _extract_text_from_html(html, url)


async def list_links_async(
    url: str, same_domain_only: bool, client: httpx.AsyncClient
) -> dict:
    """Async: fetch URL and list all links on the page."""
    max_links = get_max_links_per_page()
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content
        encoding = resp.charset_encoding or "utf-8"
        try:
            html = content.decode(encoding, errors="replace")
        except Exception:
            html = content.decode("utf-8", errors="replace")
    except httpx.HTTPStatusError as e:
        return {"url": url, "links": [], "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"url": url, "links": [], "error": str(e)}

    try:
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(url).netloc
        seen: set[str] = set()
        links: List[dict] = []
        for a in soup.find_all("a", href=True):
            if len(links) >= max_links:
                break
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            abs_url = urljoin(url, href)
            parsed = urlparse(abs_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if same_domain_only and parsed.netloc != base_domain:
                continue
            if abs_url in seen:
                continue
            seen.add(abs_url)
            text = a.get_text(strip=True) or abs_url
            links.append({"href": abs_url, "text": text[:200]})
        return {"url": url, "links": links, "error": None}
    except Exception as e:
        return {"url": url, "links": [], "error": str(e)}


async def scrape_links_async(
    url: str,
    same_domain_only: bool = True,
    max_pages: Optional[int] = None,
) -> dict:
    """
    Async: list links on a page, then scrape all links in parallel.

    Uses asyncio.gather with a semaphore to limit concurrency. Returns as soon
    as all scrapes complete for minimal response latency.
    """
    limit = max_pages if max_pages is not None else get_max_pages_to_scrape()
    concurrency = get_max_concurrent_requests()
    headers = {"User-Agent": get_user_agent()}
    timeout = get_request_timeout()
    sem = asyncio.Semaphore(concurrency)

    async def scrape_one(href: str, client: httpx.AsyncClient) -> dict:
        async with sem:
            return await scrape_url_async(href, client)

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=timeout, headers=headers
    ) as client:
        link_result = await list_links_async(url, same_domain_only, client)
        if link_result.get("error"):
            return {
                "base_url": url,
                "pages": [],
                "errors": [link_result["error"]],
            }

        to_scrape = [item["href"] for item in link_result["links"][:limit]]
        if not to_scrape:
            return {"base_url": url, "pages": [], "errors": []}

        results = await asyncio.gather(
            *[scrape_one(href, client) for href in to_scrape],
            return_exceptions=True,
        )

    pages: List[dict] = []
    errors: List[str] = []
    for href, result in zip(to_scrape, results):
        if isinstance(result, Exception):
            errors.append(f"{href}: {result}")
            continue
        if result.get("error"):
            errors.append(f"{href}: {result['error']}")
        else:
            pages.append({
                "url": result["url"],
                "title": result["title"],
                "text": result["text"],
            })
    return {"base_url": url, "pages": pages, "errors": errors}


async def scrape_urls_async(urls: List[str]) -> dict:
    """
    Async: scrape multiple URLs in parallel.

    Use when the agent already has a list of links (e.g. from list_links) and
    wants to fetch all content in one fast call.
    """
    if not urls:
        return {"pages": [], "errors": []}

    concurrency = get_max_concurrent_requests()
    headers = {"User-Agent": get_user_agent()}
    timeout = get_request_timeout()
    sem = asyncio.Semaphore(concurrency)

    async def scrape_one(u: str, client: httpx.AsyncClient) -> dict:
        async with sem:
            return await scrape_url_async(u, client)

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=timeout, headers=headers
    ) as client:
        results = await asyncio.gather(
            *[scrape_one(u, client) for u in urls],
            return_exceptions=True,
        )

    pages: List[dict] = []
    errors: List[str] = []
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            errors.append(f"{url}: {result}")
            continue
        if result.get("error"):
            errors.append(f"{url}: {result['error']}")
        else:
            pages.append({
                "url": result["url"],
                "title": result["title"],
                "text": result["text"],
            })
    return {"pages": pages, "errors": errors}
