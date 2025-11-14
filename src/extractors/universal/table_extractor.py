"""
Table-based meeting extractor parsing tabular meeting data structures.

Table Processing:
- Detect header row for column identification
- Map columns to data types (date, title, agenda, minutes, video)
- Extract data from each row with proper column alignment
- Handle colspan and complex table structures
- Validate extracted data before adding to results
"""
from typing import List
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ...utils.logger import setup_logger
from ...utils.text_cleaner import clean_title
from ...utils.patterns import CANCELLED_KEYWORDS, COMPILED_PATTERNS
from ..date_parser import is_date_in_range
from ..link_classifier import extract_and_classify_links
from ..validators import validate_meeting_data
from .date_extractor import extract_date_from_text
from .text_extractor import extract_title


logger = setup_logger("table_extractor")


def extract_table_meetings(soup: BeautifulSoup, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
    meetings = []
    
    from datetime import datetime
    start_year = int(start_date.split('-')[0])
    end_year = int(end_date.split('-')[0])
    
    page_year = None
    for select in soup.find_all('select'):
        selected = select.find('option', selected=True)
        if selected:
            year_match = COMPILED_PATTERNS['year'].search(selected.get_text(strip=True))
            if year_match:
                page_year = int(year_match.group(1))
                break
    
    if not page_year:
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            year_match = COMPILED_PATTERNS['year'].search(heading.get_text(strip=True))
            if year_match:
                page_year = int(year_match.group(1))
                break
    
    if not page_year or page_year not in range(start_year, end_year + 1):
        page_year = start_year
    
    logger.info(f"Table extraction: Using year {page_year} (range: {start_year}-{end_year})")
    
    for row in soup.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) < 1:
            continue
        
        date_found = None
        date_cell = None
        date_cell_idx = None
        
        for idx, cell in enumerate(cells):
            cell_text = cell.get_text(' ', strip=True)
            date_str = extract_date_from_text(cell_text, page_year)
            if date_str:
                date_found = date_str
                date_cell = cell
                date_cell_idx = idx
                break
        
        if not date_found or not is_date_in_range(date_found, start_date, end_date):
            continue
        
        row_text = row.get_text(' ', strip=True).lower()
        if any(kw in row_text for kw in CANCELLED_KEYWORDS):
            continue
        
        links = {'agenda': None, 'minutes': None, 'video': None}
        
        if date_cell:
            cell_links = extract_and_classify_links(date_cell, base_url)
            if any(cell_links.values()):
                links.update({k: v for k, v in cell_links.items() if v})
                logger.debug(f"Found links in date cell: {cell_links}")
        
        row_links = extract_and_classify_links(row, base_url)
        for link_type, url in row_links.items():
            if url and not links.get(link_type):
                links[link_type] = url
        
        for cell in cells:
            cell_links = extract_and_classify_links(cell, base_url)
            for link_type, url in cell_links.items():
                if url and not links.get(link_type):
                    links[link_type] = url
        
        title = extract_title(row, date_found)
        title = clean_title(title) or f"Meeting on {date_found}"
        
        if validate_meeting_data(date_found, title, links):
            meetings.append(MeetingMetadata(
                date=date_found,
                title=title,
                meeting_url=links.get('video'),
                agenda_url=links.get('agenda'),
                minutes_url=links.get('minutes')
            ))
    
    logger.info(f"Table extraction: Extracted {len(meetings)} meetings")
    return meetings

