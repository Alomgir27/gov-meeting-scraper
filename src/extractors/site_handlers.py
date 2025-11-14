"""
Site-specific handler dispatcher for platforms requiring custom data collection strategies.

Supported Platforms:
- Ventura: Custom API-based collection
- Bethlehem: Multi-year navigation
- Lansdale: Calendar-based extraction
- Facebook: Event parsing
- BoardDocs: Meeting navigation
- eBoardSolutions: Board meeting extraction
"""
from typing import List


async def get_site_htmls(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    
    if 'cityofventura.ca.gov' in base_url.lower():
        from .site_specific.ventura import collect_ventura_html
        return await collect_ventura_html(browser_manager, base_url, start_date, end_date)
    
    if 'bethlehem-pa.gov' in base_url.lower():
        from .site_specific.bethlehem import collect_bethlehem_html
        return await collect_bethlehem_html(browser_manager, base_url, start_date, end_date)
    
    if 'lansdale.org' in base_url.lower():
        from .site_specific.lansdale import collect_lansdale_html
        return await collect_lansdale_html(browser_manager, base_url, start_date, end_date)
    
    if 'facebook.com' in base_url.lower():
        from .site_specific.facebook import collect_facebook_html
        return await collect_facebook_html(browser_manager, base_url, start_date, end_date)
    
    if 'boarddocs.com' in base_url.lower():
        from .site_specific.boarddocs import collect_boarddocs_html
        return await collect_boarddocs_html(browser_manager, base_url, start_date, end_date)
    
    if 'eboardsolutions.com' in base_url.lower():
        from .site_specific.eboardsolutions import collect_eboardsolutions_html
        return await collect_eboardsolutions_html(browser_manager, base_url, start_date, end_date)
    
    return []


def needs_special_collection(base_url: str) -> bool:
    special_sites = [
        'cityofventura.ca.gov',
        'bethlehem-pa.gov',
        'lansdale.org',
        'facebook.com',
        'boarddocs.com',
        'eboardsolutions.com',
    ]
    return any(site in base_url.lower() for site in special_sites)

