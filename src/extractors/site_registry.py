"""
Site-specific extractor registry dynamically loading and routing platform-optimized extraction logic.

Registry Pattern:
- register_extractor: Register (check_func, extract_func) pairs
- get_extractor: Match URL to registered extractors
- Dynamic imports prevent import errors from missing modules
- Graceful fallback to universal extractor
"""
from typing import List, Optional, Callable
from bs4 import BeautifulSoup

from ..storage.meeting_models import MeetingMetadata

SITE_EXTRACTORS = []


def register_extractor(check_func: Callable[[str], bool], extract_func: Callable):
    SITE_EXTRACTORS.append((check_func, extract_func))


def get_extractor(base_url: str) -> Optional[Callable]:
    for check_func, extract_func in SITE_EXTRACTORS:
        if check_func(base_url):
            return extract_func
    return None


try:
    from .site_specific.ventura import extract_ventura_meetings, should_use_ventura_extractor
    register_extractor(should_use_ventura_extractor, extract_ventura_meetings)
except ImportError:
    pass

try:
    from .site_specific.bethlehem import extract_bethlehem_meetings, should_use_bethlehem_extractor
    register_extractor(should_use_bethlehem_extractor, extract_bethlehem_meetings)
except ImportError:
    pass

try:
    from .site_specific.boarddocs import extract_boarddocs_meetings, should_use_boarddocs_extractor
    register_extractor(should_use_boarddocs_extractor, extract_boarddocs_meetings)
except ImportError:
    pass

try:
    from .site_specific.lansdale import extract_lansdale_meetings, should_use_lansdale_extractor
    register_extractor(should_use_lansdale_extractor, extract_lansdale_meetings)
except ImportError:
    pass

try:
    from .site_specific.facebook import extract_facebook_meetings, should_use_facebook_extractor
    register_extractor(should_use_facebook_extractor, extract_facebook_meetings)
except ImportError:
    pass

try:
    from .site_specific.eboardsolutions import extract_eboardsolutions_meetings, should_use_eboardsolutions_extractor
    register_extractor(should_use_eboardsolutions_extractor, extract_eboardsolutions_meetings)
except ImportError:
    pass
