"""
Web scraping module for Flocrawl.

Fetches pages, extracts text, and discovers links using httpx + BeautifulSoup.
When a page requires JavaScript (e.g. Google Docs), optionally falls back to
a headless browser (Playwright) if installed.
"""

import logging
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from flocrawl.config import (
    get_browser_wait_after_load_ms,
    get_max_links_per_page,
    get_max_scrape_size,
    get_request_timeout,
    get_user_agent,
    get_use_browser_fallback,
)

logger = logging.getLogger(__name__)

# Lazy: Playwright only imported when browser fallback is used
_playwright_available: Optional[bool] = None


def _playwright_installed() -> bool:
    global _playwright_available
    if _playwright_available is None:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            _playwright_available = True
        except ImportError:
            _playwright_available = False
    return _playwright_available


# Phrases that indicate the server returned a "please enable JavaScript" page
_JS_REQUIRED_PHRASES = (
    "javascript is not enabled",
    "javascript is not supported",
    "enable javascript",
    "please enable javascript",
    "browser version is not supported",
    "browser is not supported",
    "turn on javascript",
    "you need to enable javascript",
)

# Domains that typically require JS for main content (try browser first or after minimal content)
_JS_HEAVY_DOMAINS = ("docs.google.com", "drive.google.com", "notion.so", "notion.site")


def _is_js_required_page(html: str, url: str, extracted_text: str) -> bool:
    """Return True if the response looks like a JS-required placeholder page."""
    lower = html.lower()
    if any(phrase in lower for phrase in _JS_REQUIRED_PHRASES):
        return True
    # Very little text from a known JS-heavy host
    if len(extracted_text.strip()) < 400 and any(d in url for d in _JS_HEAVY_DOMAINS):
        return True
    return False


def _try_google_docs_export(url: str) -> Optional[str]:
    """
    For Google Docs URLs, try the export endpoint first (no JS required).
    Returns plain text content or None if not a Google Doc or export fails.
    """
    import re
    # Match Google Docs URLs: docs.google.com/document/d/{ID}/...
    match = re.search(r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        return None

    doc_id = match.group(1)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=get_request_timeout(),
            headers={"User-Agent": get_user_agent()},
        ) as client:
            resp = client.get(export_url)
            resp.raise_for_status()
            content = resp.content
            if len(content) > get_max_scrape_size():
                content = content[:get_max_scrape_size()]
            # Try to decode as UTF-8, fallback to latin-1 for Google Docs
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="replace")

            # Google Docs export might return HTML error page if private/not accessible
            if len(text.strip()) < 50 and ("404" in text or "not found" in text.lower() or "access" in text.lower()):
                return None

            if text.strip():  # Only return if we got actual content
                logger.info("Retrieved Google Doc content via export URL.")
                return text
    except Exception as e:
        logger.debug("Google Docs export failed for %s: %s", url, e)

    return None


def _fetch_html_with_browser(url: str) -> Optional[str]:
    """
    Fetch URL with a headless browser (Playwright). Returns HTML or None on failure.
    Requires: pip install flocrawl[browser] && playwright install chromium
    """
    if not _playwright_installed():
        logger.debug("Playwright not installed; cannot use browser fallback.")
        return None
    if not get_use_browser_fallback():
        return None
    timeout_ms = int(get_request_timeout() * 1000)
    wait_ms = get_browser_wait_after_load_ms()

    # Use modern Chrome user agent for better compatibility
    chrome_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Launch with args to reduce automation detection
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )
            try:
                context = browser.new_context(
                    user_agent=chrome_ua,
                    viewport={"width": 1920, "height": 1080},
                    ignore_https_errors=True,
                    # Add more realistic browser context
                    locale="en-US",
                    timezone_id="America/New_York",
                )
                page = context.new_page()

                # Navigate and wait for content
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                # For Google Docs, wait longer and try to detect when content is loaded
                if "docs.google.com" in url:
                    # Wait for the document body to appear (Google Docs specific)
                    try:
                        page.wait_for_selector(".kix-appview-editor", timeout=10000)
                    except:
                        pass  # Continue even if selector not found
                    page.wait_for_timeout(max(wait_ms, 5000))  # At least 5s for Google Docs
                else:
                    page.wait_for_timeout(wait_ms)

                html = page.content()
                context.close()
                return html
            finally:
                browser.close()
    except Exception as e:
        logger.warning("Browser fetch failed for %s: %s", url, e)
        return None


