"""Meeting metadata extractor."""
from typing import List
from bs4 import BeautifulSoup

from ..storage.meeting_models import MeetingMetadata
from ..utils.logger import setup_logger
from .date_parser import is_date_in_range
from .site_registry import get_extractor


class MeetingExtractor:
    
    def __init__(self):
        self.logger = setup_logger("meeting_extractor")
    
    def extract_meetings(self, html: str, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
        soup = BeautifulSoup(html, 'lxml')
        
        extractor = get_extractor(base_url)
        if not extractor:
            self.logger.warning(f"No extractor found for {base_url}")
            return []
        
        self.logger.info(f"Using extractor for {base_url}")
        meetings = extractor(soup, base_url)
        
        filtered = [
            m for m in meetings
            if m.date and is_date_in_range(m.date, start_date, end_date)
        ]
        
        self.logger.info(f"Extracted {len(filtered)} meetings from {base_url}")
        return filtered
