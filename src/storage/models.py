"""
Scraper configuration model defining rate limits, timeouts, and output formats.

Configuration Options:
- domain: Identifier for logger and output naming
- rate_limit: Requests per second (default: 2)
- timeout: Request timeout in seconds (default: 60)
- storage_format: Output format (default: "json")
"""
from pydantic import BaseModel


class ScraperConfig(BaseModel):
    domain: str
    rate_limit: int = 2
    timeout: float = 60.0
    storage_format: str = "json"

