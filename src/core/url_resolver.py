"""URL resolver for videos, audio, and documents with yt-dlp verification."""
import re
import asyncio
from typing import Optional, List
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

from ..utils.logger import setup_logger


class URLResolver:
    def __init__(self, browser_manager=None, rate_limiter=None):
        self.logger = setup_logger("url_resolver")
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
    
    async def _extract_from_page(self, url: str, max_retries: int = 1) -> List[str]:
        """Extract video URLs from page using browser with retry logic."""
        extracted_urls = []
        
        if not self.browser_manager:
            return extracted_urls
        
        for attempt in range(max_retries + 1):
            page = None
            try:
                page = await self.browser_manager.new_page()
                if not page:
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                        continue
                    return extracted_urls
                
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                html = await page.content()
                
                soup = BeautifulSoup(html, 'lxml')
                
                for video_tag in soup.find_all('video'):
                    if video_tag.get('src'):
                        extracted_urls.append(urljoin(url, video_tag.get('src')))
                    for source in video_tag.find_all('source'):
                        if source.get('src'):
                            extracted_urls.append(urljoin(url, source.get('src')))
                
                for iframe in soup.find_all('iframe'):
                    if iframe.get('src'):
                        extracted_urls.append(urljoin(url, iframe.get('src')))
                
                for script in soup.find_all('script'):
                    if script.string:
                        video_urls = re.findall(
                            r'["\']https?://[^"\']+\.(?:mp4|m3u8|webm|mp3)[^"\']*["\']',
                            script.string
                        )
                        for video_url in video_urls:
                            extracted_urls.append(video_url.strip('"\''))
                
                for elem in soup.find_all(attrs={'data-video-url': True}):
                    extracted_urls.append(urljoin(url, elem['data-video-url']))
                
                for elem in soup.find_all(attrs={'data-src': True}):
                    data_src = elem['data-src']
                    if any(ext in data_src.lower() for ext in ['.mp4', '.m3u8', 'video', 'media']):
                        extracted_urls.append(urljoin(url, data_src))
                
                if page:
                    await page.close()
                return extracted_urls
                
            except Exception as e:
                if page:
                    await page.close()
                
                error_msg = str(e).lower()
                is_network_error = any(err in error_msg for err in [
                    'timeout', 'connection', 'network', 'err_name_not_resolved'
                ])
                
                if is_network_error and attempt < max_retries:
                    self.logger.info(f"Network error extracting {url}, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2)
                    continue
                
                if attempt == max_retries:
                    self.logger.warning(f"Failed to extract from {url} after {max_retries + 1} attempts")
        
        return extracted_urls
    
    async def _verify_with_ytdlp(self, url: str, max_retries: int = 2) -> bool:
        """
        Verify URL works with yt-dlp using --simulate with retry logic.
        
        Args:
            url: URL to verify
            max_retries: Maximum retry attempts for network issues
        
        Returns:
            True if yt-dlp can handle the URL
        """
        for attempt in range(max_retries + 1):
            process = None
            try:
                process = await asyncio.create_subprocess_exec(
                    'yt-dlp',
                    '--simulate',
                    '--no-warnings',
                    '--quiet',
                    '--socket-timeout', '15',
                    url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45.0)
                
                if process.returncode == 0:
                    return True
                
                stderr_text = stderr.decode('utf-8', errors='ignore').lower()
                if 'private video' in stderr_text or 'requires authentication' in stderr_text:
                    return True
                
                if 'unable to download' in stderr_text or 'http error' in stderr_text:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        self.logger.info(f"Network error for {url}, retry {attempt + 1}/{max_retries} in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                
                return False
                
            except asyncio.TimeoutError:
                if process:
                    try:
                        process.kill()
                        await process.wait()
                    except:
                        pass
                if attempt < max_retries:
                    self.logger.info(f"Timeout for {url}, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2)
                    continue
                self.logger.warning(f"yt-dlp timeout after {max_retries + 1} attempts: {url}")
                return False
            except FileNotFoundError:
                self.logger.error("yt-dlp not found. Please install: pip install yt-dlp")
                return False
            except Exception as e:
                if process:
                    try:
                        process.kill()
                        await process.wait()
                    except:
                        pass
                if attempt < max_retries:
                    self.logger.info(f"Error for {url}, retry {attempt + 1}/{max_retries}: {str(e)[:100]}")
                    await asyncio.sleep(2)
                    continue
                self.logger.error(f"yt-dlp error after {max_retries + 1} attempts: {str(e)[:100]}")
                return False
        
        return False
    
    async def _verify_document_url(self, url: str, max_retries: int = 2) -> bool:
        """
        Verify document URL is accessible with retry logic.
        
        Args:
            url: Document URL to verify
            max_retries: Maximum retry attempts
        
        Returns:
            True if document is accessible
        """
        for attempt in range(max_retries + 1):
            try:
                response = await self.http_client.head(url, follow_redirects=True, timeout=15.0)
                return response.status_code == 200
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                if attempt < max_retries:
                    wait_time = 1 + attempt
                    self.logger.info(f"Network error for document {url}, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    continue
                self.logger.warning(f"Document verification failed after retries: {url}")
                return True
            except Exception:
                return True
        
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
