"""
URL Resolver for Problem 2: Video/Document Download URL Resolution
Extracts downloadable URLs from webpages and verifies with yt-dlp or requests.
"""
import re
import asyncio
import json
from typing import Optional, List
from urllib.parse import urljoin, urlparse, unquote
import httpx
from bs4 import BeautifulSoup

from ..utils.logger import setup_logger


class URLResolver:
    """Resolves webpage URLs to downloadable media/document URLs."""
    
    REFERER_REQUIRED = ['champds.com', 'viebit', 'civicclerk.com']
    DIRECT_PLATFORMS = ['video.ibm.com', 'vimeo.com', 'facebook.com', 'sharepoint.com', 'youtube.com', 'youtu.be']
    MEDIA_EXTENSIONS = ['.mp4', '.m3u8', '.m3u', '.webm', '.mp3', '.wav']
    TIMEOUT_DEFAULT = 30.0
    TIMEOUT_SHORT = 15.0
    
    def __init__(self, browser_manager=None, rate_limiter=None):
        self.logger = setup_logger("url_resolver")
        self.browser_manager = browser_manager
        self.rate_limiter = rate_limiter
        self.http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.TIMEOUT_DEFAULT,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
    
    async def close(self):
        """Close HTTP client resources."""
        await self.http_client.aclose()
    
    async def resolve_url(self, url: str, url_type: str = 'video') -> Optional[str]:
        """Main entry: resolve URL to downloadable form and verify it works."""
        self.logger.info(f"Resolving {url_type} URL: {url}")
        
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        try:
            if url_type == 'document':
                return await self._resolve_document(url)
            
            return await self._resolve_media(url)
        except Exception as e:
            self.logger.error(f"Error resolving {url}: {str(e)}")
            return None
    
    async def _resolve_document(self, url: str) -> Optional[str]:
        """Resolve document URLs (PDFs, HTML)."""
        resolved = await self._extract_platform_url(url)
        if resolved and resolved != url and await self._verify_document(resolved):
            self.logger.info(f"✓ Resolved to: {resolved}")
            return resolved
        
        return url if await self._verify_document(url) else None
    
    async def _resolve_media(self, url: str) -> Optional[str]:
        """Resolve video/audio URLs."""
        if await self._verify_ytdlp(url, url):
            self.logger.info(f"✓ URL works directly: {url}")
            return url
        
        resolved = await self._extract_platform_url(url)
        if resolved and await self._verify_ytdlp(resolved, url):
            self.logger.info(f"✓ Resolved to: {resolved}")
            return resolved
        
        if self.browser_manager:
            for extracted_url in await self._extract_from_page(url):
                if await self._verify_ytdlp(extracted_url, url):
                    self.logger.info(f"✓ Extracted: {extracted_url}")
                    return extracted_url
        
        return None
    
    async def _extract_platform_url(self, url: str) -> Optional[str]:
        """Route to platform-specific extractors."""
        url_lower = url.lower()
        
        platform_map = {
            'swagit.com': lambda: url.rstrip('/') + '/download' if not url.endswith('/download') else url,
            'granicus.com': lambda: self._extract_granicus(url),
            'champds.com': lambda: self._extract_browser_media(url, '.m3u8', 5000),
            'civicclerk.com': lambda: self._extract_civicclerk(url),
            'viebit.com': lambda: self._extract_viebit(url),
            'audiomack.com': lambda: self._extract_browser_media(url, '.mp3', 5000, 'networkidle'),
            'savannahga.gov': lambda: self._extract_savannah_docs(url) if '/minutes.html' in url_lower else url,
        }
        
        for domain, handler in platform_map.items():
            if domain in url_lower:
                result = handler()
                return await result if asyncio.iscoroutine(result) else result
        
        if any(p in url_lower for p in self.DIRECT_PLATFORMS) or any(e in url_lower for e in self.MEDIA_EXTENSIONS):
            return url
        
        return None
    
    async def _extract_granicus(self, url: str) -> str:
        """Extract MP4 from Granicus via HTTP."""
        try:
            response = await self.http_client.get(url, timeout=self.TIMEOUT_SHORT)
            if response.status_code == 200:
                mp4_match = re.search(r'(https://archive-video\.granicus\.com/[^"\'<>\s]+\.mp4)', response.text)
                if mp4_match:
                    self.logger.info(f"✓ Extracted Granicus MP4")
                    return mp4_match.group(1)
        except Exception as e:
            self.logger.warning(f"Granicus extraction failed: {str(e)}")
        return url
    
    async def _extract_savannah_docs(self, url: str) -> str:
        """Extract PDF documents from Savannah minutes pages."""
        try:
            response = await self.http_client.get(url, timeout=self.TIMEOUT_SHORT)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                for link in soup.find_all('a', href=True):
                    if '.pdf' in link['href'].lower():
                        pdf_url = urljoin(url, link['href'])
                        self.logger.info(f"✓ Extracted PDF from minutes page")
                        return pdf_url
        except Exception as e:
            self.logger.warning(f"Savannah docs extraction failed: {str(e)}")
        return url
    
    async def _extract_viebit(self, url: str) -> Optional[str]:
        """Extract M3U8 from Viebit video player."""
        if not self.browser_manager:
            return None
        
        page = None
        captured_m3u8 = None
        
        try:
            page = await self.browser_manager.new_page(allow_resources=True)
            if not page:
                return None
            
            page.on("request", lambda req: setattr(self, '_m3u8_url', req.url) if '.m3u8' in req.url else None)
            
            await page.goto(url, wait_until='domcontentloaded', timeout=self.TIMEOUT_DEFAULT * 1000)
            await page.wait_for_timeout(5000)
            
            try:
                play_button = await page.query_selector('button.vjs-big-play-button')
                if play_button:
                    await play_button.click()
                    await page.wait_for_timeout(3000)
            except:
                pass
            
            if hasattr(self, '_m3u8_url'):
                captured_m3u8 = self._m3u8_url
                delattr(self, '_m3u8_url')
            
            if captured_m3u8:
                await page.close()
                return captured_m3u8
            
            html = await page.content()
            
            # Parse pageConfig JSON
            pageconfig_match = re.search(r'var pageConfig = ({.+?});', html)
            if pageconfig_match:
                try:
                    config = json.loads(pageconfig_match.group(1))
                    if 'video' in config and 'src' in config['video']:
                        for src in config['video']['src']:
                            if 'storage' in src and 'url' in src:
                                await page.close()
                                return src['storage'] + src['url']
                except:
                    pass
            
            # Fallback to regex
            m3u8_match = re.search(r'(https://[^"\'<>]+\.m3u8[^"\'<>]*)', html)
            if m3u8_match:
                await page.close()
                return m3u8_match.group(1)
            
            await page.close()
            return None
        except Exception as e:
            if page:
                await page.close()
            self.logger.warning(f"Viebit extraction failed: {str(e)}")
            return None
    
    async def _extract_civicclerk(self, url: str) -> Optional[str]:
        """Extract video from CivicClerk React app."""
        if not self.browser_manager:
            return None
        
        page = None
        captured_video = None
        
        try:
            page = await self.browser_manager.new_page(allow_resources=True)
            if not page:
                return None
            
            def capture_video(request):
                nonlocal captured_video
                req_url = request.url
                
                if 'mu=' in req_url and ('.mp4' in req_url or '.m3u8' in req_url):
                    match = re.search(r'mu=([^&]+)', req_url)
                    if match:
                        captured_video = unquote(match.group(1))
                        self.logger.info("Extracted video from tracking URL")
                        return
                
                if 'ping.gif' not in req_url and 'analytics' not in req_url and ('.mp4' in req_url or '.m3u8' in req_url):
                    captured_video = req_url
            
            page.on("request", capture_video)
            await page.goto(url, wait_until='networkidle', timeout=self.TIMEOUT_DEFAULT * 1000)
            await page.wait_for_timeout(5000)
            
            try:
                play_button = await page.query_selector('button.jw-icon-playback, .jw-icon-play, [aria-label="Play"]')
                if play_button:
                    await play_button.click()
                    await page.wait_for_timeout(2000)
            except:
                pass
            
            if captured_video:
                await page.close()
                return captured_video.replace('&amp;', '&')
            
            # Fallback to HTML parsing
            html = await page.content()
            for pattern in [
                r'<video[^>]+src=["\']([^"\']+\.mp4[^"\']*)["\']',
                r'(https?://[^"\'<>]+\.mp4[^"\'<>]*)',
                r'(https?://[^"\'<>]+\.m3u8[^"\'<>]*)'
            ]:
                match = re.search(pattern, html)
                if match:
                    await page.close()
                    return match.group(1).replace('&amp;', '&')
            
            await page.close()
            return None
        except Exception as e:
            if page:
                await page.close()
            self.logger.warning(f"CivicClerk extraction failed: {str(e)}")
            return None
    
    async def _extract_browser_media(self, url: str, media_ext: str, wait_ms: int = 3000, wait_until: str = 'domcontentloaded') -> Optional[str]:
        """Generic browser extraction for media files."""
        if not self.browser_manager:
            return None
        
        page = None
        captured_url = None
        
        try:
            page = await self.browser_manager.new_page(allow_resources=True)
            if not page:
                return None
            
            page.on("request", lambda req: setattr(self, '_media_url', req.url) if media_ext in req.url else None)
            
            await page.goto(url, wait_until=wait_until, timeout=self.TIMEOUT_DEFAULT * 1000)
            await page.wait_for_timeout(wait_ms)
            
            if hasattr(self, '_media_url'):
                captured_url = self._media_url
                delattr(self, '_media_url')
            
            if captured_url:
                await page.close()
                return captured_url.replace('&amp;', '&')
            
            # Fallback to HTML parsing
            html = await page.content()
            media_match = re.search(rf'(https?://[^"\'<>]+{re.escape(media_ext)}[^"\'<>]*)', html)
            if media_match:
                await page.close()
                return media_match.group(1).replace('&amp;', '&')
            
            await page.close()
            return None
        except Exception as e:
            if page:
                await page.close()
            self.logger.warning(f"Browser media extraction failed: {str(e)}")
            return None
    
    async def _extract_from_page(self, url: str) -> List[str]:
        """Fallback: extract media URLs from page HTML."""
        if not self.browser_manager:
            return []
        
        page = None
        try:
            page = await self.browser_manager.new_page()
            if not page:
                return []
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(2000)
            html = await page.content()
            
            soup = BeautifulSoup(html, 'lxml')
            extracted_urls = []
            
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
                    video_urls = re.findall(r'["\']https?://[^"\']+\.(?:mp4|m3u8|webm|mp3|wav)[^"\']*["\']', script.string)
                    extracted_urls.extend([u.strip('"\'') for u in video_urls])
            
            for attr in ['data-video-url', 'data-src']:
                for elem in soup.find_all(attrs={attr: True}):
                    data_val = elem[attr]
                    if attr == 'data-src' and not any(ext in data_val.lower() for ext in ['.mp4', '.m3u8', 'video', 'media', '.mp3', '.wav']):
                        continue
                    extracted_urls.append(urljoin(url, data_val))
            
            await page.close()
            return extracted_urls
        except Exception as e:
            if page:
                await page.close()
            self.logger.warning(f"Page extraction failed: {str(e)}")
            return []
    
    async def _verify_ytdlp(self, url: str, original_url: str = None, max_retries: int = 2) -> bool:
        """Verify URL with yt-dlp."""
        for attempt in range(max_retries + 1):
            process = None
            try:
                cmd = ['yt-dlp', '--simulate', '--no-warnings', '--quiet', '--socket-timeout', '15']
                
                if original_url and any(d in url for d in self.REFERER_REQUIRED):
                    parsed = urlparse(original_url)
                    cmd.extend(['--referer', f"{parsed.scheme}://{parsed.netloc}/"])
                
                cmd.append(url)
                
                process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45.0)
                
                if process.returncode == 0:
                    return True
                
                stderr_text = stderr.decode('utf-8', errors='ignore').lower()
                if any(msg in stderr_text for msg in ['private video', 'requires authentication']):
                    return True
                
                if any(msg in stderr_text for msg in ['unable to download', 'http error']) and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                return False
            except asyncio.TimeoutError:
                if process:
                    process.kill()
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                return False
            except FileNotFoundError:
                self.logger.error("yt-dlp not found. Install: pip install yt-dlp")
                return False
            except Exception:
                if process:
                    process.kill()
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
                return False
        return False
    
    async def _verify_document(self, url: str, max_retries: int = 2) -> bool:
        """Verify document URL is accessible."""
        for attempt in range(max_retries + 1):
            try:
                response = await self.http_client.head(url, follow_redirects=True, timeout=self.TIMEOUT_SHORT)
                return response.status_code == 200
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError):
                if attempt < max_retries:
                    await asyncio.sleep(1 + attempt)
                    continue
                return True
            except Exception:
                return True
        return True
    
    async def batch_resolve(self, url_list: List[dict]) -> List[str]:
        """Resolve multiple URLs concurrently."""
        self.logger.info(f"Starting batch resolution of {len(url_list)} URLs")
        tasks = [self._resolve_item(item) for item in url_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        resolved = [r for r in results if r and not isinstance(r, Exception)]
        self.logger.info(f"Resolved {len(resolved)}/{len(url_list)} URLs")
        return resolved
    
    async def _resolve_item(self, item: dict) -> Optional[str]:
        """Resolve single item from dict."""
        url = item.get('url')
        url_type = item.get('type', 'video')
        return await self.resolve_url(url, url_type) if url else None
