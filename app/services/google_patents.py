"""
Google Patents Crawler - V6 STEALTH
Advanced anti-detection techniques for Google Patents searches
"""
import asyncio
import random
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser
import logging

from app.utils.user_agents import UserAgentRotator
from app.utils.fingerprint import FingerprintRandomizer
from app.utils.delays import DelayManager

logger = logging.getLogger(__name__)


class GooglePatentsCrawler:
    """
    Advanced Google Patents crawler with comprehensive anti-detection
    
    Features:
    - Playwright with stealth fingerprinting
    - Session management with cookie persistence
    - Correct Chrome header order
    - Client Hints consistency
    - Gaussian delays
    - Circuit breaker pattern
    - WO number extraction
    - BR patent filtering
    """
    
    BASE_URL = "https://patents.google.com"
    SEARCH_URL = f"{BASE_URL}/"
    
    # Circuit breaker settings
    MAX_CONSECUTIVE_FAILURES = 3
    CIRCUIT_OPEN_DURATION = 300  # 5 minutes
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.ua_rotator = UserAgentRotator()
        self.fingerprint = FingerprintRandomizer()
        self.delay_manager = DelayManager()
        
        # Session state
        self.current_user_agent = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.session_cookies = []
        
        # Circuit breaker
        self.consecutive_failures = 0
        self.circuit_open_until = 0
        
        # Statistics
        self.stats = {
            'searches': 0,
            'successes': 0,
            'failures': 0,
            'wo_numbers_found': 0,
            'br_patents_found': 0
        }
    
    def _get_chrome_headers(self, user_agent: str, referer: Optional[str] = None) -> Dict[str, str]:
        """
        Generate Chrome headers in correct order with Client Hints
        
        CRITICAL: Header order matters for detection!
        Chrome order: Host → Connection → Cache-Control → sec-ch-ua → User-Agent → Accept → Sec-Fetch → Accept-Encoding → Accept-Language
        """
        # Extract Chrome version from User-Agent
        chrome_version = "131"  # default
        if "Chrome/" in user_agent:
            try:
                chrome_version = user_agent.split("Chrome/")[1].split(".")[0]
            except:
                pass
        
        # Client Hints MUST match User-Agent
        headers = {
            # Core headers (order matters!)
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            
            # Client Hints (CRITICAL for consistency)
            'sec-ch-ua': f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not=A?Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            
            # Sec-Fetch (indicates legitimate browser navigation)
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': user_agent,
        }
        
        if referer:
            headers['Referer'] = referer
            headers['Sec-Fetch-Site'] = 'same-origin'
        
        return headers
    
    async def _init_browser_session(self):
        """Initialize Playwright browser with advanced stealth"""
        if self.browser:
            return
        
        logger.info("🚀 Initializing Google Patents stealth session...")
        
        # Get fresh User-Agent
        self.current_user_agent = self.ua_rotator.get_random()
        logger.info(f"   User-Agent: {self.current_user_agent[:80]}...")
        
        playwright = await async_playwright().start()
        
        # Launch with stealth args
        self.browser = await playwright.chromium.launch(
            headless=True,
            proxy={'server': self.proxy} if self.proxy else None,
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
        
        # Create context with geolocation (São Paulo)
        self.context = await self.browser.new_context(
            user_agent=self.current_user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            geolocation={'latitude': -23.5505, 'longitude': -46.6333},
            permissions=['geolocation'],
            extra_http_headers=self._get_chrome_headers(self.current_user_agent)
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Apply comprehensive stealth scripts
        await self.page.add_init_script(self.fingerprint.get_full_stealth_script())
        logger.info("✅ Applied advanced fingerprint randomization")
        
        # Warm-up: Visit homepage first (realistic behavior)
        logger.info("🔥 Warming up session (visiting homepage)...")
        try:
            await self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))  # Realistic dwell time
            logger.info("✅ Session warmed up")
        except Exception as e:
            logger.warning(f"⚠️  Warm-up failed (non-critical): {e}")
    
    async def _close_session(self):
        """Close browser session"""
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open (blocking requests)"""
        if time.time() < self.circuit_open_until:
            remaining = int(self.circuit_open_until - time.time())
            logger.warning(f"⛔ Circuit breaker OPEN - blocking requests for {remaining}s more")
            return True
        return False
    
    def _record_failure(self):
        """Record failure and potentially open circuit breaker"""
        self.consecutive_failures += 1
        self.stats['failures'] += 1
        
        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self.circuit_open_until = time.time() + self.CIRCUIT_OPEN_DURATION
            logger.error(f"🔥 Circuit breaker OPENED after {self.consecutive_failures} consecutive failures")
            logger.error(f"   Blocking requests for {self.CIRCUIT_OPEN_DURATION}s")
    
    def _record_success(self):
        """Record success and reset circuit breaker"""
        self.consecutive_failures = 0
        self.stats['successes'] += 1
    
    async def search_wo_numbers(self, molecule_name: str, dev_codes: List[str] = None, cas: str = None) -> List[str]:
        """
        Search for WO patent numbers for a molecule
        
        Strategy:
        1. Use multiple search queries (molecule + company names + dev codes)
        2. Extract WO numbers from search results
        3. Deduplicate and return
        
        Returns:
            List of unique WO numbers (e.g., ['WO2016001234', 'WO2020056789'])
        """
        if self._check_circuit_breaker():
            return []
        
        self.stats['searches'] += 1
        
        try:
            await self._init_browser_session()
            
            # Build search queries
            queries = self._build_search_queries(molecule_name, dev_codes, cas)
            logger.info(f"🔍 Searching Google Patents with {len(queries)} queries for: {molecule_name}")
            
            all_wo_numbers = set()
            
            for i, query in enumerate(queries, 1):
                logger.info(f"   Query {i}/{len(queries)}: {query}")
                
                # Gaussian delay between queries (15-30s recommended for Google)
                if i > 1:
                    delay = self.delay_manager.get_gaussian_delay(mean=20, std_dev=5, min_val=15, max_val=30)
                    logger.info(f"   ⏱️  Delay: {delay:.1f}s")
                    await asyncio.sleep(delay)
                
                # Execute search
                wo_numbers = await self._execute_search(query)
                all_wo_numbers.update(wo_numbers)
                
                logger.info(f"   Found {len(wo_numbers)} WO numbers (total unique: {len(all_wo_numbers)})")
            
            result = sorted(list(all_wo_numbers))
            self.stats['wo_numbers_found'] += len(result)
            self._record_success()
            
            logger.info(f"✅ Total unique WO numbers found: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Google Patents search failed: {e}")
            self._record_failure()
            return []
    
    def _build_search_queries(self, molecule: str, dev_codes: List[str] = None, cas: str = None) -> List[str]:
        """
        Build multiple search queries to maximize WO number discovery
        
        Strategy from research:
        - Molecule name + different year ranges
        - Molecule + known pharmaceutical companies
        - Development codes
        """
        queries = []
        
        # Base queries with year ranges
        year_ranges = ['2016', '2018', '2019', '2020', '2021', '2022', '2023']
        for year in year_ranges:
            queries.append(f'{molecule} patent WO{year}')
        
        # Company-specific searches (common pharma patent holders)
        companies = ['Orion Corporation', 'Bayer', 'Pfizer', 'Roche', 'Novartis']
        for company in companies[:3]:  # Limit to 3 to avoid too many queries
            queries.append(f'{molecule} {company} patent')
        
        # Dev codes
        if dev_codes:
            for code in dev_codes[:2]:  # First 2 dev codes
                queries.append(f'{code} patent WO')
        
        return queries
    
    async def _execute_search(self, query: str) -> set:
        """Execute a single search query and extract WO numbers"""
        wo_numbers = set()
        
        try:
            # Navigate to search
            search_url = f"{self.SEARCH_URL}?q={quote_plus(query)}"
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            
            # Random dwell time (5-15s for search results - realistic)
            await asyncio.sleep(random.uniform(5, 15))
            
            # Get page content
            content = await self.page.content()
            
            # Check for blocking
            if self._detect_block(content):
                logger.error("🚫 BLOCKED by Google Patents!")
                raise Exception("Blocked by anti-bot protection")
            
            # Extract WO numbers using regex
            import re
            wo_pattern = re.compile(r'WO[\s-]?(\d{4})[\s/]?(\d{6})', re.IGNORECASE)
            matches = wo_pattern.findall(content)
            
            for year, number in matches:
                wo = f"WO{year}{number}"
                wo_numbers.add(wo)
            
        except Exception as e:
            logger.error(f"   Search execution failed: {e}")
        
        return wo_numbers
    
    def _detect_block(self, content: str) -> bool:
        """Detect if we've been blocked"""
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
        
        # Check for empty results (might indicate soft block)
        if len(content) < 1000:
            logger.warning("⚠️  Suspiciously small response")
            return True
        
        return False
    
    async def get_wo_worldwide_applications(self, wo_number: str) -> Tuple[bool, List[str]]:
        """
        Get worldwide applications for a WO number and extract BR patents
        
        Args:
            wo_number: WO patent number (e.g., 'WO2016001234')
            
        Returns:
            (success: bool, br_patents: List[str])
        """
        if self._check_circuit_breaker():
            return False, []
        
        try:
            await self._init_browser_session()
            
            logger.info(f"🌍 Getting worldwide applications for: {wo_number}")
            
            # Search for the specific WO number
            search_url = f"{self.SEARCH_URL}?q={wo_number}"
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(3, 6))
            
            # Click on first result (the WO patent itself)
            try:
                await self.page.click('search-result-item', timeout=10000)
                await asyncio.sleep(random.uniform(2, 4))
            except:
                logger.warning(f"   Could not click on WO {wo_number} result")
                return False, []
            
            # Look for "Worldwide applications" section
            # This would require analyzing the actual page structure
            # For now, we'll extract from page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            br_patents = self._extract_br_patents_from_content(soup)
            
            if br_patents:
                self.stats['br_patents_found'] += len(br_patents)
                logger.info(f"✅ Found {len(br_patents)} BR patents for {wo_number}")
                self._record_success()
                return True, br_patents
            else:
                logger.info(f"   No BR patents found for {wo_number}")
                self._record_success()  # Still a success, just no BR
                return True, []
            
        except Exception as e:
            logger.error(f"❌ Failed to get worldwide applications for {wo_number}: {e}")
            self._record_failure()
            return False, []
    
    def _extract_br_patents_from_content(self, soup: BeautifulSoup) -> List[str]:
        """Extract BR patent numbers from page content"""
        br_patents = []
        
        # Look for BR patent numbers in various formats
        import re
        br_pattern = re.compile(r'BR[\s-]?(\d{10,12})[A-Z]?\d?', re.IGNORECASE)
        
        # Search in all text content
        text = soup.get_text()
        matches = br_pattern.findall(text)
        
        for match in matches:
            br_patent = f"BR{match}"
            if br_patent not in br_patents:
                br_patents.append(br_patent)
        
        return br_patents
    
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
        await self._close_session()
        logger.info("🧹 Google Patents crawler cleaned up")


async def test_google_patents():
    """Test function"""
    crawler = GooglePatentsCrawler()
    
    try:
        # Test WO search
        wo_numbers = await crawler.search_wo_numbers(
            molecule_name="Darolutamide",
            dev_codes=["ODM-201", "BAY-1841788"]
        )
        
        print(f"\n✅ Found {len(wo_numbers)} WO numbers:")
        for wo in wo_numbers:
            print(f"   - {wo}")
        
        # Test BR extraction from first WO
        if wo_numbers:
            success, br_patents = await crawler.get_wo_worldwide_applications(wo_numbers[0])
            print(f"\n✅ BR patents for {wo_numbers[0]}: {len(br_patents)}")
            for br in br_patents:
                print(f"   - {br}")
        
        # Print stats
        print(f"\n📊 Statistics:")
        stats = crawler.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
    finally:
        await crawler.cleanup()


if __name__ == "__main__":
    asyncio.run(test_google_patents())
