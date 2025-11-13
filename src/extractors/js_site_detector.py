"""Detect and handle JavaScript-heavy sites."""
import re
from typing import Optional


def is_js_heavy_site(html: str, url: str) -> bool:
    """Detect if site loads content via JavaScript."""
    if 'datatables' in html.lower():
        return True
    
    if 'novusagenda' in url.lower():
        return True
    
    if 'towncloud' in url.lower():
        return True
    
    if re.search(r'data-url=["\']/[^"\']+/table_data', html):
        return True
    
    if '__doPostBack' in html or 'RadGrid' in html:
        return True
    
    if 'react-root' in html or 'ng-app' in html or 'vue-app' in html:
        return True
    
    return False


async def wait_for_js_content(page, url: str):
    """Wait for JavaScript content to load based on site type."""
    try:
        if 'novusagenda' in url.lower():
            await page.wait_for_selector('table[id*="radGrid"]', timeout=8000)
            
            await page.wait_for_timeout(3000)
            
            try:
                rows = await page.query_selector_all('tr.rgRow, tr.rgAltRow')
                if len(rows) == 0:
                    await page.wait_for_timeout(3000)
            except:
                pass
        
        elif 'towncloud' in url.lower():
            await page.wait_for_selector('table.tc-table', timeout=8000)
            await page.wait_for_timeout(2000)
        
        else:
            await page.wait_for_timeout(4000)
    
    except Exception:
        await page.wait_for_timeout(5000)


def get_content_selector(url: str) -> Optional[str]:
    """Get CSS selector to wait for based on site type."""
    if 'towncloud' in url:
        return 'table.tc-table tbody tr'
    
    if 'novusagenda' in url:
        return 'table[id*="radGrid"]'
    
    if 'granicus' in url:
        return '.minutes-item, .meeting-row'
    
    return None

