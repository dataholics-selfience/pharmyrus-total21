"""
Playwright Stealth Crawler
Advanced anti-detection techniques for Google Patents
"""
import asyncio
import re
import logging
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout

from app.utils.user_agents import UserAgentRotator
from app.utils.delays import HumanDelaySimulator, RetryStrategy
from app.utils.fingerprint import FingerprintRandomizer

logger = logging.getLogger(__name__)


class PlaywrightStealthCrawler:
    """
    Stealth crawler using Playwright
    Anti-detection techniques:
    - Real browser (Chromium)
    - Randomized user agents
    - Human-like delays
    - Stealth plugins
    - CDP commands to hide automation
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.delays = HumanDelaySimulator()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Start browser with stealth mode"""
        logger.info("🎭 Starting Playwright Stealth Browser...")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser with stealth args
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--disable-extensions',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-ipc-flooding-protection',
            ]
        )
        
        # Create context with realistic settings
        context_args = UserAgentRotator.get_playwright_context_args()
        self.context = await self.browser.new_context(**context_args)
        
        # Add stealth scripts via CDP
        await self._apply_stealth_scripts(self.context)
        
        logger.info("✅ Playwright browser ready")
    
    async def _apply_stealth_scripts(self, context: BrowserContext):
        """
        Apply ADVANCED stealth scripts to hide automation
        Uses CDP (Chrome DevTools Protocol) commands
        Includes fingerprint randomization
        """
        # Get complete stealth script with ALL randomizations
        full_stealth_script = FingerprintRandomizer.get_full_stealth_script()
        
        await context.add_init_script(full_stealth_script)
        
        logger.info("  ✅ Applied advanced fingerprint randomization")
    
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("🔴 Playwright browser closed")
    
    async def search_patents(self, query: str, max_results: int = 20) -> List[str]:
        """
        Search Google Patents and extract WO numbers
        Returns list of WO patent numbers
        """
        logger.info(f"  🔍 Playwright: Searching '{query}'")
        
        retry = RetryStrategy(max_retries=3)
        wo_numbers = []
        
        while retry.should_retry() and len(wo_numbers) == 0:
            try:
                page = await self.context.new_page()
                
                # Navigate to Google Patents
                url = f"https://patents.google.com/?q={query}"
                
                logger.info(f"    Navigating to: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for page load (human-like)
                await asyncio.sleep(self.delays.page_load())
                
                # Wait for search results
                try:
                    await page.wait_for_selector('search-result-item', timeout=10000)
                except PlaywrightTimeout:
                    logger.warning("    No search results found (timeout)")
                    await page.close()
                    
                    if retry.should_retry():
                        delay = retry.get_delay()
                        logger.info(f"    Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    continue
                
                # Extract WO numbers from page
                html = await page.content()
                
                # Strategy 1: Find WO in links
                links = await page.query_selector_all('a[href*="/patent/WO"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        match = re.search(r'/patent/(WO\d{4}\d{6,7})', href)
                        if match:
                            wo = match.group(1)[:13]  # WO + year + 6 digits
                            if wo not in wo_numbers:
                                wo_numbers.append(wo)
                
                # Strategy 2: Find WO in text
                wo_pattern = r'WO[\s-]?(\d{4})[\s/\-]?(\d{6,7})'
                matches = re.findall(wo_pattern, html)
                for year, num in matches:
                    wo = f"WO{year}{num[:6]}"
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
                
                # Scroll to load more results
                if len(wo_numbers) < max_results:
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(self.delays.scroll())
                    
                    # Extract again after scroll
                    html = await page.content()
                    matches = re.findall(wo_pattern, html)
                    for year, num in matches:
                        wo = f"WO{year}{num[:6]}"
                        if wo not in wo_numbers and len(wo_numbers) < max_results:
                            wo_numbers.append(wo)
                
                await page.close()
                
                if wo_numbers:
                    logger.info(f"    ✅ Found {len(wo_numbers)} WO numbers")
                    retry.reset()
                else:
                    logger.warning(f"    ⚠️ No WO numbers found (attempt {retry.attempt + 1})")
                    
                    if retry.should_retry():
                        delay = retry.get_delay()
                        logger.info(f"    Retrying with different approach in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"    ❌ Error: {str(e)}")
                
                if retry.should_retry():
                    delay = retry.get_delay()
                    logger.info(f"    Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    break
        
        return wo_numbers[:max_results]
    
    async def get_br_patents_from_wo(self, wo_number: str) -> List[Dict]:
        """
        Get BR patents from WO patent page
        Scrapes worldwide applications section
        """
        logger.info(f"  🔍 Playwright: Crawling WO {wo_number}")
        
        retry = RetryStrategy(max_retries=2)
        br_patents = []
        
        while retry.should_retry() and len(br_patents) == 0:
            try:
                page = await self.context.new_page()
                
                # Clean WO number
                clean_wo = wo_number.replace(' ', '').replace('-', '')
                url = f"https://patents.google.com/patent/{clean_wo}"
                
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(self.delays.page_load())
                
                # Look for BR patents in family
                html = await page.content()
                
                # Find all BR patent links
                links = await page.query_selector_all('a[href*="/patent/BR"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        match = re.search(r'/patent/(BR\d+[A-Z]\d?)', href)
                        if match:
                            br_num = match.group(1)
                            
                            # Get title from link or nearby text
                            title = await link.inner_text() or 'Patent family member'
                            
                            if not any(p['publication_number'] == br_num for p in br_patents):
                                br_patents.append({
                                    'publication_number': br_num,
                                    'title': title[:200],
                                    'abstract': '',
                                    'assignee': '',
                                    'filing_date': '',
                                    'patent_type': 'FAMILY_MEMBER',
                                    'link': f"https://patents.google.com/patent/{br_num}",
                                    'source': f'playwright_wo_{wo_number}',
                                    'score': 9
                                })
                
                # Also search in text
                br_pattern = r'BR[\s-]?(\d{12,13}[A-Z]\d?)'
                matches = re.findall(br_pattern, html)
                for match in matches:
                    br_num = f"BR{match}"
                    if not any(p['publication_number'] == br_num for p in br_patents):
                        br_patents.append({
                            'publication_number': br_num,
                            'title': f'Found in {wo_number} family',
                            'abstract': '',
                            'assignee': '',
                            'filing_date': '',
                            'patent_type': 'FAMILY_MEMBER',
                            'link': f"https://patents.google.com/patent/{br_num}",
                            'source': f'playwright_wo_{wo_number}',
                            'score': 8
                        })
                
                await page.close()
                
                if br_patents:
                    logger.info(f"    ✅ Found {len(br_patents)} BR patents")
                
            except Exception as e:
                logger.error(f"    ❌ Error crawling {wo_number}: {str(e)}")
                
                if retry.should_retry():
                    delay = retry.get_delay()
                    await asyncio.sleep(delay)
        
        return br_patents
    
    async def search_br_direct(self, molecule: str) -> List[Dict]:
        """
        Direct search for BR patents
        """
        logger.info(f"  🔍 Playwright: Direct BR search for '{molecule}'")
        
        br_patents = []
        
        try:
            page = await self.context.new_page()
            
            url = f"https://patents.google.com/?q={molecule}+BR"
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(self.delays.page_load())
            
            # Find BR patent links
            links = await page.query_selector_all('a[href*="/patent/BR"]')
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    match = re.search(r'/patent/(BR\d+[A-Z]\d?)', href)
                    if match:
                        br_num = match.group(1)
                        title = await link.inner_text() or 'BR Patent'
                        
                        if not any(p['publication_number'] == br_num for p in br_patents):
                            br_patents.append({
                                'publication_number': br_num,
                                'title': title[:200],
                                'abstract': '',
                                'assignee': '',
                                'filing_date': '',
                                'patent_type': 'DIRECT_SEARCH',
                                'link': f"https://patents.google.com/patent/{br_num}",
                                'source': 'playwright_direct',
                                'score': 10
                            })
            
            await page.close()
            
            logger.info(f"    ✅ Direct: {len(br_patents)} BR patents")
            
        except Exception as e:
            logger.error(f"    ❌ Direct search error: {str(e)}")
        
        return br_patents
