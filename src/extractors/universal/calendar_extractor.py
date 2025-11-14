"""
Calendar-style meeting extractor for year/month hierarchical page structures.

Extraction Process:
- Locate year headings (h1, h2, h3) with 4-digit years
- Find month sections under each year
- Extract meeting containers within month sections
- Parse dates, titles, and links from containers
"""
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ...utils.logger import setup_logger
from ...utils.text_cleaner import clean_title
from ...utils.patterns import COMPILED_PATTERNS
from ..date_parser import is_date_in_range
from ..link_classifier import extract_and_classify_links
from ..validators import validate_meeting_data
from .date_extractor import extract_date_from_text
from .link_utils import is_video_link


logger = setup_logger("calendar_extractor")


def extract_calendar_style_meetings(soup: BeautifulSoup, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
    meetings = []
    year_headings = soup.find_all(['h1', 'h2', 'h3'], string=COMPILED_PATTERNS['year_strict'])
    
    logger.info(f"Calendar style: Found {len(year_headings)} year headings")
    
    for year_heading in year_headings:
        year_match = COMPILED_PATTERNS['year_simple'].search(year_heading.get_text(strip=True))
        if not year_match:
            continue
        
        year = int(year_match.group(1))
        current_month = None
        
        for elem in year_heading.find_all_next():
            if elem.name in ['h1', 'h2'] and COMPILED_PATTERNS['year_boundary'].search(elem.get_text(strip=True)):
                break
            
            elem_text = elem.get_text(strip=True)
            month_match = COMPILED_PATTERNS['month_full'].match(elem_text)
            
            if month_match:
                current_month = month_match.group(1)
                continue
            
            if not current_month:
                continue
            
            links = elem.find_all('a', href=True)
            for link in links:
                link_text = link.get_text(strip=True)
                date_str = extract_date_from_text(link_text, year)
                
                if not date_str or not is_date_in_range(date_str, start_date, end_date):
                    continue
                
                href = urljoin(base_url, link.get('href'))
                video_url = href if is_video_link(link) else None
                
                nearby_links = []
                parent = link.parent
                if parent:
                    nearby_links = parent.find_all('a', href=True)
                
                all_links = extract_and_classify_links(parent or elem, base_url)
                if video_url and not all_links.get('video'):
                    all_links['video'] = video_url
                
                title = f"{current_month} {date_str.split('-')[2]}, {year} - Board Meeting"
                title = clean_title(title) or f"Meeting on {date_str}"
                
                if validate_meeting_data(date_str, title, all_links):
                    meetings.append(MeetingMetadata(
                        date=date_str,
                        title=title,
                        meeting_url=all_links.get('video'),
                        agenda_url=all_links.get('agenda'),
                        minutes_url=all_links.get('minutes')
                    ))
    
    logger.info(f"Calendar style: Extracted {len(meetings)} meetings")
    return meetings

