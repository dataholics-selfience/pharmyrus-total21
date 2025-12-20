"""
WIPO Patentscope Crawler - V6 STEALTH
Advanced anti-detection for WIPO patent searches
"""
import asyncio
import random
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser
import logging
import json

from app.utils.user_agents import UserAgentRotator
from app.utils.fingerprint import FingerprintRandomizer
from app.utils.delays import DelayManager

logger = logging.getLogger(__name__)


class WIPOCrawler:
    """
    WIPO Patentscope crawler with anti-detection
    
    WIPO is generally lighter on protection than Google, but still requires:
    - Realistic headers
    - Session management
    - Rate limiting
    - User-Agent rotation
    
    Endpoints:
    - Search: https://patentscope.wipo.int/search/en/search.jsf
    - API: https://patentscope.wipo.int/search/rest/patents
    """
    
    BASE_URL = "https://patentscope.wipo.int"
    SEARCH_URL = f"{BASE_URL}/search/en/search.jsf"
    API_URL = f"{BASE_URL}/search/rest/patents"
    
    # Circuit breaker settings
    MAX_CONSECUTIVE_FAILURES = 3
    CIRCUIT_OPEN_DURATION = 180  # 3 minutes (WIPO is lighter)
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.ua_rotator = UserAgentRotator()
        self.fingerprint = FingerprintRandomizer()
        self.delay_manager = DelayManager()
        
        # Session state
        self.current_user_agent = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        
        # Circuit breaker
        self.consecutive_failures = 0
        self.circuit_open_until = 0
        
        # Statistics
        self.stats = {
            'searches': 0,
            'successes': 0,
            'failures': 0,
            'wo_numbers_found': 0,
            'br_applications_found': 0,
            'method_used': {}  # Track which method worked
        }
    
    def _get_headers(self, user_agent: str, referer: Optional[str] = None) -> Dict[str, str]:
        """Generate headers for WIPO requests"""
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': user_agent,
        }
        
        if referer:
            headers['Referer'] = referer
        
        return headers
    
    async def _init_http_client(self):
        """Initialize HTTP client with stealth settings"""
        if self.http_client:
            return
        
        self.current_user_agent = self.ua_rotator.get_random()
        logger.info(f"🔧 HTTP Client User-Agent: {self.current_user_agent[:80]}...")
        
        self.http_client = httpx.AsyncClient(
            headers=self._get_headers(self.current_user_agent),
            timeout=30.0,
            follow_redirects=True,
            proxies=self.proxy if self.proxy else None
        )
    
    async def _init_browser_session(self):
        """Initialize Playwright browser for complex scraping"""
        if self.browser:
            return
        
        logger.info("🚀 Initializing WIPO browser session...")
        
        self.current_user_agent = self.ua_rotator.get_random()
        
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            proxy={'server': self.proxy} if self.proxy else None,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent=self.current_user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            extra_http_headers=self._get_headers(self.current_user_agent)
        )
        
        self.page = await self.context.new_page()
        await self.page.add_init_script(self.fingerprint.get_full_stealth_script())
        
        logger.info("✅ WIPO browser session initialized")
    
    def _check_circuit_breaker(self) -> bool:
        """Check circuit breaker state"""
        if time.time() < self.circuit_open_until:
            remaining = int(self.circuit_open_until - time.time())
            logger.warning(f"⛔ Circuit breaker OPEN - {remaining}s remaining")
            return True
        return False
    
    def _record_failure(self):
        """Record failure"""
        self.consecutive_failures += 1
        self.stats['failures'] += 1
        
        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self.circuit_open_until = time.time() + self.CIRCUIT_OPEN_DURATION
            logger.error(f"🔥 Circuit breaker OPENED - blocking for {self.CIRCUIT_OPEN_DURATION}s")
    
    def _record_success(self, method: str):
        """Record success"""
        self.consecutive_failures = 0
        self.stats['successes'] += 1
        self.stats['method_used'][method] = self.stats['method_used'].get(method, 0) + 1
    
    async def search_wo_number(self, wo_number: str) -> Tuple[bool, Optional[Dict]]:
        """
        Search for a specific WO number in WIPO
        
        Returns:
            (success, patent_data)
        """
        if self._check_circuit_breaker():
            return False, None
        
        self.stats['searches'] += 1
        
        # Try HTTP API first (faster, lighter)
        success, data = await self._search_via_api(wo_number)
        if success:
            self._record_success('api')
            return True, data
        
        # Fallback to browser scraping
        logger.info("   Falling back to browser scraping...")
        success, data = await self._search_via_browser(wo_number)
        if success:
            self._record_success('browser')
            return True, data
        
        self._record_failure()
        return False, None
    
    async def _search_via_api(self, wo_number: str) -> Tuple[bool, Optional[Dict]]:
        """
        Search via WIPO REST API
        
        WIPO has a REST API that's more lenient than web scraping
        """
        try:
            await self._init_http_client()
            
            logger.info(f"🔍 WIPO API search: {wo_number}")
            
            # Clean WO number
            wo_clean = wo_number.replace('WO', '').replace(' ', '').replace('-', '')
            
            # API endpoint
            api_url = f"{self.API_URL}?query={wo_clean}&offset=0&limit=10"
            
            # Add delay
            delay = self.delay_manager.get_gaussian_delay(mean=2, std_dev=0.5, min_val=1, max_val=4)
            await asyncio.sleep(delay)
            
            response = await self.http_client.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract patent info
                if 'results' in data and len(data['results']) > 0:
                    patent = data['results'][0]
                    logger.info(f"✅ Found via API: {patent.get('IA', 'N/A')}")
                    return True, patent
                else:
                    logger.warning("   No results from API")
                    return False, None
            else:
                logger.warning(f"   API returned status {response.status_code}")
                return False, None
                
        except Exception as e:
            logger.error(f"   API search failed: {e}")
            return False, None
    
    async def _search_via_browser(self, wo_number: str) -> Tuple[bool, Optional[Dict]]:
        """
        Search via browser scraping (fallback)
        """
        try:
            await self._init_browser_session()
            
            logger.info(f"🌐 WIPO browser search: {wo_number}")
            
            # Navigate to search page
            search_url = f"{self.SEARCH_URL}?query={quote_plus(wo_number)}"
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(3, 6))
            
            # Extract data from page
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Parse results (would need actual WIPO HTML structure)
            patent_data = self._parse_wipo_results(soup)
            
            if patent_data:
                logger.info("✅ Found via browser")
                return True, patent_data
            else:
                logger.warning("   No results from browser")
                return False, None
                
        except Exception as e:
            logger.error(f"   Browser search failed: {e}")
            return False, None
    
    def _parse_wipo_results(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Parse WIPO search results page"""
        # This would need actual WIPO HTML structure
        # For now, return basic structure
        
        try:
            # Look for patent title, publication number, etc.
            title_elem = soup.find('span', class_='title')
            title = title_elem.text.strip() if title_elem else None
            
            if title:
                return {
                    'title': title,
                    'source': 'wipo_browser'
                }
        except:
            pass
        
        return None
    
    async def get_br_applications(self, wo_number: str) -> List[str]:
        """
        Get Brazilian applications for a WO number
        
        Strategy:
        1. Search for WO number
        2. Extract "Designated States" or "National Phase" data
        3. Filter for BR applications
        """
        if self._check_circuit_breaker():
            return []
        
        try:
            logger.info(f"🇧🇷 Getting BR applications for: {wo_number}")
            
            success, patent_data = await self.search_wo_number(wo_number)
            
            if not success or not patent_data:
                return []
            
            br_applications = []
            
            # Extract BR applications from patent data
            if 'nationalPhase' in patent_data:
                for entry in patent_data['nationalPhase']:
                    if entry.get('country') == 'BR':
                        app_number = entry.get('applicationNumber')
                        if app_number:
                            br_applications.append(app_number)
            
            # Also check designated states
            if 'designatedStates' in patent_data:
                if 'BR' in patent_data['designatedStates']:
                    logger.info("   BR is a designated state")
            
            if br_applications:
                self.stats['br_applications_found'] += len(br_applications)
                logger.info(f"✅ Found {len(br_applications)} BR applications")
            else:
                logger.info("   No BR applications found")
            
            return br_applications
            
        except Exception as e:
            logger.error(f"❌ Failed to get BR applications: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get crawler statistics"""
        success_rate = (self.stats['successes'] / self.stats['searches'] * 100) if self.stats['searches'] > 0 else 0
        
        return {
            **self.stats,
            'success_rate': f"{success_rate:.1f}%",
            'circuit_breaker': 'OPEN' if time.time() < self.circuit_open_until else 'CLOSED'
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        
        logger.info("🧹 WIPO crawler cleaned up")


async def test_wipo():
    """Test function"""
    crawler = WIPOCrawler()
    
    try:
        # Test search
        wo_number = "WO2016001234"
        success, data = await crawler.search_wo_number(wo_number)
        
        print(f"\n✅ Search result: {success}")
        if data:
            print(f"   Title: {data.get('title', 'N/A')}")
        
        # Test BR applications
        br_apps = await crawler.get_br_applications(wo_number)
        print(f"\n✅ BR applications: {len(br_apps)}")
        for app in br_apps:
            print(f"   - {app}")
        
        # Stats
        print(f"\n📊 Statistics:")
        stats = crawler.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
    finally:
        await crawler.cleanup()


if __name__ == "__main__":
    asyncio.run(test_wipo())
