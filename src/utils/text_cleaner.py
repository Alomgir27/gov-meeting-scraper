"""
Text normalization utilities removing unicode artifacts, dates, and extra whitespace.

Cleaning Functions:
- remove_unicode_chars: Strip non-ASCII characters
- clean_title: Remove date prefixes, posted timestamps, normalize whitespace
- clean_url: Validate and normalize URLs
- normalize_text: Replace unicode dashes, spaces, zero-width characters
"""
import re
import unicodedata
from typing import Optional


def remove_unicode_chars(text: str) -> str:
    """Remove all non-ASCII unicode characters."""
    result = []
    for char in text:
        if ord(char) < 128:
            result.append(char)
        elif char.isspace():
            result.append(' ')
    return ''.join(result)


def clean_title(title: Optional[str]) -> Optional[str]:
    """Clean meeting title by removing unicode, redundant dates, and normalizing."""
    if not title:
        return None
    
    title = remove_unicode_chars(title)
    
    title = re.sub(r'Posted\s+\w+\s+\d{1,2},?\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M', '', title, flags=re.IGNORECASE)
    
    date_prefixes = [
        r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\s*[-—–]?\s*',
        r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*[-—–]?\s*',
        r'^\d{4}-\d{2}-\d{2}\s*[-—–]?\s*',
    ]
    
    for pattern in date_prefixes:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    title = re.sub(r'\s+', ' ', title)
    
    title = re.sub(r'^[-—–\s]+|[-—–\s]+$', '', title)
    
    title = title.strip()
    
    if len(title) > 200:
        title = title[:197] + '...'
    
    if not title or len(title) < 3:
        return None
    
    return title


def clean_url(url: Optional[str]) -> Optional[str]:
    """Clean and validate URL."""
    if not url:
        return None
    
    url = url.strip()
    
    if not url.startswith(('http://', 'https://')):
        return None
    
    return url


def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and special characters."""
    text = text.replace('\u2014', '-')
    text = text.replace('\u2009', ' ')
    text = text.replace('\u2013', '-')
    text = text.replace('\xa0', ' ')
    text = text.replace('\u200b', '')
    
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

