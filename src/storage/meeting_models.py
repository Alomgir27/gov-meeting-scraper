"""
Pydantic models for meeting metadata including input validation and output serialization.

Data Models:
- MeetingMetadata: Single meeting with date, title, and URLs (agenda, minutes, video)
- MeetingInput: Request parameters (date range, base URLs)
- MeetingOutput: Response container (base_url, list of meetings)
- URLResolutionInput: URL resolution request (url, type)
- URLResolutionOutput: Resolution result (original, resolved, success, error)
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re
from dateutil import parser as date_parser


class MeetingMetadata(BaseModel):
    """Individual meeting metadata."""
    meeting_url: Optional[str] = None
    agenda_url: Optional[str] = None
    minutes_url: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            return v
        
        try:
            from ..extractors.date_parser import parse_flexible_date
            parsed_date = parse_flexible_date(v)
            if parsed_date:
                return parsed_date.strftime('%Y-%m-%d')
        except:
            pass
        
        return v
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MeetingInput(BaseModel):
    """Input for meeting scraping request."""
    start_date: str
    end_date: str
    base_urls: List[str]
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")


class MeetingOutput(BaseModel):
    """Output for meeting scraping request."""
    base_url: str
    medias: List[MeetingMetadata] = Field(default_factory=list)


class URLResolutionInput(BaseModel):
    """Input for URL resolution request."""
    url: str
    type: str


class URLResolutionOutput(BaseModel):
    """Output for URL resolution."""
    original_url: str
    resolved_url: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None

