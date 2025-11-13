"""Core scraping engine - orchestrates meeting scraping and URL resolution."""
import asyncio
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .browser import BrowserManager
from .stealth import StealthConfig
from .url_resolver import URLResolver
from ..extractors.base_extractor import MeetingExtractor
from ..extractors.site_handlers import needs_special_collection, get_site_htmls
from ..storage.models import ScraperConfig
from ..storage.meeting_models import MeetingOutput, MeetingMetadata
from ..utils.logger import setup_logger
from ..utils.helpers import RateLimiter
from ..utils.error_detector import detect_error_type, ErrorType


class ScraperEngine:
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = setup_logger("scraper_engine")
        self.rate_limiter = RateLimiter(rate=config.rate_limit)
        
        stealth_config = StealthConfig(
            use_proxy=False,
            randomize_viewport=True,
            user_agent_rotation=True
        )
        self.browser_manager = BrowserManager(stealth_config)
        self.extractor = MeetingExtractor()
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
                    
            except Exception as e:
                self.logger.error(f"Error scraping {base_url}: {str(e)}")
                result = MeetingOutput(base_url=base_url, medias=[])
                outputs.append(result)
                
                if on_site_complete:
                    on_site_complete(result, i, len(base_urls))
        
        total = sum(len(o.medias) for o in outputs)
        self.logger.info(f"Scraped {total} meetings from {len(outputs)} sites")
        return outputs
    
    async def _scrape_single_site(self, base_url: str, start_date: str, end_date: str) -> MeetingOutput:
        self.logger.info(f"Scraping: {base_url}")
        
        try:
            await self.rate_limiter.acquire()
            
            if needs_special_collection(base_url):
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
            
            # Try pagination
            additional = await self._scrape_paginated_pages(html, base_url, start_date, end_date)
            meetings.extend(additional)
            
            # Deduplicate
            meetings = self._deduplicate(meetings)
            
            self.logger.info(f"Found {len(meetings)} meetings from {base_url}")
            return MeetingOutput(base_url=base_url, medias=meetings)
            
        except Exception as e:
            self.logger.error(f"Error scraping {base_url}: {str(e)}")
            return MeetingOutput(base_url=base_url, medias=[])
    
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page with smart retry based on error type."""
        max_retries = 2  # 2 retries = 3 total attempts
        
        for attempt in range(max_retries + 1):
            try:
                page = await self.browser_manager.new_page()
                if not page:
                    continue
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
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
                
                # Handle based on error type
                if error_type in (ErrorType.TIMEOUT, ErrorType.NETWORK):
                    # Network/timeout: exponential backoff
                    wait_time = 2 ** (attempt + 1)  # 2s, 4s
                    self.logger.warning(
                        f"⚠️  {error_type.value} on attempt {attempt + 1} for {url} "
                        f"- Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    
                elif error_type in (ErrorType.BOT_DETECTION, ErrorType.CLOUDFLARE):
                    # Bot detection: rotate fingerprint + new context
                    self.logger.warning(
                        f"🤖 {error_type.value} detected on attempt {attempt + 1} for {url} "
                        f"- Rotating fingerprint and retrying..."
                    )
                    await self.browser_manager.recreate_context()
                    # Retry immediately with new fingerprint
                    
                else:
                    # Non-retriable error
                    self.logger.error(f"✗ Non-retriable error for {url}: {error_msg[:200]}")
                    return None
        
        return None
    
    async def _scrape_paginated_pages(self, html: str, base_url: str, start_date: str, end_date: str) -> List[MeetingMetadata]:
        meetings = []
        max_pages = 5
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            pagination_links = []
            
            for selector in ['a[rel="next"]', 'a.next', 'a.pagination-next', 'li.next a']:
                links = soup.select(selector)
                print(f"Links: {links}")
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if full_url not in pagination_links and full_url != base_url:
                            pagination_links.append(full_url)
            
            for i, page_url in enumerate(pagination_links[:max_pages]):
                await self.rate_limiter.acquire()
                page_html = await self._fetch_page(page_url)
                if page_html:
                    page_meetings = self.extractor.extract_meetings_from_page(
                        page_html, base_url, start_date, end_date
                    )
                    meetings.extend(page_meetings)
                    self.logger.info(f"Scraped pagination page {i+1}")
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
