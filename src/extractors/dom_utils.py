"""DOM extraction utilities for meeting data."""
from typing import Optional, List
from urllib.parse import urljoin
from bs4 import Tag


def extract_text_from_element(element: Tag) -> str:
    return element.get_text(strip=True)


def find_links_in_element(element: Tag) -> List[Tag]:
    return element.find_all('a', href=True)


def get_full_url(href: str, base_url: str) -> str:
    return urljoin(base_url, href)


def classify_link_type(href: str, text: str) -> Optional[str]:
    href_lower = href.lower()
    text_lower = text.lower()
    
    video_indicators = ['youtube', 'vimeo', 'video', 'watch', 'media', 'swagit', 'granicus']
    if any(v in href_lower for v in video_indicators):
        return 'video'
    
    if 'minutes' in href_lower or 'minute' in text_lower:
        return 'minutes'
    
    if 'agenda' in href_lower or 'agenda' in text_lower:
        return 'agenda'
    
    return None


def extract_date_from_attributes(element: Tag) -> Optional[str]:
    date_attrs = ['data-date', 'data-meeting-date', 'datetime', 'data-day']
    for attr in date_attrs:
        if element.has_attr(attr):
            return element.get(attr)
    return None

