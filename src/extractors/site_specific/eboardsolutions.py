"""EBoardSolutions special collection and extraction with advanced bot detection avoidance."""
import random
from typing import List
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ..date_parser import extract_date_from_text
from ..dom_utils import extract_text_from_element


async def simulate_human_behavior(page):
    """Simulate human-like interactions to avoid bot detection."""
    try:
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await page.wait_for_timeout(random.randint(500, 1500))
        
        await page.mouse.move(random.randint(200, 600), random.randint(200, 600))
        await page.wait_for_timeout(random.randint(300, 800))
        
        await page.evaluate("""
            () => {
                window.scrollTo(0, Math.random() * 300);
            }
        """)
        await page.wait_for_timeout(random.randint(1000, 2000))
        
        await page.evaluate("""
            () => {
                window.scrollTo(0, 0);
            }
        """)
        await page.wait_for_timeout(random.randint(500, 1000))
    except:
        pass


async def check_for_incapsula_block(page) -> bool:
    """Check if page is blocked by Incapsula."""
    try:
        html = await page.content()
        if 'incapsula' in html.lower():
            print("  ⚠️ Detected Incapsula security check")
            return True
        
        if 'additional security check' in html.lower():
            print("  ⚠️ Incapsula challenge page detected")
            return True
            
        iframe = await page.query_selector('iframe[src*="Incapsula"]')
        if iframe:
            print("  ⚠️ Detected Incapsula iframe")
            return True
        
        if len(html) < 5000:
            print(f"  ⚠️ Insufficient content ({len(html)} chars)")
            return True
            
        return False
    except:
        return True


async def wait_for_incapsula_challenge(page, timeout: int = 30000):
    """Wait for Incapsula JavaScript challenge to complete."""
    print("  ⏳ Waiting for challenge (max 15s)...")
    start_time = 0
    max_wait = timeout / 1000
    
    while start_time < max_wait:
        await page.wait_for_timeout(2000)
        start_time += 2
        
        try:
            html = await page.content()
            
            if 'ContentPlaceHolder1_MeetingGrid' in html:
                print(f"  ✅ Challenge passed after {start_time}s!")
                return True
            
            if 'incapsula' in html.lower() or 'additional security check' in html.lower():
                if start_time % 4 == 0:
                    print(f"  ⏳ Still waiting... ({start_time}s)")
                continue
            
            if len(html) > 10000:
                print(f"  ✅ Page loaded ({len(html)} chars)")
                return True
                
        except Exception as e:
            print(f"  ⚠️ Check error: {str(e)[:50]}")
            
    print(f"  ❌ Timeout after {max_wait}s")
    return False


async def collect_eboardsolutions_html(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    """Collect HTML from EBoardSolutions with advanced bot detection avoidance."""
    htmls = []
    max_retries = 2
    
    for attempt in range(max_retries):
        page = None
        try:
            if attempt > 0:
                print(f"  🔄 Retry attempt {attempt + 1}/{max_retries}")
                await browser_manager.recreate_context()
                import asyncio
                await asyncio.sleep(random.randint(2, 4))
            
            page = await browser_manager.new_page(allow_resources=True)
            
            print("  🌐 Navigating to EBoardSolutions...")
            await page.goto(base_url, timeout=60000, wait_until='domcontentloaded')
            
            print("  ⏳ Initial wait for page load...")
            await page.wait_for_timeout(random.randint(2000, 3000))
            
            if await check_for_incapsula_block(page):
                print("  🔐 Incapsula detected, attempting quick pass...")
                challenge_passed = await wait_for_incapsula_challenge(page, timeout=15000)
                
                if not challenge_passed:
                    if attempt < max_retries - 1:
                        print("  🔄 Quick attempt failed, will retry once...")
                        await page.close()
                        continue
                    else:
                        print("  ❌ Site protected by Incapsula - cannot bypass")
                        print("  💡 Tip: Requires residential IP or manual access")
                        await page.close()
                        return htmls
            
            print("  🎯 Simulating human behavior...")
            await simulate_human_behavior(page)
            
            print("  🔍 Waiting for meeting grid...")
            try:
                await page.wait_for_selector('#ContentPlaceHolder1_MeetingGrid tbody tr', timeout=20000)
                print("  ✅ Meeting grid found!")
                await page.wait_for_timeout(random.randint(2000, 4000))
            except Exception as e:
                print(f"  ⚠️ Grid selector timeout: {str(e)[:100]}")
                if attempt < max_retries - 1:
                    await page.close()
                    continue
            
            await page.evaluate("""
                () => {
                    const grid = document.getElementById('ContentPlaceHolder1_MeetingGrid');
                    if (grid) {
                        grid.scrollIntoView({behavior: 'smooth'});
                    }
                }
            """)
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            html = await page.content()
            
            if await check_for_incapsula_block(page):
                if attempt < max_retries - 1:
                    print("  🔄 Content check failed, retrying...")
                    await page.close()
                    continue
            
            htmls.append(html)
            print(f"  ✅ Successfully collected HTML ({len(html):,} chars)")
            
            await page.close()
            break
            
        except Exception as e:
            print(f"  ❌ Error on attempt {attempt + 1}: {str(e)[:200]}")
            if page:
                try:
                    await page.close()
                except:
                    pass
            
            if attempt < max_retries - 1:
                await page.wait_for_timeout(random.randint(3000, 5000))
            else:
                print("  ❌ All retry attempts exhausted")
    
    return htmls


def extract_site_id_from_url(base_url: str) -> str:
    """Extract site ID from EBoardSolutions URL."""
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query)
    return params.get('S', [''])[0]


def extract_eboardsolutions_meetings(soup: BeautifulSoup, base_url: str) -> List[MeetingMetadata]:
    """Extract meetings from EBoardSolutions HTML."""
    meetings = []
    site_id = extract_site_id_from_url(base_url)
    base_domain = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
    
    meeting_table = soup.find('table', id='ContentPlaceHolder1_MeetingGrid')
    if not meeting_table:
        return meetings
    
    tbody = meeting_table.find('tbody')
    if not tbody:
        return meetings
    
    for row in tbody.find_all('tr', recursive=False):
        try:
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
            
            date_col = cols[0]
            title_col = cols[1]
            
            date_span = date_col.find('span')
            if not date_span:
                continue
            date_text = extract_text_from_element(date_span)
            date = extract_date_from_text(date_text)
            
            title_link = title_col.find('a')
            if not title_link:
                continue
            title = extract_text_from_element(title_link)
            
            onclick_attr = title_link.get('onclick', '')
            if 'ViewMeeting' in onclick_attr:
                import re
                params = re.findall(r'"([^"]*)"', onclick_attr)
                if len(params) >= 2:
                    meeting_id = params[1]
                    meeting_url = f"{base_domain}/SB_Meetings/SB_MeetingDetail.aspx?S={site_id}&MID={meeting_id}"
                else:
                    meeting_url = None
            else:
                meeting_url = None
            
            if date and title:
                meeting = MeetingMetadata()
                meeting.date = date
                meeting.title = title
                meeting.agenda_url = meeting_url
                meetings.append(meeting)
                
        except Exception as e:
            print(f"Error extracting EBoardSolutions meeting row: {str(e)[:100]}")
            continue
    
    return meetings


def should_use_eboardsolutions_extractor(base_url: str) -> bool:
    return 'eboardsolutions.com' in base_url.lower()

