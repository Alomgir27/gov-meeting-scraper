"""Facebook videos extractor with modal handling."""
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ..dom_utils import get_full_url
from ..date_parser import extract_date_from_text


async def collect_facebook_html(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    """Collect HTML from Facebook videos page with modal handling."""
    htmls = []
    page = None
    
    try:
        page = await browser_manager.new_page()
        
        print("Navigating to Facebook videos page...")
        await page.goto(base_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        
        # Handle login/cookie modal - try to close it
        try:
            close_selectors = [
                'div[aria-label="Close"]',
                'button[aria-label="Close"]',
                '[data-testid="cookie-policy-manage-dialog-accept-button"]',
                '[data-testid="non-users-dialog-close"]',
                'div[role="button"]:has-text("Close")',
                'div[aria-label="Close"]:visible',
            ]
            
            for selector in close_selectors:
                try:
                    close_button = await page.query_selector(selector)
                    if close_button:
                        print(f"Closing modal with selector: {selector}")
                        await close_button.click()
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
        except Exception as modal_error:
            print(f"Could not close modal (might not exist): {modal_error}")
        
        # Scroll to load more videos with infinite scroll detection
        print("Scrolling to load all videos...")
        last_height = await page.evaluate("document.body.scrollHeight")
        scroll_attempts = 0
        max_attempts = 20  # Maximum scroll attempts
        no_change_count = 0
        
        while scroll_attempts < max_attempts and no_change_count < 3:
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)  # Wait for content to load
            
            # Calculate new height
            new_height = await page.evaluate("document.body.scrollHeight")
            
            if new_height == last_height:
                no_change_count += 1
                print(f"  No new content loaded (attempt {no_change_count}/3)")
            else:
                no_change_count = 0
                print(f"  Scrolled {scroll_attempts + 1} times, loaded more content...")
            
            last_height = new_height
            scroll_attempts += 1
        
        print(f"Finished scrolling after {scroll_attempts} attempts")
        
        html = await page.content()
        htmls.append(html)
        print(f"Collected Facebook videos page")
        
    except Exception as e:
        print(f"Error collecting Facebook HTML: {e}")
    finally:
        if page:
            try:
                await page.close()
            except:
                pass
    
    return htmls


def extract_facebook_meetings(soup: BeautifulSoup, base_url: str) -> List[MeetingMetadata]:
    """Extract meeting metadata from Facebook videos page."""
    meetings = []
    seen_urls = set()
    
    # Method 1: Find videos through aria-labels (main video)
    all_elements = soup.find_all(attrs={'aria-label': re.compile(r'.*', re.I)})
    print(f"Found {len(all_elements)} elements with aria-labels")
    
    for element in all_elements:
        aria_label = element.get('aria-label', '').strip()
        
        if len(aria_label) < 10:
            continue
        
        skip_patterns = [
            r'^(Like|Comment|Share|See|View|Log|Email|Password|Back|Profile|Facebook)',
            r'(people|person|reactions|ago)$',
            r'^\d+\s+(reaction|comment|share)',
        ]
        
        if any(re.search(pattern, aria_label, re.I) for pattern in skip_patterns):
            continue
        
        video_url = None
        parent = element.parent
        for _ in range(5):
            if parent:
                link = parent.find('a', href=re.compile(r'/videos/'))
                if link:
                    href = link.get('href', '')
                    video_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
                    break
                parent = parent.parent
        
        if not video_url:
            if element.name == 'a':
                href = element.get('href', '')
                if '/videos/' in href:
                    video_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
            else:
                link = element.find('a', href=re.compile(r'/videos/'))
                if link:
                    href = link.get('href', '')
                    video_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
        
        if video_url:
            clean_url = video_url.split('?')[0].split('#')[0]
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                date = extract_date_from_title_facebook(aria_label)
                
                meeting = MeetingMetadata()
                meeting.title = aria_label
                meeting.date = date
                meeting.meeting_url = clean_url
                meetings.append(meeting)
    
    # Method 2: Find all video links and extract nearby titles
    video_links = soup.find_all('a', href=re.compile(r'/videos/'))
    print(f"Found {len(video_links)} video links")
    
    for link in video_links:
        href = link.get('href', '')
        video_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
        clean_url = video_url.split('?')[0].split('#')[0]
        
        if clean_url in seen_urls:
            continue
        
        # Try to find title from nearby elements
        title = None
        
        # Check aria-label on link
        title = link.get('aria-label', '').strip()
        
        # Check text content in link
        if not title or len(title) < 10:
            link_text = link.get_text(strip=True)
            if len(link_text) > 10:
                title = link_text
        
        # Check parent and sibling elements for title
        if not title or len(title) < 10:
            parent = link.parent
            for _ in range(3):
                if parent:
                    # Look for span or div with meaningful text
                    text_elements = parent.find_all(['span', 'div'], recursive=False)
                    for elem in text_elements:
                        text = elem.get_text(strip=True)
                        if len(text) > 15 and 'view' not in text.lower():
                            title = text
                            break
                    if title and len(title) > 15:
                        break
                    parent = parent.parent
        
        if not title or len(title) < 10:
            continue
        
        # Skip if title looks like a count or generic text
        if re.match(r'^\d+[\s,\d]*\s*(view|like|comment)', title, re.I):
            continue
        
        seen_urls.add(clean_url)
        date = extract_date_from_title_facebook(title)
        
        meeting = MeetingMetadata()
        meeting.title = title
        meeting.date = date
        meeting.meeting_url = clean_url
        meetings.append(meeting)
    
    print(f"Extracted {len(meetings)} unique videos")
    return meetings


def extract_date_from_title_facebook(title: str) -> str:
    """Extract date from Facebook video title."""
    # Try common date patterns
    date = extract_date_from_text(title)
    if date:
        return date
    
    # Try additional Facebook-specific patterns
    patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YY or MM-DD-YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',     # YYYY-MM-DD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            try:
                groups = match.groups()
                if len(groups[2]) == 2:
                    year = '20' + groups[2]
                else:
                    year = groups[2]
                
                date_str = f"{year}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt.strftime('%Y-%m-%d')
            except:
                continue
    
    return None


def should_use_facebook_extractor(base_url: str) -> bool:
    """Check if Facebook extractor should be used."""
    return 'facebook.com' in base_url.lower()
