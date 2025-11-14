"""
Data validators ensuring meeting metadata quality and preventing false positives through strict validation.

Validation Rules:
- validate_url: Check proper http/https scheme and netloc
- validate_date: Enforce YYYY-MM-DD format
- validate_title: Enforce length constraints (5-300 chars)
- validate_meeting_data: Composite validation for complete records
- deduplicate_meetings: Remove duplicates by date + URL key
"""
from typing import Optional, Dict
from urllib.parse import urlparse
from ..utils.patterns import TITLE_MIN_LENGTH, TITLE_MAX_LENGTH, COMPILED_PATTERNS


def validate_url(url: Optional[str]) -> bool:
    if not url:
        return True
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False


def validate_date(date_str: Optional[str]) -> bool:
    if not date_str:
        return False
    return bool(COMPILED_PATTERNS['date_validation'].match(date_str))


def validate_title(title: Optional[str]) -> bool:
    if not title:
        return False
    title = title.strip()
    return TITLE_MIN_LENGTH <= len(title) <= TITLE_MAX_LENGTH


def validate_meeting_data(date: Optional[str], title: Optional[str], links: Dict[str, Optional[str]]) -> bool:
    if not validate_date(date):
        return False
    
    if not validate_title(title):
        return False
    
    for url in links.values():
        if url and not validate_url(url):
            return False
    
    return True


def deduplicate_meetings(meetings):
    """
    Deduplicate meetings using multiple criteria.
    Key: date + all URLs (to allow multiple meetings per day with different content)
    """
    seen = {}
    
    for meeting in meetings:
        # Create key from date + all non-null URLs
        url_parts = []
        if meeting.meeting_url:
            url_parts.append(meeting.meeting_url)
        if meeting.agenda_url:
            url_parts.append(meeting.agenda_url)
        if meeting.minutes_url:
            url_parts.append(meeting.minutes_url)
        
        # If no URLs, use title as fallback (but this allows multiple same-date meetings)
        url_key = '|'.join(sorted(url_parts)) if url_parts else meeting.title
        key = (meeting.date, url_key)
        
        if key in seen:
            # Merge additional URLs if found
            existing = seen[key]
            if meeting.meeting_url and not existing.meeting_url:
                existing.meeting_url = meeting.meeting_url
            if meeting.agenda_url and not existing.agenda_url:
                existing.agenda_url = meeting.agenda_url
            if meeting.minutes_url and not existing.minutes_url:
                existing.minutes_url = meeting.minutes_url
        else:
            seen[key] = meeting
    
    return list(seen.values())

