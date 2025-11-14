"""
Link enhancer extracting additional links from parent and sibling DOM elements for complete data collection.

Enhancement Methods:
- check_parent_links: Extract from parent container
- check_sibling_links: Check previous and next siblings
- merge_links: Combine results prioritizing non-null values
- extract_all_links: Full extraction from container hierarchy
"""
from typing import Dict, Optional
from urllib.parse import urljoin
from bs4 import Tag
from .link_classifier import extract_and_classify_links


def check_parent_links(container: Tag, base_url: str) -> Dict[str, Optional[str]]:
    """Check parent element for additional links."""
    if not container or not container.parent:
        return {'agenda': None, 'minutes': None, 'video': None}
    
    parent = container.parent
    return extract_and_classify_links(parent, base_url)


def check_sibling_links(container: Tag, base_url: str) -> Dict[str, Optional[str]]:
    """Check sibling elements for additional links."""
    if not container:
        return {'agenda': None, 'minutes': None, 'video': None}
    
    links = {'agenda': None, 'minutes': None, 'video': None}
    
    prev_sibling = container.previous_sibling
    if prev_sibling and isinstance(prev_sibling, Tag):
        prev_links = extract_and_classify_links(prev_sibling, base_url)
        for link_type, url in prev_links.items():
            if url and not links.get(link_type):
                links[link_type] = url
    
    next_sibling = container.next_sibling
    if next_sibling and isinstance(next_sibling, Tag):
        next_links = extract_and_classify_links(next_sibling, base_url)
        for link_type, url in next_links.items():
            if url and not links.get(link_type):
                links[link_type] = url
    
    return links


def merge_links(*link_dicts) -> Dict[str, Optional[str]]:
    """Merge multiple link dictionaries, preferring non-null values."""
    merged = {'agenda': None, 'minutes': None, 'video': None}
    
    for links in link_dicts:
        for link_type in ['agenda', 'minutes', 'video']:
            if links.get(link_type) and not merged.get(link_type):
                merged[link_type] = links[link_type]
    
    return merged


def extract_all_links(container: Tag, base_url: str) -> Dict[str, Optional[str]]:
    """
    Extract links from container, parent, and siblings.
    Returns merged results with maximum coverage.
    """
    container_links = extract_and_classify_links(container, base_url)
    parent_links = check_parent_links(container, base_url)
    sibling_links = check_sibling_links(container, base_url)
    
    return merge_links(container_links, sibling_links, parent_links)