def scrape_url(url: str) -> dict:
    """
    Fetch a URL and extract main text content.

    Args:
        url: Full URL to fetch.

    Returns:
        Dict with keys: url, title, text, error (if any).
    """
    # Special handling for Google Docs: try export URL first (no JS needed)
    export_text = _try_google_docs_export(url)
    if export_text:
        # For export URLs, we get plain text directly
        lines = [line.strip() for line in export_text.splitlines() if line.strip()]
        title = "Google Document"  # Default title for exported docs
        # Try to extract title from first line if it's a heading
        if lines and len(lines[0]) < 100:
            title = lines[0]
        text = "\n".join(lines)
        return {"url": url, "title": title, "text": text[:50000], "error": None}

    # Normal scraping flow
    headers = {"User-Agent": get_user_agent()}
    timeout = get_request_timeout()
    max_size = get_max_scrape_size()

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as client:
            resp = client.get(url)
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
        return {
            "url": url,
            "title": "",
            "text": "",
            "error": f"HTTP {e.response.status_code}",
        }
    except Exception as e:
        return {
            "url": url,
            "title": "",
            "text": "",
            "error": str(e),
        }

    try:
        soup, title, text = _parse_html_to_text(html)
        # If response looks like "enable JavaScript" (e.g. Google Docs), try browser
        if get_use_browser_fallback() and _is_js_required_page(html, url, text):
            browser_html = _fetch_html_with_browser(url)
            if browser_html:
                soup, title, text = _parse_html_to_text(browser_html)
                logger.info("Scraped %s using browser fallback (JS-rendered content).", url)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return {"url": url, "title": title, "text": text[:50000], "error": None}
    except Exception as e:
        return {"url": url, "title": "", "text": "", "error": str(e)}


def _parse_html_to_text(html: str) -> Tuple[BeautifulSoup, str, str]:
    """Parse HTML with BeautifulSoup; return soup, title, and main text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "aside"]):
        tag.decompose()
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    main = soup.find("main") or soup.find("article") or soup.find("body")
    text = main.get_text(separator="\n", strip=True) if main else ""
    if not text:
        text = soup.get_text(separator="\n", strip=True)
    return soup, title, text


def list_links(url: str, same_domain_only: bool = True) -> dict:
    """
    Fetch a URL and list all links found on the page.

    Args:
        url: Full URL to fetch.
        same_domain_only: If True, only return links on the same domain.

    Returns:
        Dict with keys: url, links (list of {href, text}), error (if any).
    """
    headers = {"User-Agent": get_user_agent()}
    timeout = get_request_timeout()
    max_links = get_max_links_per_page()

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as client:
            resp = client.get(url)
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
        # If page looks like "enable JavaScript" (e.g. Google Docs), try browser
        if get_use_browser_fallback():
            placeholder_text = soup.get_text(separator=" ", strip=True)[:500]
            if _is_js_required_page(html, url, placeholder_text):
                browser_html = _fetch_html_with_browser(url)
                if browser_html:
                    soup = BeautifulSoup(browser_html, "html.parser")
                    logger.info("Listed links for %s using browser fallback.", url)

        base_domain = urlparse(url).netloc
        seen = set()
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


def scrape_links(
    url: str,
    same_domain_only: bool = True,
    max_pages: Optional[int] = None,
) -> dict:
    """
    List links on a page, then scrape each link (recursive crawl).

    Args:
        url: Starting URL.
        same_domain_only: Only follow links on the same domain.
        max_pages: Maximum number of pages to scrape (default from config).

    Returns:
        Dict with keys: base_url, pages (list of {url, title, text}), errors.
    """
    from flocrawl.config import get_max_pages_to_scrape

    limit = max_pages if max_pages is not None else get_max_pages_to_scrape()
    link_result = list_links(url, same_domain_only=same_domain_only)
    if link_result.get("error"):
        return {
            "base_url": url,
            "pages": [],
            "errors": [link_result["error"]],
        }

    links = link_result["links"][:limit]
    pages: List[dict] = []
    errors: List[str] = []

    for item in links:
        href = item["href"]
        scraped = scrape_url(href)
        if scraped.get("error"):
            errors.append(f"{href}: {scraped['error']}")
        else:
            pages.append({
                "url": scraped["url"],
                "title": scraped["title"],
                "text": scraped["text"],
            })

    return {
        "base_url": url,
        "pages": pages,
        "errors": errors if errors else [],
    }
