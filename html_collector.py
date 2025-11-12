"""Collect HTML from domains using stealth browser."""
import asyncio
from pathlib import Path
from src.core.browser import BrowserManager
from src.core.stealth import StealthConfig

PROBLEM1_DOMAINS = [
    # "https://www.cityofventura.ca.gov/AgendaCenter",
    # "https://www.bethlehem-pa.gov/Calendar",
    # "https://www.lansdale.org/CivicMedia?CID=2024-Council-Meetings-26",
    # "https://www.facebook.com/DauphinCountyPA/videos",
    # "https://go.boarddocs.com/ca/acoe/Board.nsf/Public",
    "https://simbli.eboardsolutions.com/SB_Meetings/SB_MeetingListing.aspx?S=36030373"
]

OUTPUT_DIR = Path("domain_html")


async def collect_html(url: str, browser: BrowserManager) -> bool:
    try:
        print(f"\n-> {url}")
        page = await browser.new_page()
        
        await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # For Facebook, scroll to load all videos
        if 'facebook.com' in url.lower():
            print("  Scrolling Facebook page to load all videos...")
            
            # Try to close modals first
            try:
                close_selectors = [
                    'div[aria-label="Close"]',
                    'button[aria-label="Close"]',
                    '[data-testid="cookie-policy-manage-dialog-accept-button"]',
                ]
                for selector in close_selectors:
                    try:
                        close_button = await page.query_selector(selector)
                        if close_button:
                            await close_button.click()
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            except:
                pass
            
            # Infinite scroll
            last_height = await page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0
            no_change_count = 0
            
            while scroll_attempts < 20 and no_change_count < 3:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)
                
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    no_change_count += 1
                else:
                    no_change_count = 0
                    print(f"  Loaded more content (scroll {scroll_attempts + 1})...")
                
                last_height = new_height
                scroll_attempts += 1
        
        # For EBoardSolutions, advanced bot detection avoidance
        if 'eboardsolutions.com' in url.lower():
            print("  Applying advanced bot detection avoidance for EBoardSolutions...")
            
            # Initial wait
            import random
            await page.wait_for_timeout(random.randint(5000, 8000))
            
            # Mouse movements to simulate human
            try:
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                await page.wait_for_timeout(random.randint(500, 1500))
                await page.mouse.move(random.randint(200, 600), random.randint(200, 600))
                await page.wait_for_timeout(random.randint(300, 800))
            except:
                pass
            
            # Scroll to simulate human behavior
            try:
                await page.evaluate("window.scrollTo(0, Math.random() * 300)")
                await page.wait_for_timeout(random.randint(1000, 2000))
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(random.randint(500, 1000))
            except:
                pass
            
            # Wait for content
            try:
                await page.wait_for_selector('#ContentPlaceHolder1_MeetingGrid tbody tr', timeout=15000)
                print("  Meeting grid loaded successfully")
                await page.wait_for_timeout(2000)
            except:
                print("  Warning: Meeting grid selector not found, continuing anyway")
                pass
        
        html = await page.content()
        body_start = html.find('<body')
        body_end = html.rfind('</body>') + 7
        
        if body_start != -1 and body_end > body_start:
            body_html = html[body_start:body_end]
        else:
            body_html = html
        
        filename = url.split('//')[-1].replace('/', '_').replace('?', '_').replace('=', '_')[:60] + '.html'
        output_path = OUTPUT_DIR / filename
        output_path.write_text(body_html, encoding='utf-8')
        
        print(f"OK {filename} ({len(body_html):,} chars)")
        await page.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)[:100]}")
        return False


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    stealth_config = StealthConfig()
    
    async with BrowserManager(stealth_config=stealth_config, headless=False) as browser:
        results = {}
        for url in PROBLEM1_DOMAINS:
            success = await collect_html(url, browser)
            results[url] = success
            await asyncio.sleep(1)
    
    print(f"\n{'='*60}")
    print("Summary:")
    for url, success in results.items():
        status = 'OK' if success else 'FAILED'
        print(f"{status} {url}")


if __name__ == '__main__':
    asyncio.run(main())

