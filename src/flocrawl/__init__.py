"""
Flocrawl MCP Server.

MCP tools for web search, scraping, link discovery, and recursive crawling.
"""

from flocrawl.agent_instructions import AGENT_SYSTEM_PROMPT, get_agent_system_prompt

__all__ = [
    "__version__",
    "AGENT_SYSTEM_PROMPT",
    "get_agent_system_prompt",
]

__version__ = "1.0.0"
