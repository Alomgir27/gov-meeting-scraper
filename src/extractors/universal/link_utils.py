"""
Link utility functions for video platform detection and URL classification.

Video Detection:
- Platform domains (YouTube, Vimeo, Swagit, Granicus, etc.)
- Video keywords (watch, recording, stream, media)
- File extensions (.mp4, .webm, .m3u8)
"""
from bs4 import Tag

from ...utils.patterns import VIDEO_EXTENSIONS, VIDEO_KEYWORDS, VIDEO_PLATFORMS


def is_video_link(link: Tag) -> bool:
    if not link or not link.get('href'):
        return False
    
    href = link.get('href', '').lower()
    text = link.get_text(strip=True).lower()
    data_file = link.get('data-file-name', '').lower()
    
    return (
        any(href.endswith(ext) for ext in VIDEO_EXTENSIONS) or
        any(data_file.endswith(ext) for ext in VIDEO_EXTENSIONS) or
        any(kw in text for kw in VIDEO_KEYWORDS) or
        any(kw in href for kw in VIDEO_KEYWORDS) or
        any(domain in href for domain in VIDEO_PLATFORMS) or
        '/resource-manager/' in href
    )

