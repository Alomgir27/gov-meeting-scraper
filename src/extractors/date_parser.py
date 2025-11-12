"""Date parsing utilities for meeting metadata extraction."""
import re
from datetime import datetime, date
from typing import Optional
from dateutil import parser as date_parser


DATE_PATTERNS = [
    r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',
    r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{1,2}),?\s+(\d{4})\b',
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(\d{1,2}),?\s+(\d{4})\b',
    r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
]


def parse_flexible_date(date_str: str) -> Optional[date]:
    """Parse date string with multiple format support."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    common_formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m-%d-%Y', '%d-%m-%Y',
        '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y', '%Y.%m.%d', '%m.%d.%Y',
    ]
    
    for fmt in common_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    try:
        parsed = date_parser.parse(date_str, fuzzy=True)
        return parsed.date()
    except:
        pass
    
    return None


def extract_date_from_text(text: str) -> Optional[str]:
    """Extract date from text using regex patterns."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matched_text = match.group(0)
            parsed = parse_flexible_date(matched_text)
            if parsed:
                return parsed.strftime('%Y-%m-%d')
    
    return None


def is_date_in_range(date_str: Optional[str], start_date: str, end_date: str) -> bool:
    """Check if a date string falls within the specified range."""
    if not date_str:
        return False
    
    try:
        check_date = parse_flexible_date(date_str)
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if check_date:
            return start <= check_date <= end
    except:
        pass
    
    return False

