from pydantic import BaseModel


class ScraperConfig(BaseModel):
    domain: str
    rate_limit: int = 2
    timeout: float = 60.0
    storage_format: str = "json"

