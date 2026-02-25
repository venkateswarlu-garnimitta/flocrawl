---
title: Flocrawl MCP Server
emoji: 🌐
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
short_description: MCP server for web search, scraping & crawling. No API keys.
tags:
  - mcp
  - web-search
  - scraping
  - crawling
---

# Flocrawl MCP Server

MCP server for web search, scraping, link discovery, and recursive crawling. No API keys required.

## Quick Start

```bash
pip install -e .
python -m flocrawl
```

Server runs at `http://0.0.0.0:8081` (override with `PORT` and `HOST` environment variables).

### Optional: JavaScript-rendered content

For sites that require a browser to render content, install the optional backend:

```bash
pip install -e ".[browser]"
playwright install chromium
```

When installed, the server will use it automatically when needed. For Docker, add `requirements-browser.txt` and run `playwright install chromium` (and install Chromium system dependencies if using a slim base image).

## Tools

| Tool | Description |
|------|-------------|
| `search_web_tool` | Web search; returns titles, URLs, snippets |
| `scrape_url_tool` | Scrape a URL; extract main text |
| `list_links_tool` | List links on a page |
| `scrape_links_tool` | List links, then scrape each (crawl) |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8081 | Server port |
| `HOST` | 0.0.0.0 | Bind address |
| `CRAWL_MAX_PAGE_SIZE` | 1048576 | Max bytes per page (1MB) |
| `CRAWL_MAX_LINKS_PER_PAGE` | 100 | Max links per page |
| `CRAWL_MAX_PAGES` | 20 | Max pages for scrape_links |
| `CRAWL_REQUEST_TIMEOUT` | 30 | HTTP timeout (seconds) |
| `CRAWL_USER_AGENT` | Flocrawl/1.0 | User-Agent header |
| `CRAWL_USE_BROWSER_FALLBACK` | true | Use browser when response indicates JS-only content |
| `CRAWL_BROWSER_WAIT_MS` | 3000 | Wait after load for JS-rendered content (ms) |
| `SEARCH_TIMEOUT` | 20 | Search request timeout (seconds) |
| `SEARCH_BACKEND_DELAY` | 1.0 | Delay between search backend attempts |
| `SEARCH_RATE_LIMIT_DELAY` | 3.0 | Delay after rate limit (seconds) |

## MCP Client Configuration

```json
{
  "transport": "HTTP_STREAMABLE",
  "url": "http://localhost:8081/flocrawl/mcp",
  "timeout": 60000,
  "sse_read_timeout": 60000
}
```

### Hugging Face Hub MCP Settings

When adding flocrawl from [Hugging Face Hub MCP settings](https://huggingface.co/settings/mcp), use HTTP_STREAMABLE with your deployed URL. If the server is behind HF auth, add the optional Authorization header:

```json
{
  "transport": "HTTP_STREAMABLE",
  "url": "http://localhost:8081/flocrawl/mcp",
  "timeout": 60000,
  "sse_read_timeout": 60000,
  "headers": {
    "Authorization": "Bearer <YOUR_HF_TOKEN>"
  }
}
```

> A valid Hugging Face token with READ permissions is required when using MCP tools through Hub. Create one at [hf.co/settings/tokens](https://huggingface.co/settings/tokens).

### Gateway / reverse proxy (AWS, Kubernetes, etc.)

MCP endpoint: **`/flocrawl/mcp`**. Allow **POST** (required) and **GET** (optional, for discovery).

| Purpose | Path | Method |
|--------|------|--------|
| MCP protocol | `/flocrawl/mcp` | POST |
| Discovery | `/flocrawl/mcp` | GET |

Configure the gateway backend URL to the service root plus path, e.g. `http://<service>:<port>/flocrawl/mcp`, and allow POST (and optionally GET) on that path.

## Usage

Connect your MCP client to `http://<host>:<port>/flocrawl/mcp` using the HTTP_STREAMABLE transport. The server exposes the tools listed above over the MCP protocol.

## Project structure

```
flocrawl/
├── src/flocrawl/
│   ├── config.py
│   ├── search.py
│   ├── scraper.py
│   ├── server.py
│   ├── __init__.py
│   └── __main__.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11+
- Core: httpx, beautifulsoup4, ddgs, fastmcp
- Optional: `playwright` (install with `pip install flocrawl[browser]` and `playwright install chromium`) for JavaScript-rendered pages

## License

MIT License
