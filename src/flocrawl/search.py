"""
Web search module for Flocrawl.

Uses DDGS metasearch (DuckDuckGo, Brave, Google, etc.) for resilient search.
No API keys required.
"""

import logging
import os
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Backends to try in order. Google and Yandex tend to be more reliable;
# DuckDuckGo and Brave often return "No results" or 429 when rate-limited.
_SEARCH_BACKENDS = ["google", "yandex", "duckduckgo", "yahoo", "mojeek", "brave", "wikipedia"]
_DEFAULT_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "20"))
_BACKEND_DELAY = float(os.getenv("SEARCH_BACKEND_DELAY", "1.0"))  # seconds between backend attempts
_RATE_LIMIT_DELAY = float(os.getenv("SEARCH_RATE_LIMIT_DELAY", "3.0"))  # extra delay after 429


def search_web(
    query: str,
    max_results: int = 10,
    region: str = "us-en",
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

    for i, backend in enumerate(_SEARCH_BACKENDS):
        # Add delay between attempts to reduce rate limiting (skip before first try)
        if i > 0:
            time.sleep(_BACKEND_DELAY)
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
            err_str = str(e).lower()
            # "No results found" is common from DuckDuckGo; log at debug to reduce noise
            if "no results found" in err_str:
                logger.debug("Search backend %r returned no results. Trying next.", backend)
            # 429 rate limit: add extra delay before next backend
            elif "429" in err_str or "too many requests" in err_str or "ratelimit" in err_str:
                logger.debug(
                    "Search backend %r rate-limited. Waiting %.1fs before next.",
                    backend, _RATE_LIMIT_DELAY,
                )
                time.sleep(_RATE_LIMIT_DELAY)
            else:
                logger.warning("Search backend %r failed: %r. Trying next.", backend, e)
            continue

    if last_error:
        logger.warning("All search backends failed. Last error: %s", last_error)

    return []
