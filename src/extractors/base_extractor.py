"""Meeting metadata extractor."""
from typing import List
from bs4 import BeautifulSoup

from ..storage.meeting_models import MeetingMetadata
from ..utils.logger import setup_logger
from .date_parser import is_date_in_range
from .site_registry import get_extractor
from .universal import extract_universal_meetings


class MeetingExtractor:
    
    def __init__(self, use_universal_only: bool = False):
        self.logger = setup_logger("meeting_extractor")
        self.use_universal_only = use_universal_only
    
    def extract_meetings(self, html: str, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
        soup = BeautifulSoup(html, 'lxml')
        
        if self.use_universal_only:
            self.logger.info(f"Using UNIVERSAL extractor only for {base_url}")
            meetings = extract_universal_meetings(soup, base_url, start_date, end_date)
            self.logger.info(f"Extracted {len(meetings)} meetings from {base_url}")
            return meetings
        
        extractor = get_extractor(base_url)
        
        if extractor:
            self.logger.info(f"Using site-specific extractor for {base_url}")
            meetings = extractor(soup, base_url)
            
            filtered = [
                m for m in meetings
                if m.date and is_date_in_range(m.date, start_date, end_date)
            ]
            
            self.logger.info(f"Extracted {len(filtered)} meetings from {base_url}")
            return filtered
        
        self.logger.info(f"Using universal extractor (fallback) for {base_url}")
        meetings = extract_universal_meetings(soup, base_url, start_date, end_date)
        
        self.logger.info(f"Extracted {len(meetings)} meetings from {base_url}")
        return meetings

