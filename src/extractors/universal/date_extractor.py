"""Universal date extraction utilities."""
import re
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from ...utils.patterns import (
    DATE_PATTERNS_WITH_YEAR,
    DATE_PATTERNS_WITHOUT_YEAR,
    COMPILED_PATTERNS
)
from .year_extractor import find_context_year


def extract_date_universal(elem: Tag, soup: BeautifulSoup) -> Optional[str]:
    for attr in ['data-date', 'data-meeting-date', 'datetime']:
        if elem.get(attr):
            try:
                dt = date_parser.parse(elem.get(attr))
                return dt.strftime('%Y-%m-%d')
            except:
                pass
    
    time_tag = elem.find('time')
    if time_tag and time_tag.get('datetime'):
        try:
            dt = date_parser.parse(time_tag.get('datetime'))
            return dt.strftime('%Y-%m-%d')
        except:
            pass
    
    text = elem.get_text(' ', strip=True)
    
    for pattern in DATE_PATTERNS_WITH_YEAR:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                dt = date_parser.parse(match.group())
                return dt.strftime('%Y-%m-%d')
            except:
                continue
    
    context_year = find_context_year(elem, soup)
    if context_year:
        for pattern in DATE_PATTERNS_WITHOUT_YEAR:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str_only = match.group()
                    date_str_only = re.sub(r'[*\-].*$', '', date_str_only).strip()
                    date_str_with_year = f"{date_str_only} {context_year}"
                    dt = date_parser.parse(date_str_with_year)
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
    
    return None


def extract_date_from_text(text: str, context_year: Optional[int] = None) -> Optional[str]:
    date_patterns = [
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%m-%d-%Y'),
    ]
    
    for pattern, fmt in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                dt = datetime.strptime(match.group(), fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
    
    month_patterns = [
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})',
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})',
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})',
        r'(\d{1,2})-(\d{1,2})-(\d{2,4})',
    ]
    
    for pattern in month_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                date_str = match.group()
                if context_year and not COMPILED_PATTERNS['year_in_string'].search(date_str):
                    date_str = f"{date_str}, {context_year}"
                
                dt = date_parser.parse(date_str)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
    
    return None

