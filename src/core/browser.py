"""
Playwright browser manager with stealth configuration and resource blocking for optimized web scraping.

Key Features:
- Automatic stealth script injection to bypass bot detection
- Resource blocking (images, fonts, CSS, media) for faster page loads
- Context recreation with fingerprint rotation on detection
- Async context manager support for clean lifecycle management
"""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .stealth import StealthManager, StealthConfig


class BrowserManager:
    def __init__(self, stealth_config: Optional[StealthConfig] = None, headless: bool = True):
        self.headless = headless
        self.stealth = StealthManager(stealth_config or StealthConfig())
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def start(self) -> None:
        if self._browser:
            return
            
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=self.stealth.get_browser_args()
        )
        
    async def _get_context(self) -> BrowserContext:
        if not self._context:
            if not self._browser:
                await self.start()
            
            viewport = self.stealth.get_viewport()
            user_agent = self.stealth.get_user_agent()
            
            self._context = await self._browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale=self.stealth.LOCALES[0],
                timezone_id=self.stealth.TIMEZONES[0]
            )
        
        return self._context
        
    async def new_page(self, allow_resources: bool = False) -> Page:
        context = await self._get_context()
        page = await context.new_page()
        
        if not allow_resources:
            # Block unnecessary resources (images, fonts, CSS, media, analytics)
            BLOCKED_RESOURCES = ["image", "font", "stylesheet", "media"]
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in BLOCKED_RESOURCES 
                else route.continue_())
        
        await self.stealth.apply_stealth_scripts(page)
        return page
        
    async def recreate_context(self) -> None:
        """Recreate browser context with new fingerprint (for bot detection retry)."""
        if self._context:
            try:
                await self._context.close()
            except:
                pass
            self._context = None
        
        # Rotate fingerprint for new context
        self.stealth.rotate_fingerprint()
    
    async def close(self) -> None:
        if self._context:
            try:
                await self._context.close()
            except:
                pass
            self._context = None
        
        if self._browser:
            await self._browser.close()
            self._browser = None
            
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
