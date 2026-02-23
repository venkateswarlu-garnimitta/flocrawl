"""
Web search module for Flocrawl.

Uses DuckDuckGo for search (DDGS library + HTML fallback).
Also includes a Google HTML fallback for maximum reliability.
No API keys required.
"""

import logging
import time
from typing import Any, Dict, List
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Browser-like headers to avoid bot detection
_SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://html.duckduckgo.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
}


def search_web(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
) -> List[Dict[str, Any]]:
    """
    Execute web search and return structured results.

    Tries multiple search strategies in order:
    1. DuckDuckGo via DDGS library (fastest)
    2. DuckDuckGo HTML scrape fallback
    3. Google HTML scrape fallback (most reliable)

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default 10).
        region: Region/locale for search (e.g. wt-wt, us-en, in-en).

    Returns:
        List of dicts with keys: title, url, snippet.
    """
    # Strategy 1: DDGS library
    try:
        results = _search_duckduckgo(query, max_results, region)
        if results:
            logger.info("DDGS library returned %d results", len(results))
            return results
    except Exception as e:
        logger.warning("DDGS library search failed: %s", e)

    # Strategy 2: DuckDuckGo HTML fallback
    logger.info("Trying DDG HTML fallback for: %s", query[:50])
    try:
        results = _search_duckduckgo_html(query, max_results)
        if results:
            logger.info("DDG HTML fallback returned %d results", len(results))
            return results
    except Exception as e:
        logger.warning("DDG HTML fallback failed: %s", e)

    # Strategy 3: Google HTML fallback
    logger.info("Trying Google HTML fallback for: %s", query[:50])
    try:
        results = _search_google_html(query, max_results)
        if results:
            logger.info("Google HTML fallback returned %d results", len(results))
            return results
    except Exception as e:
        logger.warning("Google HTML fallback failed: %s", e)

    logger.error("All search strategies failed for query: %s", query[:50])
    return []


def _search_duckduckgo(
    query: str,
    max_results: int,
    region: str,
) -> List[Dict[str, Any]]:
    """Search using duckduckgo-search library with browser headers."""
    try:
        from duckduckgo_search import DDGS
    except ImportError as e:
        raise ImportError(
            "duckduckgo-search is required for web search. "
            "Install with: pip install duckduckgo-search"
        ) from e

    results: List[Dict[str, Any]] = []
    for attempt in range(2):
        try:
            text_kw: dict = {
                "keywords": query,
                "region": region,
                "safesearch": "moderate",
                "max_results": max_results,
            }
            # Try with headers and html backend first
            try:
                with DDGS(headers=_SEARCH_HEADERS, timeout=15) as ddgs:
                    text_kw["backend"] = "html"
                    for r in ddgs.text(**text_kw):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", r.get("url", "")),
                            "snippet": r.get("body", r.get("snippet", "")),
                        })
                        if len(results) >= max_results:
                            break
            except TypeError:
                # Older DDGS version may not support 'backend' or 'headers' kwargs
                text_kw.pop("backend", None)
                with DDGS(timeout=15) as ddgs:
                    for r in ddgs.text(**text_kw):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", r.get("url", "")),
                            "snippet": r.get("body", r.get("snippet", "")),
                        })
                        if len(results) >= max_results:
                            break

            if results:
                return results
        except Exception as e:
            logger.warning("DDGS attempt %d failed: %s", attempt + 1, e)
            if attempt < 1:
                time.sleep(1)

    return results


def _extract_ddg_url(href: str) -> str:
    """Extract real URL from DuckDuckGo redirect (//duckduckgo.com/l/?uddg=...)."""
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if "uddg=" in href:
        parsed = urlparse(href if href.startswith("http") else "https:" + href)
        params = parse_qs(parsed.query)
        uddg = params.get("uddg", [""])[0]
        return unquote(uddg) if uddg else href
    return href


def _search_duckduckgo_html(query: str, max_results: int) -> List[Dict[str, Any]]:
    """
    Fallback: scrape DuckDuckGo HTML interface directly.
    Works when DDGS library returns empty (e.g. from datacenter IPs).
    """
    results: List[Dict[str, Any]] = []
    url = "https://html.duckduckgo.com/html/"

    with httpx.Client(
        follow_redirects=True,
        timeout=20,
        headers=_SEARCH_HEADERS,
    ) as client:
        resp = client.post(
            url,
            data={"q": query[:500], "b": "", "kl": "wt-wt"},
            headers={**_SEARCH_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

    for result in soup.select("div.web-result, div.result")[:max_results + 5]:
        link = result.select_one("h2 a, .result__a")
        snippet_el = result.select_one(".result__snippet, a.result__snippet")
        if not link:
            continue
        href = link.get("href") or ""
        real_url = _extract_ddg_url(href)
        if real_url and (real_url.startswith("http://") or real_url.startswith("https://")):
            title = link.get_text(strip=True) or ""
            snippet = (snippet_el.get_text(strip=True) if snippet_el else "") or ""
            results.append({"title": title, "url": real_url, "snippet": snippet})
            if len(results) >= max_results:
                break

    return results


def _search_google_html(query: str, max_results: int) -> List[Dict[str, Any]]:
    """
    Last-resort fallback: scrape Google search HTML results.
    Uses browser headers to mimic a real browser request.
    No API key required.
    """
    results: List[Dict[str, Any]] = []
    params = urlencode({"q": query, "num": min(max_results + 3, 20), "hl": "en"})
    url = f"https://www.google.com/search?{params}"

    google_headers = {
        **_SEARCH_HEADERS,
        "Referer": "https://www.google.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }

    with httpx.Client(
        follow_redirects=True,
        timeout=20,
        headers=google_headers,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

    # Google search result containers: div#search > div > div with a h3 title
    for g in soup.select("div.g, div[data-hveid]"):
        title_el = g.select_one("h3")
        link_el = g.select_one("a[href]")
        snippet_el = g.select_one(
            "div[data-sncf], div.VwiC3b, span.aCOpRe, div[style*='-webkit-line-clamp']"
        )
        if not title_el or not link_el:
            continue
        href = link_el.get("href", "")
        # Google wraps results in /url?q=... — extract real URL
        if href.startswith("/url?"):
            parsed = urlparse("https://www.google.com" + href)
            qs = parse_qs(parsed.query)
            href = qs.get("q", [href])[0]
        if not (href.startswith("http://") or href.startswith("https://")):
            continue
        title = title_el.get_text(strip=True)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break

    return results
