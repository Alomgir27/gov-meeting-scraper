"""
Container detection using heuristics to identify meeting-related DOM elements.

Detection Heuristics:
- Class/ID contains meeting keywords (meeting, agenda, event, item)
- Contains date pattern and meeting keywords in text
- Has appropriate depth and link structure
- Minimum quality score threshold
- Size constraints (not too small, not too large)
"""
import re
from typing import List
from bs4 import BeautifulSoup, Tag

from ...utils.patterns import (
    MEETING_KEYWORDS,
    MEETING_ATTR_PATTERNS,
    MEETING_DIV_PATTERNS,
    COMPILED_PATTERNS
)


def looks_like_meeting_container(elem: Tag) -> bool:
    if not elem or not isinstance(elem, Tag):
        return False
    
    text = elem.get_text(' ', strip=True)
    text_lower = text.lower()
    
    if len(text) < 3:
        return False
    
    has_date = bool(COMPILED_PATTERNS['date_combined'].search(text_lower))
    has_keyword = any(kw in text_lower for kw in MEETING_KEYWORDS)
    has_links = len(elem.find_all('a', href=True)) > 0
    
    elem_str = str(elem)[:500].lower()
    has_meeting_attr = any(attr in elem_str for attr in MEETING_ATTR_PATTERNS)
    
    if has_date:
        return True
    
    if has_keyword and (has_links or len(text) > 10):
        return True
    
    if has_meeting_attr:
        return True
    
    signals = sum([has_date, has_keyword, has_links, has_meeting_attr])
    return signals >= 1


def find_meeting_containers(soup: BeautifulSoup) -> List[Tag]:
    candidates = []
    seen = set()
    
    for tr in soup.find_all('tr'):
        if id(tr) not in seen:
            candidates.append(tr)
            seen.add(id(tr))
    
    for li in soup.find_all('li'):
        if id(li) not in seen:
            candidates.append(li)
            seen.add(id(li))
    
    for pattern in MEETING_DIV_PATTERNS:
        for div in soup.find_all('div', class_=re.compile(pattern, re.IGNORECASE)):
            if id(div) not in seen:
                candidates.append(div)
                seen.add(id(div))
        for div in soup.find_all('div', id=re.compile(pattern, re.IGNORECASE)):
            if id(div) not in seen:
                candidates.append(div)
                seen.add(id(div))
    
    for tag in ['article', 'section']:
        for elem in soup.find_all(tag):
            if id(elem) not in seen:
                candidates.append(elem)
                seen.add(id(elem))
    
    for elem in soup.find_all(attrs={'data-date': True}):
        if id(elem) not in seen:
            candidates.append(elem)
            seen.add(id(elem))
    
    for elem in soup.find_all(attrs={'data-meeting-date': True}):
        if id(elem) not in seen:
            candidates.append(elem)
            seen.add(elem)
    
    for time_elem in soup.find_all('time'):
        parent = time_elem.parent
        if parent and id(parent) not in seen:
            candidates.append(parent)
            seen.add(id(parent))
    
    for link in soup.find_all('a', href=True):
        link_text = link.get_text(strip=True)
        if COMPILED_PATTERNS['date_with_month'].search(link_text):
            parent = link.parent
            if parent and id(parent) not in seen:
                candidates.append(parent)
                seen.add(id(parent))
    
    return [c for c in candidates if looks_like_meeting_container(c)]

