"""Click calendar navigation buttons to access all data."""
import hashlib
from typing import List, Set
from bs4 import BeautifulSoup
from ..utils.logger import setup_logger

logger = setup_logger("calendar_navigator")


def get_html_hash(html: str) -> str:
    return hashlib.md5(html.encode()).hexdigest()


def is_year_relevant(text: str, start_year: int, end_year: int) -> bool:
    if not text.isdigit() or len(text) != 4:
        return False
    year = int(text)
    return start_year - 1 <= year <= end_year + 1


async def get_all_year_pages(browser_manager, base_url: str, start_year: int, end_year: int) -> List[str]:
    htmls = []
    seen_hashes: Set[str] = set()
    
    try:
        page = await browser_manager.new_page()
        if not page:
            return htmls
        
        try:
            await page.goto(base_url, wait_until='domcontentloaded', timeout=30000)
            
            initial_html = await page.content()
            initial_hash = get_html_hash(initial_html)
            seen_hashes.add(initial_hash)
            htmls.append(initial_html)
            
            soup = BeautifulSoup(initial_html, 'lxml')
            
            year_targets = []
            for elem in soup.find_all(['button', 'a', 'select']):
                if elem.name == 'select':
                    for option in elem.find_all('option'):
                        text = option.get_text(strip=True)
                        if is_year_relevant(text, start_year, end_year):
                            select_id = elem.get('id') or elem.get('name') or 'select'
                            year_targets.append(('select', select_id, text))
                else:
                    text = elem.get_text(strip=True)
                    if is_year_relevant(text, start_year, end_year):
                        year_targets.append(('button', text, None))
            
            year_targets = list(dict.fromkeys(year_targets))
            
            if year_targets:
                logger.info(f"Found {len(year_targets)} year navigation controls")
            
            for control_type, identifier, value in year_targets:
                try:
                    if control_type == 'select':
                        await page.select_option(f'select', value)
                    else:
                        selector = f"button:has-text('{identifier}'), a:has-text('{identifier}')"
                        await page.click(selector, timeout=5000)
                    
                    await page.wait_for_timeout(800)
                    
                    new_html = await page.content()
                    new_hash = get_html_hash(new_html)
                    
                    if new_hash not in seen_hashes:
                        seen_hashes.add(new_hash)
                        htmls.append(new_html)
                        logger.info(f"✓ New content for {identifier}")
                    
                except Exception:
                    pass
            
        finally:
            await page.close()
            
    except Exception as e:
        logger.warning(f"Calendar navigation error: {str(e)}")
    
    return htmls

