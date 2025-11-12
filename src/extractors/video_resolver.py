"""Video and document URL resolver with yt-dlp verification."""
import re
import asyncio
from typing import Optional, List
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

from ..utils.logger import setup_logger


class VideoURLResolver:
    def __init__(self, browser_manager=None, rate_limiter=None):
        self.logger = setup_logger("video_resolver")
        self.browser_manager = browser_manager
        self.rate_limiter = rate_limiter
        self.http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    async def resolve_url(self, url: str, url_type: str = 'video') -> Optional[str]:
        self.logger.info(f"Resolving {url_type} URL: {url}")
        
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        try:
            if url_type == 'document':
                if await self._verify_document_url(url):
                    return url
                return None
            
            # Try yt-dlp directly
            if await self._verify_with_ytdlp(url):
                self.logger.info(f"✓ yt-dlp can handle: {url}")
                return url
            
            # Try platform-specific resolution
            resolved = await self._platform_specific_resolve(url)
            if resolved and await self._verify_with_ytdlp(resolved):
                self.logger.info(f"✓ Resolved to: {resolved}")
                return resolved
            
            # Try extracting from page
            if self.browser_manager:
                extracted_urls = await self._extract_from_page(url)
                for extracted_url in extracted_urls:
                    if await self._verify_with_ytdlp(extracted_url):
                        self.logger.info(f"✓ Extracted: {extracted_url}")
                        return extracted_url
            
            return None
        except Exception as e:
            self.logger.error(f"Error resolving {url}: {str(e)}")
            return None
    
    async def _platform_specific_resolve(self, url: str) -> Optional[str]:
        """Apply platform-specific URL resolution."""
        url_lower = url.lower()
        
        # YouTube
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return url
        
        # Granicus
        if 'granicus.com' in url_lower:
            return url
        
        # Swagit - add /download suffix
        if 'swagit.com' in url_lower:
            if not url.endswith('/download'):
                return url.rstrip('/') + '/download'
            return url
        
        # Other common video platforms
        if any(platform in url_lower for platform in [
            'video.ibm.com', 'vimeo.com', 'facebook.com', 
            'civicclerk.com', 'audiomack.com', 'champds.com', 'viebit.com'
        ]):
            return url
        
        # Direct media files
        if any(ext in url_lower for ext in ['.mp4', '.m3u8', '.m3u', '.webm', '.mp3', '.wav']):
            return url
        
        return None
    
    async def _extract_from_page(self, url: str) -> List[str]:
        """Extract video URLs from page using browser."""
        extracted_urls = []
        
        if not self.browser_manager:
            return extracted_urls
        
        try:
            page = await self.browser_manager.new_page()
            if not page:
                return extracted_urls
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                html = await page.content()
                
                soup = BeautifulSoup(html, 'lxml')
                
                # Extract from video tags
                for video_tag in soup.find_all('video'):
                    if video_tag.get('src'):
                        extracted_urls.append(urljoin(url, video_tag.get('src')))
                    
                    for source in video_tag.find_all('source'):
                        if source.get('src'):
                            extracted_urls.append(urljoin(url, source.get('src')))
                
                # Extract from iframes
                for iframe in soup.find_all('iframe'):
                    if iframe.get('src'):
                        extracted_urls.append(urljoin(url, iframe.get('src')))
                
                # Extract from scripts
                for script in soup.find_all('script'):
                    if script.string:
                        video_urls = re.findall(
                            r'["\']https?://[^"\']+\.(?:mp4|m3u8|webm|mp3)[^"\']*["\']',
                            script.string
                        )
                        for video_url in video_urls:
                            extracted_urls.append(video_url.strip('"\''))
                
                # Extract from data attributes
                for elem in soup.find_all(attrs={'data-video-url': True}):
                    extracted_urls.append(urljoin(url, elem['data-video-url']))
                
                for elem in soup.find_all(attrs={'data-src': True}):
                    data_src = elem['data-src']
                    if any(ext in data_src.lower() for ext in ['.mp4', '.m3u8', 'video', 'media']):
                        extracted_urls.append(urljoin(url, data_src))
                        
            finally:
                await page.close()
            
        except Exception as e:
            self.logger.error(f"Error extracting from page {url}: {str(e)}")
        
        return extracted_urls
    
    async def _verify_with_ytdlp(self, url: str) -> bool:
        """
        Verify URL works with yt-dlp using --simulate.
        
        Args:
            url: URL to verify
        
        Returns:
            True if yt-dlp can handle the URL
        """
        try:
            process = await asyncio.create_subprocess_exec(
                'yt-dlp',
                '--simulate',
                '--no-warnings',
                '--quiet',
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
            
            if process.returncode == 0:
                return True
            
            # Some URLs work even with certain error messages
            stderr_text = stderr.decode('utf-8', errors='ignore').lower()
            if 'private video' in stderr_text or 'requires authentication' in stderr_text:
                return True
            
            return False
            
        except asyncio.TimeoutError:
            self.logger.warning(f"yt-dlp verification timeout for {url}")
            return False
        except FileNotFoundError:
            self.logger.error("yt-dlp not found. Please install: pip install yt-dlp")
            return False
        except Exception as e:
            self.logger.error(f"yt-dlp verification error for {url}: {str(e)}")
            return False
    
    async def _verify_document_url(self, url: str) -> bool:
        """
        Verify document URL is accessible.
        
        Args:
            url: Document URL to verify
        
        Returns:
            True if document is accessible
        """
        try:
            # Simple HEAD request to check if document is accessible
            response = await self.http_client.head(url, follow_redirects=True, timeout=15.0)
            return response.status_code == 200
            
        except Exception:
            # If HEAD fails, assume URL is valid and let downstream handle it
            return True
    
    async def batch_resolve(self, url_list: List[dict]) -> List[str]:
        """
        Batch resolve multiple URLs with concurrency.
        
        Args:
            url_list: List of dicts with 'url' and 'type' keys
        
        Returns:
            List of successfully resolved URLs
        """
        self.logger.info(f"Starting batch resolution of {len(url_list)} URLs")
        
        tasks = [
            self._resolve_single_item(item)
            for item in url_list
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        resolved = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error resolving {url_list[i].get('url')}: {str(result)}")
            elif result:
                resolved.append(result)
        
        self.logger.info(f"Resolved {len(resolved)}/{len(url_list)} URLs")
        return resolved
    
    async def _resolve_single_item(self, item: dict) -> Optional[str]:
        """Resolve a single URL item."""
        url = item.get('url')
        url_type = item.get('type', 'video')
        
        if not url:
            return None
        
        return await self.resolve_url(url, url_type)
