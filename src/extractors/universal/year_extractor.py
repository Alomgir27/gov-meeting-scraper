"""Year extraction from headings and context."""
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup, Tag

from ...utils.patterns import YEAR_MIN, YEAR_MAX, COMPILED_PATTERNS


def extract_year_from_heading(elem: Tag) -> Optional[int]:
    for heading in elem.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = heading.get_text(' ', strip=True)
        year_match = COMPILED_PATTERNS['year'].search(text)
        if year_match:
            year = int(year_match.group(1))
            if YEAR_MIN <= year <= YEAR_MAX:
                return year
    return None


def find_context_year(elem: Tag, soup: BeautifulSoup) -> Optional[int]:
    current = elem
    while current:
        year = extract_year_from_heading(current)
        if year:
            return year
        current = current.parent
        if current == soup:
            break
    
    page_text = soup.get_text()
    years = COMPILED_PATTERNS['year'].findall(page_text)
    if years:
        year_counts = {}
        for y in years:
            year_int = int(y)
            if YEAR_MIN <= year_int <= YEAR_MAX:
                year_counts[year_int] = year_counts.get(year_int, 0) + 1
        if year_counts:
            return max(year_counts, key=year_counts.get)
    
    return datetime.now().year

