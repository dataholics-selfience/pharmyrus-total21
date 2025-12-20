"""
Playwright Crawler - Layer 1 (Highest Stealth)
"""
import asyncio
import random
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup
import re
import logging

from app.crawlers.base_crawler import BaseCrawler, CrawlerLayer, CrawlerStatus
from app.utils.user_agents import UserAgentRotator
from app.utils.fingerprint import FingerprintRandomizer
from app.utils.delays import DelayManager

logger = logging.getLogger(__name__)


class PlaywrightCrawler(BaseCrawler):
    """
    Layer 1: Playwright with maximum stealth
    
    Pros:
    - Highest stealth (full browser fingerprint)
    - JavaScript rendering
    - Best for Google Patents
    
    Cons:
    - Slower (500ms-2s per page)
    - Higher resource usage
    """
    
    GOOGLE_PATENTS_URL = "https://patents.google.com"
    
    def __init__(self):
        super().__init__("Playwright", CrawlerLayer.PLAYWRIGHT)
        
        self.ua_rotator = UserAgentRotator()
        self.fingerprint = FingerprintRandomizer()
        self.delay_manager = DelayManager()
        
        # Playwright resources
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Current session
        self.current_user_agent = None
        self.session_start_time = 0
        self.max_session_duration = 600  # 10 minutes
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if self.browser:
            return
        
        logger.info(f"🎭 {self.name}: Initializing stealth browser...")
        
        try:
            # Get User-Agent
            self.current_user_agent = self.ua_rotator.get_random()
            logger.info(f"   User-Agent: {self.current_user_agent[:80]}...")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--start-maximized',
                    '--disable-notifications',
                    '--disable-popup-blocking',
                ]
            )
            
            # Create context
            self.context = await self.browser.new_context(
                user_agent=self.current_user_agent,
                viewport={'width': 1920, 'height': 1080},
                locale='pt-BR',
                timezone_id='America/Sao_Paulo',
                geolocation={'latitude': -23.5505, 'longitude': -46.6333},
                permissions=['geolocation']
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Apply stealth scripts
            await self.page.add_init_script(self.fingerprint.get_full_stealth_script())
            
            # Warm-up session
            await self._warm_up_session()
            
            self.session_start_time = time.time()
            self.status = CrawlerStatus.READY
            
            logger.info(f"✅ {self.name}: Browser initialized and warmed up")
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Initialization failed: {e}")
            self.status = CrawlerStatus.FAILED
            raise
    
    async def _warm_up_session(self):
        """Warm up browser session by visiting homepage"""
        try:
            logger.info(f"🔥 {self.name}: Warming up session...")
            await self.page.goto(self.GOOGLE_PATENTS_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            logger.info(f"✅ {self.name}: Session warmed up")
        except Exception as e:
            logger.warning(f"⚠️  {self.name}: Warm-up failed (non-critical): {e}")
    
    async def _check_session_age(self):
        """Check if session needs renewal"""
        if time.time() - self.session_start_time > self.max_session_duration:
            logger.info(f"🔄 {self.name}: Session expired, renewing...")
            await self.cleanup()
            await self.initialize()
    
    async def cleanup(self):
        """Cleanup Playwright resources"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            logger.info(f"🧹 {self.name}: Cleaned up")
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Cleanup error: {e}")
    
    async def search_patents(self, query: str, max_results: int = 20) -> List[str]:
        """
        Search Google Patents and extract WO numbers
        """
        if not self.is_available():
            logger.warning(f"⛔ {self.name}: Not available (circuit open)")
            return []
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_age()
            
            logger.info(f"🔍 {self.name}: Searching '{query}'")
            
            # Navigate to search
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={quote_plus(query)}"
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            
            # Human-like dwell time
            await asyncio.sleep(random.uniform(3, 6))
            
            # Get page content
            content = await self.page.content()
            
            # Check for blocking
            if self._detect_block(content):
                logger.error(f"🚫 {self.name}: BLOCKED by Google Patents")
                self.record_failure(is_block=True)
                return []
            
            # Extract WO numbers
            wo_numbers = self._extract_wo_numbers(content)
            
            response_time = time.time() - start_time
            self.record_success(response_time)
            
            logger.info(f"✅ {self.name}: Found {len(wo_numbers)} WO numbers ({response_time:.2f}s)")
            
            return wo_numbers[:max_results]
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Search failed: {e}")
            self.record_failure()
            return []
    
    async def get_patent_details(self, wo_number: str) -> Optional[Dict]:
        """Get patent details"""
        if not self.is_available():
            return None
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_age()
            
            logger.info(f"📄 {self.name}: Getting details for {wo_number}")
            
            # Search for WO number
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={wo_number}"
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Click first result
            try:
                await self.page.click('search-result-item:first-child', timeout=10000)
                await asyncio.sleep(random.uniform(2, 3))
            except:
                logger.warning(f"   Could not click result for {wo_number}")
                return None
            
            # Get content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Parse details
            details = self._parse_patent_details(soup, wo_number)
            
            response_time = time.time() - start_time
            self.record_success(response_time)
            
            return details
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Get details failed: {e}")
            self.record_failure()
            return None
    
    async def get_br_patents_from_wo(self, wo_number: str) -> List[str]:
        """Get BR patents from WO family"""
        if not self.is_available():
            return []
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_age()
            
            logger.info(f"🇧🇷 {self.name}: Getting BR patents for {wo_number}")
            
            # Get patent details page
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={wo_number}"
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(2, 3))
            
            # Click first result
            try:
                await self.page.click('search-result-item:first-child', timeout=10000)
                await asyncio.sleep(random.uniform(2, 4))
            except:
                return []
            
            # Get content and extract BR patents
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            br_patents = self._extract_br_patents(soup)
            
            response_time = time.time() - start_time
            self.record_success(response_time)
            
            logger.info(f"✅ {self.name}: Found {len(br_patents)} BR patents ({response_time:.2f}s)")
            
            return br_patents
            
        except Exception as e:
            logger.error(f"❌ {self.name}: BR extraction failed: {e}")
            self.record_failure()
            return []
    
    def _detect_block(self, content: str) -> bool:
        """Detect if blocked"""
        block_indicators = [
            'unusual traffic',
            'automated requests',
            'captcha',
            'recaptcha',
            'access denied',
            'forbidden',
            'blocked'
        ]
        
        content_lower = content.lower()
        for indicator in block_indicators:
            if indicator in content_lower:
                return True
        
        # Empty response
        if len(content) < 1000:
            logger.warning(f"⚠️  {self.name}: Suspiciously small response ({len(content)} chars)")
            return True
        
        return False
    
    def _extract_wo_numbers(self, content: str) -> List[str]:
        """Extract WO numbers from content"""
        wo_numbers = set()
        wo_pattern = re.compile(r'WO[\s-]?(\d{4})[\s/]?(\d{6})', re.IGNORECASE)
        
        matches = wo_pattern.findall(content)
        for year, number in matches:
            wo = f"WO{year}{number}"
            wo_numbers.add(wo)
        
        return sorted(list(wo_numbers))
    
    def _extract_br_patents(self, soup: BeautifulSoup) -> List[str]:
        """Extract BR patent numbers from page"""
        br_patents = []
        br_pattern = re.compile(r'BR[\s-]?(\d{10,12})[A-Z]?\d?', re.IGNORECASE)
        
        text = soup.get_text()
        matches = br_pattern.findall(text)
        
        for match in matches:
            br_patent = f"BR{match}"
            if br_patent not in br_patents:
                br_patents.append(br_patent)
        
        return br_patents
    
    def _parse_patent_details(self, soup: BeautifulSoup, wo_number: str) -> Dict:
        """Parse patent details from page"""
        try:
            title_elem = soup.find('meta', {'name': 'citation_title'})
            title = title_elem['content'] if title_elem else 'Unknown'
            
            abstract_elem = soup.find('meta', {'name': 'description'})
            abstract = abstract_elem['content'] if abstract_elem else ''
            
            return {
                'wo_number': wo_number,
                'title': title,
                'abstract': abstract[:500],
                'source': 'playwright'
            }
        except:
            return {
                'wo_number': wo_number,
                'title': 'Parse error',
                'source': 'playwright'
            }
