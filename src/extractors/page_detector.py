"""
Page structure detector identifying optimal extraction strategy (table, calendar, list, or container-based).

Detection Patterns:
- table: Large tables with 3+ rows
- calendar: Year and month headings structure
- list: List items with date patterns
- paragraph: Dense paragraphs with dates and bold text
- container: Default fallback for generic layouts
"""
from typing import List
from bs4 import BeautifulSoup
from ..utils.patterns import COMPILED_PATTERNS


def detect_all_page_types(html: str, url: str) -> List[str]:
    """
    Detect ALL applicable extraction types on the page.
    Returns list of types to enable multi-strategy extraction.
    """
    soup = BeautifulSoup(html, 'lxml')
    types = []
    
    tables = soup.find_all('table')
    large_tables = [t for t in tables if len(t.find_all('tr')) > 3]
    if large_tables:
        types.append('table')
    
    year_headings = soup.find_all(['h1', 'h2', 'h3'], string=COMPILED_PATTERNS['year_strict'])
    month_headings = soup.find_all(['h3', 'h4'], string=COMPILED_PATTERNS['month_full'])
    if year_headings and month_headings:
        types.append('calendar')
    
    list_items = soup.find_all('li')
    meeting_lists = [li for li in list_items if COMPILED_PATTERNS['date_simple'].search(li.get_text())]
    if len(meeting_lists) > 3:
        types.append('list')
    
    paragraphs = soup.find_all('p')
    dense_paragraphs = []
    for p in paragraphs:
        strong_tags = p.find_all(['strong', 'b'])
        if len(strong_tags) > 2:
            dates_in_p = COMPILED_PATTERNS['month_any'].findall(p.get_text())
            if len(dates_in_p) > 2:
                dense_paragraphs.append(p)
    if dense_paragraphs:
        types.append('paragraph')
    
    if not types:
        types.append('container')
    
    return types


def detect_page_type(html: str, url: str) -> str:
    soup = BeautifulSoup(html, 'lxml')
    
    tables = soup.find_all('table')
    large_tables = [t for t in tables if len(t.find_all('tr')) > 3]
    if large_tables:
        return 'table'
    
    year_headings = soup.find_all(['h1', 'h2', 'h3'], string=COMPILED_PATTERNS['year_strict'])
    month_headings = soup.find_all(['h3', 'h4'], string=COMPILED_PATTERNS['month_full'])
    if year_headings and month_headings:
        return 'calendar'
    
    list_items = soup.find_all('li')
    meeting_lists = [li for li in list_items if COMPILED_PATTERNS['date_simple'].search(li.get_text())]
    if len(meeting_lists) > 3:
        return 'list'
    
    paragraphs = soup.find_all('p')
    dense_paragraphs = []
    for p in paragraphs:
        strong_tags = p.find_all(['strong', 'b'])
        if len(strong_tags) > 2:
            dates_in_p = COMPILED_PATTERNS['month_any'].findall(p.get_text())
            if len(dates_in_p) > 2:
                dense_paragraphs.append(p)
    if dense_paragraphs:
        return 'paragraph'
    
    return 'container'


def should_navigate_details(elem) -> bool:
    text = elem.get_text(' ', strip=True)
    links = elem.find_all('a', href=True)
    
    has_date = bool(COMPILED_PATTERNS['date_simple'].search(text))
    link_count = len(links)
    
    if has_date and link_count == 1:
        return True
    
    if has_date and link_count == 0:
        return False
    
    agenda_count = sum(1 for l in links if any(kw in l.get_text().lower() for kw in ['agenda', 'packet']))
    if agenda_count == 0 and link_count > 0:
        return True
    
    return False

