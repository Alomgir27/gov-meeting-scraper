"""
Universal link classifier using keyword scoring to categorize agenda, minutes, and video URLs.

Classification Strategy:
- Score links based on keyword matches in text and href
- Bonus points for file extensions (.pdf, .mp4, .m3u8)
- Bonus points for video platforms (YouTube, Vimeo, Swagit, Granicus)
- Return highest-scoring link for each category
"""
from typing import Dict, Optional
from urllib.parse import urljoin

from ..utils.patterns import (
    AGENDA_KEYWORDS, 
    MINUTES_KEYWORDS, 
    VIDEO_KEYWORDS, 
    VIDEO_PLATFORMS,
    DOCUMENT_EXTENSIONS,
    VIDEO_EXTENSIONS
)


def classify_link_universal(link, context_text: str = '') -> Optional[str]:
    href = link.get('href', '')
    link_text = link.get_text(' ', strip=True).lower()
    combined_text = (link_text + ' ' + context_text).lower()
    href_lower = href.lower()
    
    agenda_score = sum(kw in combined_text for kw in AGENDA_KEYWORDS)
    minutes_score = sum(kw in combined_text for kw in MINUTES_KEYWORDS)
    video_score = sum(kw in combined_text for kw in VIDEO_KEYWORDS)
    video_score += sum(platform in href_lower for platform in VIDEO_PLATFORMS)
    
    if '.pdf' in href_lower:
        if any(kw in combined_text for kw in AGENDA_KEYWORDS):
            agenda_score += 2
        if any(kw in combined_text for kw in MINUTES_KEYWORDS):
            minutes_score += 2
    
    if any(ext in href_lower for ext in ['.mp4', '.m3u8', '.webm']):
        video_score += 3
    
    scores = {'agenda': agenda_score, 'minutes': minutes_score, 'video': video_score}
    max_type = max(scores, key=scores.get)
    
    if scores[max_type] > 0:
        return max_type
    
    return None


def extract_and_classify_links(container, base_url: str) -> Dict[str, Optional[str]]:
    links = {'agenda': None, 'minutes': None, 'video': None}
    link_scores = {'agenda': 0, 'minutes': 0, 'video': 0}
    used_urls = set()
    context_text = container.get_text(' ', strip=True).lower()
    
    for link in container.find_all('a', href=True):
        href = link.get('href')
        if not href or href.startswith('#') or href.startswith('javascript:'):
            continue
        
        full_url = urljoin(base_url, href)
        
        if full_url in used_urls:
            continue
        
        link_text = link.get_text(' ', strip=True).lower()
        combined_text = (link_text + ' ' + context_text).lower()
        href_lower = href.lower()
        
        agenda_score = sum(kw in combined_text for kw in AGENDA_KEYWORDS)
        minutes_score = sum(kw in combined_text for kw in MINUTES_KEYWORDS)
        video_score = sum(kw in combined_text for kw in VIDEO_KEYWORDS)
        video_score += sum(platform in href_lower for platform in VIDEO_PLATFORMS)
        
        for ext in DOCUMENT_EXTENSIONS:
            if ext in href_lower:
                if any(kw in combined_text for kw in AGENDA_KEYWORDS):
                    agenda_score += 2
                elif any(kw in combined_text for kw in MINUTES_KEYWORDS):
                    minutes_score += 2
                else:
                    agenda_score += 1
        
        if any(kw in href_lower for kw in AGENDA_KEYWORDS):
            agenda_score += 2
        if any(kw in href_lower for kw in MINUTES_KEYWORDS):
            minutes_score += 2
        if any(kw in href_lower for kw in VIDEO_KEYWORDS):
            video_score += 2
        
        if any(ext in href_lower for ext in ['.mp4', '.m3u8', '.webm']):
            video_score += 3
        
        best_type = None
        best_score = 0
        
        if agenda_score > link_scores['agenda'] and agenda_score > 0:
            best_type = 'agenda'
            best_score = agenda_score
        
        if minutes_score > link_scores['minutes'] and minutes_score > best_score:
            best_type = 'minutes'
            best_score = minutes_score
        
        if video_score > link_scores['video'] and video_score > best_score:
            best_type = 'video'
            best_score = video_score
        
        if best_type and best_score > 0:
            links[best_type] = full_url
            link_scores[best_type] = best_score
            used_urls.add(full_url)
    
    return {
        'agenda': links['agenda'],
        'minutes': links['minutes'], 
        'video': links['video']
    }


