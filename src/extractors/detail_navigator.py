"""
Detail page navigator extracting additional agenda, minutes, and video links from dedicated meeting pages.

Navigation Logic:
- Detects single-link containers pointing to detail pages
- Identifies "detail", "view", "more" keywords
- Navigates to detail page and extracts all link types
- Returns agenda, minutes, and video URLs
"""
import asyncio
from typing import Dict, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from ..utils.logger import setup_logger
from ..utils.patterns import DETAIL_PAGE_KEYWORDS

logger = setup_logger("detail_navigator")


async def should_navigate_to_detail(container: Tag, existing_links: Dict) -> Optional[str]:
    has_agenda = existing_links.get('agenda')
    has_minutes = existing_links.get('minutes')
    has_video = existing_links.get('video')
    
    if has_agenda and has_minutes and has_video:
        return None
    
    links = container.find_all('a', href=True)
    if len(links) == 1:
        link = links[0]
        href = link.get('href')
        text = link.get_text(strip=True).lower()
        
        if 'detail' in text or 'view' in text or 'more' in text or len(text) < 20:
            return href
    
    for link in links:
        href = link.get('href', '').lower()
        text = link.get_text(strip=True).lower()
        
        if any(kw in text for kw in DETAIL_PAGE_KEYWORDS):
            return link.get('href')
        
        if any(kw in href for kw in ['detail', 'event', 'meeting']):
            return link.get('href')
    
    return None


async def extract_from_detail_page(browser_manager, detail_url: str, base_url: str) -> Dict[str, Optional[str]]:
    from .link_classifier import extract_and_classify_links
    
    try:
        page = await browser_manager.new_page()
        if not page:
            return {'agenda': None, 'minutes': None, 'video': None}
        
        try:
            await page.goto(detail_url, wait_until='domcontentloaded', timeout=15000)
            html = await page.content()
            
            soup = BeautifulSoup(html, 'lxml')
            links = extract_and_classify_links(soup.body or soup, base_url)
            
            logger.debug(f"Detail page {detail_url} extracted: {links}")
            return links
            
        finally:
            await page.close()
            
    except Exception as e:
        logger.warning(f"Failed to extract from detail page {detail_url}: {str(e)}")
        return {'agenda': None, 'minutes': None, 'video': None}

