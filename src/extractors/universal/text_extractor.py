"""Text and title extraction utilities."""
from typing import List
from bs4 import BeautifulSoup, Tag

from ...utils.patterns import MEETING_KEYWORDS, COMPILED_PATTERNS


def extract_title(elem: Tag, date_str: str) -> str:
    """Universal title extraction - works for tables, containers, paragraphs."""
    
    for link in elem.find_all('a', href=True):
        href = link.get('href', '').lower()
        if 'agenda' in href or 'viewfile' in href or 'meeting' in href:
            title = link.get_text(' ', strip=True)
            if 10 <= len(title) <= 150:
                title_lower = title.lower()
                if any(kw in title_lower for kw in MEETING_KEYWORDS):
                    if not any(btn in title_lower for btn in ['download', 'view pdf', 'previous version']):
                        return title
    
    all_text = elem.get_text('\n', strip=True)
    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
    
    for line in lines:
        if len(line) < 8 or len(line) > 150:
            continue
        
        line_lower = line.lower()
        
        if any(btn in line_lower for btn in ['download', 'view', 'click', 'select', 'filter', 'previous version']):
            continue
        
        if line.replace('/', '').replace('-', '').replace(' ', '').replace(',', '').isdigit():
            continue
        
        if any(kw in line_lower for kw in MEETING_KEYWORDS):
            return line
    
    for line in lines[:5]:
        if 10 <= len(line) <= 100:
            line_lower = line.lower()
            if any(btn in line_lower for btn in ['download', 'view', 'click']):
                continue
            digit_ratio = sum(c.isdigit() for c in line) / len(line) if line else 1
            if digit_ratio < 0.4:
                return line
    
    return f"Meeting on {date_str}"


def split_paragraph_meetings(paragraph: Tag) -> List[Tag]:
    strong_tags = paragraph.find_all(['strong', 'b'])
    
    if len(strong_tags) <= 1:
        return [paragraph]
    
    containers = []
    for strong in strong_tags:
        date_text = strong.get_text().strip()
        if not COMPILED_PATTERNS['month_short'].match(date_text):
            continue
        
        virtual_container = BeautifulSoup('', 'lxml')
        container_p = virtual_container.new_tag('p')
        
        container_p.append(virtual_container.new_tag('strong'))
        container_p.strong.string = date_text
        
        current = strong.next_sibling
        while current:
            if isinstance(current, Tag) and current.name in ['strong', 'b']:
                next_date = current.get_text().strip()
                if COMPILED_PATTERNS['month_short'].match(next_date):
                    break
            
            if isinstance(current, str):
                container_p.append(virtual_container.new_string(current))
            elif isinstance(current, Tag):
                container_p.append(current.__copy__())
            
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
        
        containers.append(container_p)
    
    return containers if containers else [paragraph]

