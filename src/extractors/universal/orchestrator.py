"""
Universal extraction orchestrator coordinating multi-strategy meeting detection across diverse page structures.

Extraction Strategies:
1. detect_page_type: Identify structure (table/calendar/list/paragraph/container)
2. Table extraction: Parse tabular meeting data
3. Calendar extraction: Extract from year/month hierarchies
4. Paragraph extraction: Split dense paragraphs into meetings
5. Container extraction: Generic DOM container detection
6. Deduplication: Remove duplicate meetings by date + URLs
"""
from typing import List
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ...utils.logger import setup_logger
from ...utils.text_cleaner import clean_title
from ...utils.patterns import COMPILED_PATTERNS
from ..date_parser import is_date_in_range
from ..link_enhancer import extract_all_links
from ..validators import validate_meeting_data, deduplicate_meetings
from ..page_detector import detect_page_type
from .container_detector import looks_like_meeting_container, find_meeting_containers
from .date_extractor import extract_date_universal
from .text_extractor import extract_title, split_paragraph_meetings
from .table_extractor import extract_table_meetings
from .calendar_extractor import extract_calendar_style_meetings


logger = setup_logger("universal_extractor")


def extract_universal_meetings(soup: BeautifulSoup, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
    """
    Universal meeting extraction with smart strategy selection.
    Detects page type first, then applies optimal strategies.
    """
    all_meetings = []
    
    page_type = detect_page_type(str(soup), base_url)
    logger.info(f"Detected page type: {page_type}")
    
    if page_type == 'table':
        table_meetings = extract_table_meetings(soup, base_url, start_date, end_date)
        if table_meetings:
            logger.info(f"Table extraction: {len(table_meetings)} meetings")
            all_meetings.extend(table_meetings)
            deduplicated = deduplicate_meetings(all_meetings)
            logger.info(f"Total: {len(deduplicated)} unique meetings")
            return deduplicated
    
    if page_type == 'calendar':
        calendar_meetings = extract_calendar_style_meetings(soup, base_url, start_date, end_date)
        if calendar_meetings:
            logger.info(f"Calendar extraction: {len(calendar_meetings)} meetings")
            all_meetings.extend(calendar_meetings)
    
    if page_type == 'paragraph':
        main_content = soup.find('main') or soup.find('div', class_=COMPILED_PATTERNS['content_area']) or soup.body
        if main_content:
            paragraphs = main_content.find_all('p')
            containers = []
            for p in paragraphs:
                if looks_like_meeting_container(p):
                    split_containers = split_paragraph_meetings(p)
                    containers.extend(split_containers)
            
            logger.info(f"Paragraph extraction: {len(containers)} containers")
            for container in containers:
                date = extract_date_universal(container, soup)
                if not date or not is_date_in_range(date, start_date, end_date):
                    continue
                
                title = extract_title(container, date)
                title = clean_title(title) or f"Meeting on {date}"
                
                links = extract_all_links(container, base_url)
                
                if validate_meeting_data(date, title, links):
                    all_meetings.append(MeetingMetadata(
                        date=date,
                        title=title,
                        meeting_url=links.get('video'),
                        agenda_url=links.get('agenda'),
                        minutes_url=links.get('minutes')
                    ))
    
    container_meetings = []
    containers = find_meeting_containers(soup)
    logger.info(f"Container extraction: Found {len(containers)} potential containers")
    
    for container in containers:
        date = extract_date_universal(container, soup)
        if not date or not is_date_in_range(date, start_date, end_date):
            continue
        
        title = extract_title(container, date)
        title = clean_title(title) or f"Meeting on {date}"
        
        links = extract_all_links(container, base_url)
        
        if validate_meeting_data(date, title, links):
            container_meetings.append(MeetingMetadata(
                date=date,
                title=title,
                meeting_url=links.get('video'),
                agenda_url=links.get('agenda'),
                minutes_url=links.get('minutes')
            ))
    
    logger.info(f"Container extraction: {len(container_meetings)} meetings")
    all_meetings.extend(container_meetings)
    
    deduplicated = deduplicate_meetings(all_meetings)
    logger.info(f"Total: {len(deduplicated)} unique meetings")
    
    return deduplicated

