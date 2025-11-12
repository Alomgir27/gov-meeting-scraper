"""Simple utilities for rate limiting and URL normalization."""
import asyncio
from urllib.parse import urlparse, urljoin


class RateLimiter:
    def __init__(self, rate: int = 2):
        self.rate = rate
        self.last_call = 0
        
    async def acquire(self):
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_call
        if time_since_last < (1.0 / self.rate):
            await asyncio.sleep((1.0 / self.rate) - time_since_last)
        self.last_call = asyncio.get_event_loop().time()


def normalize_url(url: str, base_url: str = None) -> str:
    if base_url and not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
    return url.strip()


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
