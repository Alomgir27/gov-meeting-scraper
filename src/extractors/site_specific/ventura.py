"""Ventura CivicPlus AgendaCenter extractor with year navigation."""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup

from ...storage.meeting_models import MeetingMetadata
from ..date_parser import extract_date_from_text
from ..dom_utils import extract_text_from_element, find_links_in_element, get_full_url, classify_link_type


async def collect_ventura_html(browser_manager, base_url: str, start_date: str = None, end_date: str = None) -> List[str]:
    htmls = []
    page = None
    
    target_years = set()
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        for year in range(start_dt.year, end_dt.year + 1):
            target_years.add(str(year))
        print(f"Target years for Ventura: {sorted(target_years)}")
    
    try:
        page = await browser_manager.new_page()
        
        await page.goto(base_url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        html_current = await page.content()
        htmls.append(html_current)
        
        year_links = await page.query_selector_all('a[id^="a1"]')
        
        for year_link in year_links:
            try:
                link_id = await year_link.get_attribute('id')
                link_text = await year_link.text_content()
                
                if link_id and link_text:
                    link_text = link_text.strip()
                    
                    if target_years and link_text not in target_years:
                        print(f"Skipping year link: {link_text} (not in target range)")
                        continue
                    
                    print(f"Clicking year link: {link_text} ({link_id})")
                    await year_link.click()
                    await page.wait_for_timeout(5000)
                    
                    html = await page.content()
                    htmls.append(html)
            except Exception as link_error:
                print(f"Error clicking year link: {link_error}")
                continue
        
        print(f"Collected {len(htmls)} HTML pages from Ventura")
        
    except Exception as e:
        print(f"Error collecting Ventura HTML: {e}")
    finally:
        if page:
            try:
                await page.close()
            except:
                pass
    
    return htmls


def extract_date_from_row(row) -> str:
    for strong in row.find_all('strong'):
        date_text = extract_text_from_element(strong)
        date = extract_date_from_text(date_text)
        if date:
            return date
    return None


def extract_title_from_row(row) -> str:
    for p in row.find_all('p'):
        for a in p.find_all('a', href=True):
            title = extract_text_from_element(a)
            if len(title) > 10:
                return title
    return None


def extract_ventura_meetings(soup: BeautifulSoup, base_url: str) -> List[MeetingMetadata]:
    meetings = []
    
    for row in soup.find_all('tr', class_='catAgendaRow'):
        date = extract_date_from_row(row)
        title = extract_title_from_row(row)
        
        if not date or not title:
            continue
        
        meeting = MeetingMetadata()
        meeting.date = date
        meeting.title = title
        
        for link in find_links_in_element(row):
            href = link.get('href')
            text = extract_text_from_element(link)
            link_type = classify_link_type(href, text)
            
            if link_type == 'video' and not meeting.meeting_url:
                meeting.meeting_url = get_full_url(href, base_url)
            elif link_type == 'agenda' and not meeting.agenda_url:
                meeting.agenda_url = get_full_url(href, base_url)
            elif link_type == 'minutes' and not meeting.minutes_url:
                meeting.minutes_url = get_full_url(href, base_url)
        
        meetings.append(meeting)
    
    return meetings


def should_use_ventura_extractor(base_url: str) -> bool:
    return 'cityofventura.ca.gov' in base_url.lower()
