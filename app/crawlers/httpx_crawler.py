"""
HTTPX Crawler - Layer 2 (Fast with Medium Stealth)
"""
import asyncio
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
import re
import logging

from app.crawlers.base_crawler import BaseCrawler, CrawlerLayer, CrawlerStatus
from app.utils.user_agents import UserAgentRotator
from app.utils.delays import DelayManager

logger = logging.getLogger(__name__)


class HTTPXCrawler(BaseCrawler):
    """
    Layer 2: HTTPX with advanced headers
    
    Pros:
    - Fast (100-300ms per request)
    - Low resource usage
    - Good for WIPO and lighter sites
    
    Cons:
    - No JavaScript rendering
    - Lower stealth than Playwright
    - May miss dynamic content
    """
    
    GOOGLE_PATENTS_URL = "https://patents.google.com"
    WIPO_API_URL = "https://patentscope.wipo.int/search/rest/patents"
    
    def __init__(self):
        super().__init__("HTTPX", CrawlerLayer.HTTPX)
        
        self.ua_rotator = UserAgentRotator()
        self.delay_manager = DelayManager()
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
        self.current_user_agent = None
        
        # Session management
        self.session_start_time = 0
        self.max_session_duration = 300  # 5 minutes
        self.requests_in_session = 0
        self.max_requests_per_session = 50
    
    async def initialize(self):
        """Initialize HTTP client"""
        if self.client:
            return
        
        logger.info(f"⚡ {self.name}: Initializing HTTP client...")
        
        try:
            # Get User-Agent
            self.current_user_agent = self.ua_rotator.get_random()
            logger.info(f"   User-Agent: {self.current_user_agent[:80]}...")
            
            # Create client
            self.client = httpx.AsyncClient(
                headers=self._get_headers(),
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10
                )
            )
            
            self.session_start_time = time.time()
            self.requests_in_session = 0
            self.status = CrawlerStatus.READY
            
            logger.info(f"✅ {self.name}: HTTP client initialized")
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Initialization failed: {e}")
            self.status = CrawlerStatus.FAILED
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Generate Chrome-like headers
        
        IMPORTANT: Header order matters for detection!
        """
        # Extract Chrome version
        chrome_version = "131"
        if "Chrome/" in self.current_user_agent:
            try:
                chrome_version = self.current_user_agent.split("Chrome/")[1].split(".")[0]
            except:
                pass
        
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.current_user_agent,
            'sec-ch-ua': f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not=A?Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
    
    async def _check_session_renewal(self):
        """Check if session needs renewal"""
        should_renew = (
            time.time() - self.session_start_time > self.max_session_duration or
            self.requests_in_session >= self.max_requests_per_session
        )
        
        if should_renew:
            logger.info(f"🔄 {self.name}: Renewing session...")
            await self.cleanup()
            await self.initialize()
    
    async def cleanup(self):
        """Cleanup HTTP client"""
        try:
            if self.client:
                await self.client.aclose()
                self.client = None
            
            logger.info(f"🧹 {self.name}: Cleaned up")
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Cleanup error: {e}")
    
    async def search_patents(self, query: str, max_results: int = 20) -> List[str]:
        """Search Google Patents via HTTP"""
        if not self.is_available():
            logger.warning(f"⛔ {self.name}: Not available (circuit open)")
            return []
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_renewal()
            
            logger.info(f"🔍 {self.name}: Searching '{query}'")
            
            # Request
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={quote_plus(query)}"
            
            response = await self.client.get(search_url)
            self.requests_in_session += 1
            
            # Check status
            if response.status_code != 200:
                logger.warning(f"⚠️  {self.name}: Status {response.status_code}")
                self.record_failure()
                return []
            
            # Check for blocking
            content = response.text
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
            
        except httpx.TimeoutException:
            logger.error(f"⏱️  {self.name}: Request timeout")
            self.record_failure()
            return []
        except Exception as e:
            logger.error(f"❌ {self.name}: Search failed: {e}")
            self.record_failure()
            return []
    
    async def get_patent_details(self, wo_number: str) -> Optional[Dict]:
        """Get patent details via HTTP"""
        if not self.is_available():
            return None
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_renewal()
            
            logger.info(f"📄 {self.name}: Getting details for {wo_number}")
            
            # Try WIPO API first (faster and more reliable for WO numbers)
            wo_clean = wo_number.replace('WO', '').replace(' ', '').replace('-', '')
            api_url = f"{self.WIPO_API_URL}?query={wo_clean}&offset=0&limit=1"
            
            response = await self.client.get(api_url)
            self.requests_in_session += 1
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data and len(data['results']) > 0:
                    patent = data['results'][0]
                    
                    details = {
                        'wo_number': wo_number,
                        'title': patent.get('EN_TI', 'Unknown'),
                        'abstract': patent.get('EN_AB', '')[:500],
                        'publication_date': patent.get('PD', ''),
                        'source': 'httpx_wipo_api'
                    }
                    
                    response_time = time.time() - start_time
                    self.record_success(response_time)
                    
                    return details
            
            # Fallback: Try Google Patents
            search_url = f"{self.GOOGLE_PATENTS_URL}/?q={wo_number}"
            response = await self.client.get(search_url)
            self.requests_in_session += 1
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                details = self._parse_patent_details(soup, wo_number)
                
                response_time = time.time() - start_time
                self.record_success(response_time)
                
                return details
            
            self.record_failure()
            return None
            
        except Exception as e:
            logger.error(f"❌ {self.name}: Get details failed: {e}")
            self.record_failure()
            return None
    
    async def get_br_patents_from_wo(self, wo_number: str) -> List[str]:
        """Get BR patents from WO (limited with HTTP - no JS rendering)"""
        if not self.is_available():
            return []
        
        start_time = time.time()
        
        try:
            await self.initialize()
            await self._check_session_renewal()
            
            logger.info(f"🇧🇷 {self.name}: Getting BR patents for {wo_number}")
            
            # Try WIPO API for national phase info
            wo_clean = wo_number.replace('WO', '').replace(' ', '').replace('-', '')
            api_url = f"{self.WIPO_API_URL}?query={wo_clean}"
            
            response = await self.client.get(api_url)
            self.requests_in_session += 1
            
            br_patents = []
            
            if response.status_code == 200:
                data = response.json()
                
                # Look for national phase entries
                if 'results' in data and len(data['results']) > 0:
                    patent = data['results'][0]
                    
                    # Check for BR in designated states or national phase
                    if 'nationalPhase' in patent:
                        for entry in patent['nationalPhase']:
                            if entry.get('country') == 'BR':
                                app_number = entry.get('applicationNumber')
                                if app_number:
                                    br_patents.append(app_number)
            
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
            'forbidden'
        ]
        
        content_lower = content.lower()
        for indicator in block_indicators:
            if indicator in content_lower:
                return True
        
        if len(content) < 500:
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
                'source': 'httpx_google'
            }
        except:
            return {
                'wo_number': wo_number,
                'title': 'Parse error',
                'source': 'httpx'
            }
