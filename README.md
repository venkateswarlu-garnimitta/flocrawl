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

## Tools

| Tool | Description |
|------|-------------|
| `search_web_tool` | Web search; returns titles, URLs, snippets |
| `scrape_url_tool` | Scrape a single URL; extract main text |
| `list_links_tool` | List all links on a page |
| `scrape_links_tool` | List links, then scrape each in parallel (crawl) |
| `scrape_urls_tool` | Scrape a list of URLs in parallel |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8081 | Server port |
| `HOST` | 0.0.0.0 | Bind address |
| `CRAWL_MAX_PAGE_SIZE` | 1048576 | Max bytes per page (1MB) |
| `CRAWL_MAX_LINKS_PER_PAGE` | 100 | Max links to extract per page |
| `CRAWL_MAX_PAGES` | 20 | Max pages for scrape_links |
| `CRAWL_MAX_CONCURRENT` | 10 | Max concurrent HTTP requests when scraping links in parallel |
| `CRAWL_REQUEST_TIMEOUT` | 30 | HTTP timeout (seconds) |
| `CRAWL_USER_AGENT` | Flocrawl/1.0 | User-Agent header |
| `SEARCH_TIMEOUT` | 15 | Search request timeout (seconds) |

## MCP Client Config

```json
{
  "transport": "HTTP_STREAMABLE",
  "url": "http://localhost:8081",
  "timeout": 60000,
  "sse_read_timeout": 60000
}
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
