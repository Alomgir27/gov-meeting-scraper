"""
Anti-detection stealth with fingerprint masking and user-agent rotation.

Techniques:
- User-agent rotation (realistic browser profiles)
- Viewport randomization (natural fingerprinting)
- Canvas noise injection (bypasses fingerprinting)
- WebGL/Navigator spoofing (masks automation signals)
"""
import random
from typing import Optional
from dataclasses import dataclass


@dataclass
class StealthConfig:
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    randomize_viewport: bool = True
    user_agent_rotation: bool = True


class StealthManager:
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 2560, "height": 1440},
    ]
    
    LOCALES = ["en-US", "en-GB", "en-CA"]
    TIMEZONES = ["America/New_York", "America/Los_Angeles", "Europe/London"]
    
    def __init__(self, config: StealthConfig):
        self.config = config
        self._current_fingerprint = self._generate_fingerprint()
        
    def get_user_agent(self) -> str:
        if self.config.user_agent_rotation:
            return random.choice(self.USER_AGENTS)
        return self.USER_AGENTS[0]
    
    def get_viewport(self) -> dict:
        if self.config.randomize_viewport:
            return random.choice(self.VIEWPORTS)
        return self.VIEWPORTS[0]
    
    def get_headers(self) -> dict:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": f"{random.choice(self.LOCALES)},en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
    
    def get_browser_args(self) -> list:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            # Performance optimizations
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--mute-audio",
        ]
        
        if self.config.use_proxy and self.config.proxy_url:
            args.append(f"--proxy-server={self.config.proxy_url}")
            
        return args
    
    def _generate_fingerprint(self) -> dict:
        return {
            'canvas_noise': random.random(),
            'webgl_vendor': random.choice(['Intel Inc.', 'NVIDIA Corporation', 'AMD']),
            'audio_noise': random.random()
        }
    
    def rotate_fingerprint(self) -> None:
        self._current_fingerprint = self._generate_fingerprint()
    
    async def apply_stealth_scripts(self, page) -> None:
        """
        Inject stealth scripts to mask automation signals.
        Randomizes canvas, WebGL, and navigator properties.
        """
        canvas_noise = self._current_fingerprint['canvas_noise']
        webgl_vendor = self._current_fingerprint['webgl_vendor']
        
        await page.add_init_script(f"""
            Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
            Object.defineProperty(navigator, 'plugins', {{get: () => [1, 2, 3, 4, 5]}});
            Object.defineProperty(navigator, 'languages', {{get: () => ['en-US', 'en']}});
            window.chrome = {{runtime: {{}}}};
            Object.defineProperty(navigator, 'permissions', {{get: () => ({{
                query: () => Promise.resolve({{state: 'granted'}})
            }})}});
            
            const canvasNoise = {canvas_noise};
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {{
                const context = this.getContext('2d');
                if (context) {{
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        imageData.data[i] = imageData.data[i] + canvasNoise;
                    }}
                    context.putImageData(imageData, 0, 0);
                }}
                return originalToDataURL.apply(this, arguments);
            }};
            
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) return '{webgl_vendor}';
                if (param === 37446) return 'Graphics Renderer';
                return getParameter.apply(this, arguments);
            }};
        """)

