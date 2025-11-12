"""Bethlehem PA Calendar extractor with month navigation."""
import re
from typing import List
from datetime import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ..date_parser import extract_date_from_text
from ..dom_utils import extract_text_from_element, get_full_url


async def collect_bethlehem_html(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    htmls = []
    detail_urls = set()
    page = None
    
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        months_diff = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
        max_months = max(months_diff + 2, 3)
    else:
        max_months = 12
    
    try:
        page = await browser_manager.new_page()
        
        print("Navigating to Bethlehem calendar...")
        await page.goto(base_url, timeout=90000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        
        html_current = await page.content()
        htmls.append(html_current)
        
        soup = BeautifulSoup(html_current, 'lxml')
        for link in soup.find_all('a', href=re.compile(r'/Calendar/Meetings/')):
            detail_urls.add(link.get('href'))
        
        print(f"Found {len(detail_urls)} meeting links on current page")
        
        print(f"Collecting up to {max_months} months based on date range: {start_date} to {end_date}")
        months_collected = 0
        
        while months_collected < max_months:
            try:
                prev_button = await page.query_selector('img.prevMonth')
                
                if not prev_button:
                    break
                
                parent_link = await prev_button.evaluate_handle('el => el.closest("a")')
                if parent_link:
                    await parent_link.as_element().click()
                    await page.wait_for_timeout(3000)
                    
                    html = await page.content()
                    htmls.append(html)
                    months_collected += 1
                    
                    soup = BeautifulSoup(html, 'lxml')
                    for link in soup.find_all('a', href=re.compile(r'/Calendar/Meetings/')):
                        detail_urls.add(link.get('href'))
                    
                    print(f"Collected Bethlehem month {months_collected}, total links: {len(detail_urls)}")
                else:
                    break
                    
            except Exception as nav_error:
                print(f"Navigation stopped: {nav_error}")
                break
        
        print(f"Collected {len(htmls)} calendar pages, found {len(detail_urls)} meeting detail URLs")
        
        detail_pages_collected = 0
        for detail_path in list(detail_urls):
            try:
                detail_url = f"https://www.bethlehem-pa.gov{detail_path}" if detail_path.startswith('/') else detail_path
                
                print(f"Visiting detail page: {detail_url}")
                await page.goto(detail_url, timeout=60000, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                detail_html = await page.content()
                htmls.append(detail_html)
                detail_pages_collected += 1
                
                print(f"Collected detail page {detail_pages_collected}")
                    
            except Exception as detail_error:
                print(f"Error collecting detail page {detail_path}: {detail_error}")
                continue
        
        print(f"Collected {detail_pages_collected} meeting detail pages from Bethlehem")
        
    except Exception as e:
        print(f"Error collecting Bethlehem HTML: {e}")
    finally:
        if page:
            try:
                await page.close()
            except:
                pass
    
    return htmls


def extract_detail_page_links(soup: BeautifulSoup, base_url: str) -> dict:
    links = {
        'agenda_url': None,
        'minutes_url': None,
        'meeting_url': None
    }
    
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        text = extract_text_from_element(link).strip()
        
        if text == 'Agenda':
            links['agenda_url'] = get_full_url(href, base_url)
        elif text == 'Meeting Minutes: Text':
            links['minutes_url'] = get_full_url(href, base_url)
        elif text == 'Meeting Minutes: Audio':
            links['minutes_url'] = get_full_url(href, base_url)
        elif text == 'Meeting Minutes: Video':
            full_url = get_full_url(href, base_url)
            if 'youtube.com' in full_url or 'youtu.be' in full_url:
                links['meeting_url'] = full_url
        elif text.startswith('00 Agenda') and not links['agenda_url']:
            links['agenda_url'] = get_full_url(href, base_url)
    
    return links


def clean_bethlehem_title(text: str) -> str:
    cleaned = re.sub(r'\s*-\s*\d{1,2}/\d{1,2}/\d{4}.*$', '', text)
    return cleaned.strip()


def extract_meeting_from_cell(cell, base_url: str) -> List[MeetingMetadata]:
    meetings = []
    more_links = cell.find_all('a', href=re.compile(r'/Calendar/Meetings/'))
    
    if not more_links:
        return meetings
    
    meeting_anchors = cell.find_all('a', href=re.compile(r'^#data-'))
    
    for more_link in more_links:
        title = None
        date = None
        
        for anchor in meeting_anchors:
            anchor_text = extract_text_from_element(anchor)
            if anchor_text and len(anchor_text) > 10:
                title = clean_bethlehem_title(anchor_text)
                
                date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', anchor_text)
                if date_match:
                    month, day, year = date_match.groups()
                    date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
        if not date:
            date = extract_date_from_text(extract_text_from_element(cell))
        
        if title and date:
            meeting = MeetingMetadata()
            meeting.title = title
            meeting.date = date
            meeting._detail_page_url = get_full_url(more_link.get('href'), base_url)
            meetings.append(meeting)
    
    return meetings


def extract_bethlehem_meetings(soup: BeautifulSoup, base_url: str) -> List[MeetingMetadata]:
    meetings = []
    
    is_detail_page = soup.find('h5', string=re.compile(r'Background Documents', re.I)) is not None
    
    if is_detail_page:
        detail_links = extract_detail_page_links(soup, base_url)
        
        title_elem = soup.find('h1')
        title = extract_text_from_element(title_elem) if title_elem else None
        
        date_text = soup.get_text()
        date = extract_date_from_text(date_text)
        
        if title and date:
            meeting = MeetingMetadata()
            meeting.title = title
            meeting.date = date
            meeting.agenda_url = detail_links.get('agenda_url')
            meeting.minutes_url = detail_links.get('minutes_url')
            meeting.meeting_url = detail_links.get('meeting_url')
            meetings.append(meeting)
    else:
        for cell in soup.find_all('td'):
            cell_meetings = extract_meeting_from_cell(cell, base_url)
            meetings.extend(cell_meetings)
    
    return meetings


def should_use_bethlehem_extractor(base_url: str) -> bool:
    return 'bethlehem-pa.gov' in base_url.lower()
