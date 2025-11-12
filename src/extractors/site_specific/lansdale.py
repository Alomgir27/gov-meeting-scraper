"""Lansdale CivicMedia extractor with pagination support."""
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ..dom_utils import get_full_url
from ..date_parser import extract_date_from_text


async def collect_lansdale_html(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    htmls = []
    page = None
    
    try:
        page = await browser_manager.new_page()
        
        print("Navigating to Lansdale CivicMedia...")
        url_with_all = base_url if '#' in base_url else f"{base_url}#allVideos"
        await page.goto(url_with_all, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        view_all_link = await page.query_selector('a[href*="#allVideos"], a:has-text("View All")')
        if view_all_link:
            print("Clicking 'View All' to show all videos...")
            await view_all_link.click()
            await page.wait_for_timeout(2000)
        
        html_current = await page.content()
        htmls.append(html_current)
        soup = BeautifulSoup(html_current, 'lxml')
        
        target_years = set()
        if start_date and end_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            for year in range(start_dt.year, end_dt.year + 1):
                target_years.add(str(year))
        
        pagination = soup.find('p', class_='pagination')
        if pagination:
            page_links = pagination.find_all('a')
            print(f"Found {len(page_links)} additional pages for base channel")
            
            for idx, page_link in enumerate(page_links, start=2):
                try:
                    onclick = page_link.get('href', '')
                    if 'javascript:__doPostBack' in onclick:
                        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", onclick)
                        if match:
                            event_target = match.group(1)
                            event_argument = match.group(2)
                            
                            print(f"Collecting base channel page {idx}...")
                            await page.evaluate(f"__doPostBack('{event_target}', '{event_argument}')")
                            await page.wait_for_timeout(4000)
                            
                            html = await page.content()
                            htmls.append(html)
                except Exception as page_error:
                    print(f"Error collecting page {idx}: {page_error}")
                    continue
        
        print(f"Navigating back to base channel to discover other channels...")
        await page.goto(base_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        html_current = await page.content()
        soup = BeautifulSoup(html_current, 'lxml')
        
        channel_links = soup.find_all('a', href=re.compile(r'/CivicMedia\?CID='))
        channels_to_scrape = []
        
        for link in channel_links:
            href = link.get('href', '')
            h4 = link.find('h4')
            if h4:
                channel_name = h4.get_text(strip=True)
                
                should_scrape = False
                if target_years:
                    for year in target_years:
                        if year in channel_name or year in href:
                            should_scrape = True
                            break
                else:
                    should_scrape = True
                
                if should_scrape and href not in [ch[0] for ch in channels_to_scrape]:
                    channels_to_scrape.append((href, channel_name))
                    print(f"Found channel: {channel_name}")
        
        for channel_href, channel_name in channels_to_scrape:
            if channel_href == base_url or channel_href.split('?')[-1] == base_url.split('?')[-1]:
                print(f"Skipping {channel_name} (already collected)")
                continue
            
            try:
                full_url = get_full_url(channel_href, base_url)
                print(f"\nNavigating to channel: {channel_name}")
                await page.goto(full_url, timeout=60000, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                channel_html = await page.content()
                htmls.append(channel_html)
                print(f"Collected {channel_name} page 1")
                
                channel_soup = BeautifulSoup(channel_html, 'lxml')
                pagination = channel_soup.find('p', class_='pagination')
                
                if pagination:
                    page_links = pagination.find_all('a')
                    print(f"Found {len(page_links)} additional pages for {channel_name}")
                    
                    for idx, page_link in enumerate(page_links, start=2):
                        try:
                            onclick = page_link.get('href', '')
                            if 'javascript:__doPostBack' in onclick:
                                match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", onclick)
                                if match:
                                    event_target = match.group(1)
                                    event_argument = match.group(2)
                                    
                                    await page.evaluate(f"__doPostBack('{event_target}', '{event_argument}')")
                                    await page.wait_for_timeout(4000)
                                    
                                    html = await page.content()
                                    htmls.append(html)
                                    print(f"Collected {channel_name} page {idx}")
                        except Exception as page_error:
                            print(f"Error collecting page {idx} from {channel_name}: {page_error}")
                            continue
            except Exception as channel_error:
                print(f"Error collecting channel {channel_name}: {channel_error}")
                continue
        
        print(f"\nTotal: Collected {len(htmls)} HTML pages from Lansdale")
        
    except Exception as e:
        print(f"Error collecting Lansdale HTML: {e}")
    finally:
        if page:
            try:
                await page.close()
            except:
                pass
    
    return htmls


def extract_video_url_from_page(soup: BeautifulSoup) -> str:
    """Extract actual video URL from embedded player."""
    iframe = soup.find('iframe', id='videoPlayer')
    if iframe:
        src = iframe.get('src', '')
        if src:
            return src
    return None

def extract_video_id_and_title(video_div):
    title = None
    video_id = None
    
    link = video_div.find('a', id=re.compile(r'lnkImage'))
    if link:
        img = link.find('img')
        if img:
            title = img.get('alt', '').strip()
    
            img_src = img.get('src', '')
            video_id_match = re.search(r'/videos/\d+/(\d+)/\1-', img_src)
            if video_id_match:
                video_id = video_id_match.group(1)
        
        if not title:
            h3 = link.find('h3')
            if h3:
                title = h3.get_text(strip=True)
    
    return title, video_id


def extract_date_from_title(title: str, base_url: str = None) -> str:
    """Extract date from title with dynamic year inference."""
    from datetime import datetime
    
    inferred_year = None
    if base_url:
        year_match = re.search(r'(20\d{2})', base_url)
        if year_match:
            inferred_year = year_match.group(1)
    
    if not inferred_year:
        inferred_year = str(datetime.now().year)
    
    month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})', title, re.I)
    if month_match:
        month_name = month_match.group(1)
        day = month_match.group(2).zfill(2)
        
        year = inferred_year
        title_year_match = re.search(r'20\d{2}', title)
        if title_year_match:
            year = title_year_match.group(0)
        
        date_str = f"{month_name} {day}, {year}"
        date = extract_date_from_text(date_str)
        if date:
            return date
    
    patterns = [
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', r'\3-\1-\2'),
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', r'\3-\1-\2'),
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', r'\3-\1-\2'),
        (r'(\d{6,8})', None),
    ]
    
    for pattern, replacement in patterns:
        match = re.search(pattern, title)
        if match:
            if replacement:
                matched_text = match.group(0)
                date_str = re.sub(pattern, replacement, matched_text)
                try:
                    from datetime import datetime
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    return dt.strftime('%Y-%m-%d')
                except:
                    pass
            else:
                date_digits = match.group(1)
                
                if len(date_digits) == 8:
                    month = date_digits[:2]
                    day = date_digits[2:4]
                    year = date_digits[4:]
                elif len(date_digits) == 6:
                    month = date_digits[:2]
                    day = date_digits[2:4]
                    year = '20' + date_digits[4:]
                else:
                    continue
                
                try:
                    from datetime import datetime
                    dt = datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
                    return dt.strftime('%Y-%m-%d')
                except:
                    pass
    
    return None


def extract_lansdale_meetings(soup: BeautifulSoup, base_url: str) -> List[MeetingMetadata]:
    meetings = []
    
    inferred_year = None
    channel_heading = soup.find('h1', class_='moduleTitle')
    if not channel_heading:
        channel_heading = soup.find('h2', class_='mediaTitle')
    
    if channel_heading:
        channel_text = channel_heading.get_text(strip=True)
        year_match = re.search(r'(20\d{2})', channel_text)
        if year_match:
            inferred_year = year_match.group(1)
    
    if not inferred_year:
        year_match = re.search(r'(20\d{2})', base_url)
        if year_match:
            inferred_year = year_match.group(1)
    
    if not inferred_year:
        inferred_year = str(datetime.now().year)
    
    current_video_id = None
    current_video_title = None
    
    video_player = soup.find('iframe', id='videoPlayer')
    if video_player:
        src = video_player.get('src', '')
        video_id_match = re.search(r'videoId=(\d+)', src)
        if video_id_match:
            current_video_id = video_id_match.group(1)
        
        title_elem = soup.find('h2', id='videoName')
        if title_elem:
            current_video_title = title_elem.get_text(strip=True)
    
    hidden_video_id = soup.find('input', {'name': 'currentVideoID', 'id': 'currentVideoID'})
    if hidden_video_id and not current_video_id:
        current_video_id = hidden_video_id.get('value')
    
    video_divs = soup.find_all('div', id=re.compile(r'lvwVideos.*_divVideo'))
    
    for video_div in video_divs:
        title, video_id = extract_video_id_and_title(video_div)
        
        if title:
            context_url = base_url if not inferred_year else f"/{inferred_year}/"
            date = extract_date_from_title(title, context_url)
            
            meeting = MeetingMetadata()
            meeting.title = title
            meeting.date = date
            
            if video_id:
                meeting.meeting_url = f"https://civplus.tikiliveapi.com/embed?scheme=embedVod&videoId={video_id}&autoplay=no"
            elif current_video_title and title == current_video_title and current_video_id:
                meeting.meeting_url = f"https://civplus.tikiliveapi.com/embed?scheme=embedVod&videoId={current_video_id}&autoplay=no"
            else:
                print(f"Warning: No video ID found for '{title}'")
                meeting.meeting_url = None
            
            meetings.append(meeting)
    
    return meetings


def should_use_lansdale_extractor(base_url: str) -> bool:
    return 'lansdale.org' in base_url.lower()

