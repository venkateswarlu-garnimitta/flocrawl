---
title: Flocrawl MCP
emoji: 🔍
colorFrom: green
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Flocrawl is a web scraping MCP tool developed by Flotorch.
---

# Flocrawl MCP Server

MCP server for web search, scraping, link discovery, and recursive crawling.
No API keys required—search and scraping run without token-based services.

## Quick Start

```bash
cd flocrawl
pip install -e .
python -m flocrawl
```

Server runs at `http://0.0.0.0:8081` (or `PORT` from env, e.g. 7860 on Hugging Face).

### JavaScript-rendered pages (e.g. Google Docs)

Sites that require JavaScript (like Google Docs) return a “enable JavaScript” page when fetched with plain HTTP. To scrape them, install the optional browser backend and install Chromium:

```bash
pip install -e ".[browser]"
playwright install chromium
```

With this installed, the server will automatically use a headless browser when it detects a JS-required response, so Google Docs and similar pages can be scraped.

For Docker, add to your image: install `requirements-browser.txt` and run `playwright install chromium` (and install system deps for Chromium if using a slim image).

## Tools

| Tool | Description |
|------|-------------|
| `search_web_tool` | Web search; returns titles, URLs, snippets |
| `scrape_url_tool` | Scrape a single URL; extract main text |
| `list_links_tool` | List all links on a page |
| `scrape_links_tool` | List links, then scrape each (crawl) |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8081 | Server port |
| `HOST` | 0.0.0.0 | Bind address |
| `CRAWL_MAX_PAGE_SIZE` | 1048576 | Max bytes per page (1MB) |
| `CRAWL_MAX_LINKS_PER_PAGE` | 100 | Max links to extract per page |
| `CRAWL_MAX_PAGES` | 20 | Max pages for scrape_links |
| `CRAWL_REQUEST_TIMEOUT` | 30 | HTTP timeout (seconds) |
| `CRAWL_USER_AGENT` | Flocrawl/1.0 | User-Agent header |
| `CRAWL_USE_BROWSER_FALLBACK` | true | Use Playwright when page requires JavaScript (e.g. Google Docs) |
| `CRAWL_BROWSER_WAIT_MS` | 3000 | Ms to wait after load for JS-rendered content |
| `SEARCH_TIMEOUT` | 20 | Search request timeout (seconds) |
| `SEARCH_BACKEND_DELAY` | 1.0 | Delay between backend attempts (reduces rate limiting) |
| `SEARCH_RATE_LIMIT_DELAY` | 3.0 | Extra delay after 429 (seconds) |

## MCP Client Configuration

```json
{
  "transport": "HTTP_STREAMABLE",
  "url": "http://localhost:8081",
  "timeout": 60000,
  "sse_read_timeout": 60000
}
```

## API Usage Examples

### Web Search
```bash
# Search for information
curl -X POST "http://localhost:8081/tools/search_web_tool" \
  -H "Content-Type: application/json" \
  -d '{"query": "python web scraping", "max_results": 5}'
```

### Scrape a Single Page
```bash
curl -X POST "http://localhost:8081/tools/scrape_url_tool" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### List Links on a Page
```bash
curl -X POST "http://localhost:8081/tools/list_links_tool" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "same_domain_only": true}'
```

### Recursive Crawl
```bash
curl -X POST "http://localhost:8081/tools/scrape_links_tool" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_pages": 10}'
```

## Project Structure

```
flocrawl/
├── src/flocrawl/
│   ├── config.py    # Env and limits
│   ├── search.py    # Web search (DDGS metasearch: Bing, DuckDuckGo, etc.)
│   ├── scraper.py   # Scrape, list links, crawl
│   ├── server.py    # FastMCP server and tools
│   ├── __init__.py
│   └── __main__.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11+
- httpx, beautifulsoup4, ddgs, fastmcp
- Optional: `playwright` (install with `pip install flocrawl[browser]` and run `playwright install chromium`) for JavaScript-heavy sites like Google Docs

## License

MIT License
