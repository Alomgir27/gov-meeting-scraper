"""Core scraping engine - orchestrates meeting scraping and URL resolution."""
import asyncio
import re
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .browser import BrowserManager
from .stealth import StealthConfig
from .url_resolver import URLResolver
from ..extractors.base_extractor import MeetingExtractor
from ..extractors.site_handlers import needs_special_collection, get_site_htmls
from ..extractors.detail_navigator import should_navigate_to_detail, extract_from_detail_page
from ..extractors.calendar_navigator import get_all_year_pages
from ..extractors.js_site_detector import is_js_heavy_site, wait_for_js_content
from ..storage.models import ScraperConfig
from ..storage.meeting_models import MeetingOutput, MeetingMetadata
from ..utils.logger import setup_logger
from ..utils.helpers import RateLimiter
from ..utils.error_detector import detect_error_type, ErrorType
from ..utils.patterns import PAGINATION_KEYWORDS, PAGINATION_SELECTORS


class ScraperEngine:
    def __init__(self, config: ScraperConfig, use_universal_only: bool = False):
        self.config = config
        self.logger = setup_logger("scraper_engine")
        self.rate_limiter = RateLimiter(rate=config.rate_limit)
        self.use_universal_only = use_universal_only
        self.visited_urls: set = set()
        
        stealth_config = StealthConfig(
            use_proxy=False,
            randomize_viewport=True,
            user_agent_rotation=True
        )
        self.browser_manager = BrowserManager(stealth_config)
        self.extractor = MeetingExtractor(use_universal_only=use_universal_only)
        self.url_resolver = None
        
    async def __aenter__(self):
        await self.browser_manager.start()
        self.url_resolver = URLResolver(self.browser_manager, rate_limiter=self.rate_limiter)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.url_resolver:
            await self.url_resolver.close()
        await self.browser_manager.close()
    
    async def scrape_meetings(self, base_urls: List[str], start_date: str, end_date: str, 
                             on_site_complete=None) -> List[MeetingOutput]:
        if not self.extractor:
            raise ValueError("Extractor not initialized")
        
        self.logger.info(f"Scraping {len(base_urls)} URLs sequentially (date range: {start_date} to {end_date})")
        
        outputs = []
        for i, base_url in enumerate(base_urls, 1):
            self.logger.info(f"[{i}/{len(base_urls)}] Processing: {base_url}")
            try:
                result = await self._scrape_single_site(base_url, start_date, end_date)
                outputs.append(result)
                
                if on_site_complete:
                    on_site_complete(result, i, len(base_urls))
                else:
                    self.logger.info(f"✓ Completed [{i}/{len(base_urls)}]: {len(result.medias)} meetings from {base_url}")
                    
            except Exception as e:
                self.logger.error(f"Error scraping {base_url}: {str(e)}")
                result = MeetingOutput(base_url=base_url, medias=[])
                outputs.append(result)
                
                if on_site_complete:
                    on_site_complete(result, i, len(base_urls))
        
        total = sum(len(o.medias) for o in outputs)
        self.logger.info(f"Scraped {total} meetings from {len(outputs)} sites")
        return outputs
    
    async def _enhance_with_detail_pages(self, meetings: List[MeetingMetadata], base_url: str) -> List[MeetingMetadata]:
        """Navigate to detail pages to extract additional links."""
        enhanced_meetings = []
        
        for meeting in meetings:
            existing_links = {
                'agenda': meeting.agenda_url,
                'minutes': meeting.minutes_url,
                'video': meeting.meeting_url
            }
            
            has_all_links = all([meeting.agenda_url, meeting.minutes_url, meeting.meeting_url])
            if has_all_links:
                enhanced_meetings.append(meeting)
                continue
            
            detail_url = None
            if hasattr(meeting, '_container') and meeting._container:
                detail_url = await should_navigate_to_detail(meeting._container, existing_links)
            
            if detail_url:
                full_detail_url = urljoin(base_url, detail_url)
                self.logger.debug(f"Navigating to detail page: {full_detail_url}")
                
                try:
                    await self.rate_limiter.acquire()
                    detail_links = await extract_from_detail_page(
                        self.browser_manager, full_detail_url, base_url
                    )
                    
                    if not meeting.agenda_url and detail_links.get('agenda'):
                        meeting.agenda_url = detail_links['agenda']
                    if not meeting.minutes_url and detail_links.get('minutes'):
                        meeting.minutes_url = detail_links['minutes']
                    if not meeting.meeting_url and detail_links.get('video'):
                        meeting.meeting_url = detail_links['video']
                    
                    self.logger.info(f"Enhanced meeting with detail page data")
                except Exception as e:
                    self.logger.warning(f"Failed to extract from detail page: {str(e)}")
            
            enhanced_meetings.append(meeting)
        
        return enhanced_meetings
    
    async def _scrape_single_site(self, base_url: str, start_date: str, end_date: str) -> MeetingOutput:
        self.logger.info(f"Scraping: {base_url}")
        
        try:
            await self.rate_limiter.acquire()
            
            if not self.use_universal_only and needs_special_collection(base_url):
                htmls = await get_site_htmls(self.browser_manager, base_url, start_date, end_date)
                all_meetings = []
                for html in htmls:
                    meetings = self.extractor.extract_meetings(html, base_url, start_date, end_date)
                    all_meetings.extend(meetings)
                all_meetings = self._deduplicate(all_meetings)
                self.logger.info(f"Found {len(all_meetings)} meetings from {base_url}")
                return MeetingOutput(base_url=base_url, medias=all_meetings)
            
            html = await self._fetch_page(base_url)
            if not html:
                self.logger.warning(f"Could not fetch {base_url}")
                return MeetingOutput(base_url=base_url, medias=[])
            
            meetings = self.extractor.extract_meetings(html, base_url, start_date, end_date)
            
            if self.use_universal_only:
                start_year = int(start_date.split('-')[0])
                end_year = int(end_date.split('-')[0])
                self.logger.info(f"Checking for year navigation buttons ({start_year}-{end_year})...")
                year_htmls = await get_all_year_pages(self.browser_manager, base_url, start_year, end_year)
                
                if len(year_htmls) > 1:
                    self.logger.info(f"Found {len(year_htmls)} year pages, extracting from each...")
                    for year_html in year_htmls[1:]:
                        year_meetings = self.extractor.extract_meetings(year_html, base_url, start_date, end_date)
                        meetings.extend(year_meetings)
            
            paginated_meetings = await self._scrape_paginated_pages(html, base_url, start_date, end_date)
            if paginated_meetings:
                meetings.extend(paginated_meetings)
            
            meetings = self._deduplicate(meetings)
            
            if self.use_universal_only and meetings:
                self.logger.info(f"Enhancing {len(meetings)} meetings with detail page navigation...")
                meetings = await self._enhance_with_detail_pages(meetings, base_url)
            
            self.logger.info(f"Found {len(meetings)} meetings from {base_url}")
            return MeetingOutput(base_url=base_url, medias=meetings)
            
        except Exception as e:
            self.logger.error(f"Error scraping {base_url}: {str(e)}")
            return MeetingOutput(base_url=base_url, medias=[])
    
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page with smart retry based on error type."""
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                page = await self.browser_manager.new_page()
                if not page:
                    continue
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    initial_html = await page.content()
                    
                    if is_js_heavy_site(initial_html, url):
                        self.logger.info(f"JavaScript-heavy site detected, waiting for content...")
                        await wait_for_js_content(page, url)
                    
                    html = await page.content()
                    
                    if attempt > 0:
                        self.logger.info(f"✓ Success on attempt {attempt + 1} for {url}")
                    return html
                    
                finally:
                    await page.close()
                    
            except Exception as e:
                error_msg = str(e)
                error_type = detect_error_type(error_msg)
                
                is_last_attempt = (attempt == max_retries)
                
                if is_last_attempt:
                    self.logger.error(f"✗ All attempts failed for {url}: {error_msg[:200]}")
                    return None
                
                if error_type in (ErrorType.TIMEOUT, ErrorType.NETWORK):
                    wait_time = 2 ** (attempt + 1)
                    self.logger.warning(
                        f"⚠️  {error_type.value} on attempt {attempt + 1} for {url} "
                        f"- Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    
                elif error_type in (ErrorType.BOT_DETECTION, ErrorType.CLOUDFLARE):
                    self.logger.warning(
                        f"🤖 {error_type.value} detected on attempt {attempt + 1} for {url} "
                        f"- Rotating fingerprint and retrying..."
                    )
                    await self.browser_manager.recreate_context()
                    
                else:
                    self.logger.error(f"✗ Non-retriable error for {url}: {error_msg[:200]}")
                    return None
        
        return None
    
    async def _scrape_paginated_pages(self, html: str, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
        meetings = []
        max_pages = 10
        visited_urls = {base_url}
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            pagination_links = []
            
            # Pattern 1: Look for pagination by text
            for link in soup.find_all('a', href=True):
                text = link.get_text(' ', strip=True).lower()
                href = link.get('href')
                
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                
                if any(kw in text for kw in PAGINATION_KEYWORDS):
                    full_url = urljoin(base_url, href)
                    if full_url not in visited_urls:
                        pagination_links.append(full_url)
                        visited_urls.add(full_url)
                        break
                
                # Pattern 1b: Numbered pages (1, 2, 3, etc)
                if re.match(r'^\d+$', text):
                    full_url = urljoin(base_url, href)
                    if full_url not in visited_urls:
                        pagination_links.append(full_url)
                        visited_urls.add(full_url)
                
                # Pattern 1c: "Page X" links
                if re.search(r'\bpage\s*\d+\b', text, re.IGNORECASE):
                    full_url = urljoin(base_url, href)
                    if full_url not in visited_urls:
                        pagination_links.append(full_url)
                        visited_urls.add(full_url)
            
            for selector in PAGINATION_SELECTORS:
                for link in soup.select(selector):
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if full_url not in visited_urls and full_url != base_url:
                            pagination_links.append(full_url)
                            visited_urls.add(full_url)
                            break
            
            pagination_links = pagination_links[:max_pages]
            
            if pagination_links:
                self.logger.info(f"Found {len(pagination_links)} pagination links")
            
            for i, page_url in enumerate(pagination_links):
                await self.rate_limiter.acquire()
                page_html = await self._fetch_page(page_url)
                if page_html:
                    page_meetings = self.extractor.extract_meetings(
                        page_html, base_url, start_date, end_date
                    )
                    meetings.extend(page_meetings)
                    self.logger.info(f"Scraped pagination page {i+1}: {len(page_meetings)} meetings")
        except Exception as e:
            self.logger.warning(f"Error scraping paginated pages: {str(e)}")
        
        return meetings
    
    def _deduplicate(self, meetings: List[MeetingMetadata]) -> List[MeetingMetadata]:
        seen_dict = {}
        
        for meeting in meetings:
            key = (meeting.date, meeting.title)
            
            if key in seen_dict:
                existing = seen_dict[key]
                if meeting.meeting_url and not existing.meeting_url:
                    existing.meeting_url = meeting.meeting_url
                if meeting.agenda_url and not existing.agenda_url:
                    existing.agenda_url = meeting.agenda_url
                if meeting.minutes_url and not existing.minutes_url:
                    existing.minutes_url = meeting.minutes_url
            else:
                seen_dict[key] = meeting
        
        return list(seen_dict.values())
    
    async def resolve_urls(self, url_list: List[dict]) -> List[str]:
        if not self.url_resolver:
            raise ValueError("URL resolver not initialized")
        return await self.url_resolver.batch_resolve(url_list)
