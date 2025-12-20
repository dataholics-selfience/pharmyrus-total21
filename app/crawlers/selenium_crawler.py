"""
Selenium Crawler - Layer 3 (Robust Fallback)
"""
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re
import logging
import asyncio

from app.crawlers.base_crawler import BaseCrawler, CrawlerLayer, CrawlerStatus
from app.utils.user_agents import UserAgentRotator
from app.utils.fingerprint import FingerprintRandomizer

logger = logging.getLogger(__name__)


class SeleniumCrawler(BaseCrawler):
    """
    Layer 3: Selenium with undetected-chromedriver
    
    Pros:
    - High compatibility
    - Robust against changes
    - Good fallback option
    
    Cons:
    - Slowest (1-3s per page)
    - Highest resource usage
    - More detectable than Playwright
    """
    
    GOOGLE_PATENTS_URL = "https://patents.google.com"
    
    def __init__(self):
        super().__init__("Selenium", CrawlerLayer.SELENIUM)
        
        self.ua_rotator = UserAgentRotator()
        self.fingerprint = FingerprintRandomizer()
        
        # Selenium resources
        self.driver: Optional[webdriver.Chrome] = None
        self.current_user_agent = None
        
        # Session
        self.session_start_time = 0
        self.max_session_duration = 600  # 10 minutes
    
    async def initialize(self):
        """Initialize Selenium driver"""
        if self.driver:
            return
        
        logger.info(f"🎬 {self.name}: Initializing Selenium driver...")
        
        try:
            # Get User-Agent
            self.current_user_agent = self.ua_rotator.get_random()
            logger.info(f"   User-Agent: {self.current_user_agent[:80]}...")
            
            # Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument(f'user-agent={self.current_user_agent}')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            
            # Experimental options
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Apply stealth scripts
            self.driver.execute_script(self.fingerprint.get_full_stealth_script())
            
            self.session_start_time = time.time()
            self.status = CrawlerStatus.READY
            
            logger.info(f"✅ {self.name}: Driver initialized")
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Initialization failed: {e}")
            self.status = CrawlerStatus.FAILED
            raise
    
    async def _check_session_age(self):
        """Check if session needs renewal"""
        if time.time() - self.session_start_time > self.max_session_duration:
            logger.info(f"🔄 {self.name}: Session expired, renewing...")
            await self.cleanup()
            await self.initialize()
    
    async def cleanup(self):
        """Cleanup Selenium driver"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
            
            logger.info(f"🧹 {self.name}: Cleaned up")
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Cleanup error: {e}")
    
    async def search_patents(self, query: str, max_results: int = 20) -> List[str]:
        """Search Google Patents with Selenium"""
        if not self.is_available():
            logger.warning(f"⛔ {self.name}: Not available (circuit open)")
            return []
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_age()
            
            logger.info(f"🔍 {self.name}: Searching '{query}'")
            
            # Navigate
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={quote_plus(query)}"
            self.driver.get(search_url)
            
            # Wait for content
            await asyncio.sleep(3)
            
            # Get content
            content = self.driver.page_source
            
            # Check for blocking
            if self._detect_block(content):
                logger.error(f"🚫 {self.name}: BLOCKED")
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
            
            # Navigate
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={wo_number}"
            self.driver.get(search_url)
            
            await asyncio.sleep(2)
            
            # Click first result
            try:
                first_result = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'search-result-item'))
                )
                first_result.click()
                await asyncio.sleep(2)
            except:
                logger.warning(f"   Could not click result for {wo_number}")
                return None
            
            # Parse
            content = self.driver.page_source
            soup = BeautifulSoup(content, 'html.parser')
            
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
            
            # Navigate
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={wo_number}"
            self.driver.get(search_url)
            
            await asyncio.sleep(2)
            
            # Click first result
            try:
                first_result = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'search-result-item'))
                )
                first_result.click()
                await asyncio.sleep(3)
            except:
                return []
            
            # Extract BR patents
            content = self.driver.page_source
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
            'access denied'
        ]
        
        content_lower = content.lower()
        for indicator in block_indicators:
            if indicator in content_lower:
                return True
        
        if len(content) < 1000:
            return True
        
        return False
    
    def _extract_wo_numbers(self, content: str) -> List[str]:
        """Extract WO numbers"""
        wo_numbers = set()
        wo_pattern = re.compile(r'WO[\s-]?(\d{4})[\s/]?(\d{6})', re.IGNORECASE)
        
        matches = wo_pattern.findall(content)
        for year, number in matches:
            wo = f"WO{year}{number}"
            wo_numbers.add(wo)
        
        return sorted(list(wo_numbers))
    
    def _extract_br_patents(self, soup: BeautifulSoup) -> List[str]:
        """Extract BR patent numbers"""
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
        """Parse patent details"""
        try:
            title_elem = soup.find('meta', {'name': 'citation_title'})
            title = title_elem['content'] if title_elem else 'Unknown'
            
            abstract_elem = soup.find('meta', {'name': 'description'})
            abstract = abstract_elem['content'] if abstract_elem else ''
            
            return {
                'wo_number': wo_number,
                'title': title,
                'abstract': abstract[:500],
                'source': 'selenium'
            }
        except:
            return {
                'wo_number': wo_number,
                'title': 'Parse error',
                'source': 'selenium'
            }
