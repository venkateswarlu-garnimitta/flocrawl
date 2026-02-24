"""
Web search module for Flocrawl.

Uses DDGS metasearch (Bing, DuckDuckGo, Brave, etc.) for resilient search.
No API keys required.
"""

import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Backends to try in order. Bing is disabled in recent ddgs; use only available ones:
# brave, duckduckgo, google, grokipedia, mojeek, wikipedia, yahoo, yandex
# grokipedia often has connection errors; prefer duckduckgo, brave, google
_SEARCH_BACKENDS = ["duckduckgo", "brave", "google", "duckduckgo,brave", "yandex", "yahoo", "mojeek", "wikipedia"]
_DEFAULT_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))


def search_web(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
) -> List[Dict[str, Any]]:
    """
    Execute web search and return structured results.

    Uses DDGS metasearch (multiple backends). No API key required.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default 10).
        region: Region/locale (e.g. wt-wt, us-en).

    Returns:
        List of dicts with keys: title, url, snippet.
    """
    return _search_ddgs(query, max_results, region)


def _search_ddgs(
    query: str,
    max_results: int,
    region: str,
) -> List[Dict[str, Any]]:
    """Search using DDGS metasearch (DuckDuckGo, Brave, Google, etc.)."""
    # Suppress noisy ddgs/primp warnings (KeyError, impersonate, engine errors)
    for _logger in ("ddgs.ddgs", "primp.impersonate", "primp"):
        logging.getLogger(_logger).setLevel(logging.ERROR)
    try:
        from ddgs import DDGS
    except ImportError as e:
        raise ImportError(
            "ddgs is required for web search. "
            "Install with: pip install ddgs"
        ) from e

    results: List[Dict[str, Any]] = []
    last_error: Exception | None = None

    for backend in _SEARCH_BACKENDS:
        try:
            ddgs = DDGS(proxy=os.environ.get("DDGS_PROXY"), timeout=_DEFAULT_TIMEOUT)
            raw = ddgs.text(
                query,
                region=region,
                safesearch="moderate",
                max_results=max_results,
                backend=backend,
            )
            for r in raw:
                url = r.get("href") or r.get("url") or ""
                snippet = r.get("body") or r.get("snippet") or ""
                title = r.get("title") or ""
                if url or title or snippet:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    })
            if results:
                return results[:max_results]
        except Exception as e:
            last_error = e
            logger.warning("Search backend %r failed: %r. Trying next.", backend, e)
            continue

    if last_error:
        logger.exception("All search backends failed: %s", last_error)

    return []
