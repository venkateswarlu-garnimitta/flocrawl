"""
Web search module for Flocrawl.

Uses ddgs for search.
Also includes robust HTML fallbacks for DuckDuckGo and Google.
No API keys required.
"""

import logging
import random
import time
from typing import Any, Dict, List
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Modern browser headers
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

def get_headers() -> Dict[str, str]:
    """Get randomized browser-like headers."""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


def search_web(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
) -> List[Dict[str, Any]]:
    """
    Execute web search and return structured results.

    Tries multiple search strategies in order:
    1. ddgs library (fastest)
    2. DuckDuckGo HTML scrape fallback
    3. Google HTML scrape fallback

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        region: Region/locale for search.

    Returns:
        List of dicts with keys: title, url, snippet.
    """
    # Strategy 1: ddgs library
    try:
        results = _search_ddgs(query, max_results, region)
        if results:
            logger.info("ddgs library returned %d results", len(results))
            return results
    except Exception as e:
        logger.warning("ddgs library search failed: %s", e)

    # Strategy 2: DDG HTML fallback
    logger.info("Trying DDG HTML fallback for: %s", query[:50])
    try:
        results = _search_ddg_html(query, max_results)
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


def _search_ddgs(
    query: str,
    max_results: int,
    region: str,
) -> List[Dict[str, Any]]:
    """Search using ddgs library."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError as e:
            raise ImportError(
                "ddgs is required for web search. Install with: pip install ddgs"
            ) from e

    results: List[Dict[str, Any]] = []
    # ddgs v9+ doesn't take headers in constructor
    with DDGS() as ddgs:
        # If region is specific like in-en, but fails, we gracefully try wt-wt
        regions_to_try = [region] if region == "wt-wt" else [region, "wt-wt"]
        
        for r_code in regions_to_try:
            try:
                for r in ddgs.text(query, region=r_code, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", r.get("url", "")),
                        "snippet": r.get("body", r.get("snippet", "")),
                    })
                    if len(results) >= max_results:
                        break
                if results:
                    break
            except Exception as e:
                logger.debug("DDGS failed for region %s: %s", r_code, e)
                continue

    return results


def _search_ddg_html(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Scrape DuckDuckGo HTML interface."""
    results: List[Dict[str, Any]] = []
    url = "https://html.duckduckgo.com/html/"
    
    headers = get_headers()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    
    with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
        resp = client.post(url, data={"q": query, "b": "", "kl": "wt-wt"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

    for result in soup.select("div.web-result, div.result"):
        link = result.select_one("h2 a, .result__a")
        snippet_el = result.select_one(".result__snippet, a.result__snippet")
        
        if not link:
            continue
            
        href = link.get("href") or ""
        if "uddg=" in href:
            parsed = urlparse(href if href.startswith("http") else "https:" + href)
            href = unquote(parse_qs(parsed.query).get("uddg", [""])[0])
            
        if not href.startswith("http"):
            continue
            
        results.append({
            "title": link.get_text(strip=True),
            "url": href,
            "snippet": snippet_el.get_text(strip=True) if snippet_el else ""
        })
        
        if len(results) >= max_results:
            break
            
    return results


def _search_google_html(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Robust Google scraping fallback."""
    results: List[Dict[str, Any]] = []
    params = urlencode({"q": query, "num": max_results + 5, "hl": "en"})
    url = f"https://www.google.com/search?{params}"

    headers = get_headers()
    headers["Referer"] = "https://www.google.com/"

    with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

    # Modern Google search selectors
    for g in soup.select("div.g, div[data-hveid]"):
        title_el = g.select_one("h3")
        link_el = g.select_one("a[href]")
        snippet_el = g.select_one("div[data-sncf], .VwiC3b, .yXK7lf, .st")
        
        if not title_el or not link_el:
            continue
            
        href = link_el.get("href", "")
        if href.startswith("/url?"):
            href = parse_qs(urlparse(href).query).get("q", [""])[0]
            
        if not href.startswith("http"):
            continue
            
        results.append({
            "title": title_el.get_text(strip=True),
            "url": href,
            "snippet": snippet_el.get_text(strip=True) if snippet_el else ""
        })
        
        if len(results) >= max_results:
            break
            
    return results
