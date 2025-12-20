"""
Selenium Stealth Crawler
Fallback when Playwright fails
Uses undetected-chromedriver for anti-detection
"""
import time
import re
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from app.utils.user_agents import UserAgentRotator
from app.utils.delays import HumanDelaySimulator, RetryStrategy
from app.utils.fingerprint import FingerprintRandomizer

logger = logging.getLogger(__name__)


class SeleniumStealthCrawler:
    """
    Selenium-based crawler with stealth mode
    Fallback option when Playwright fails
    """
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.delays = HumanDelaySimulator()
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def start(self):
        """Start Chrome with stealth options"""
        logger.info("🎭 Starting Selenium Stealth Driver...")
        
        options = webdriver.ChromeOptions()
        
        # Stealth arguments
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--window-size=1920,1080')
        
        # Random user agent
        user_agent = UserAgentRotator.get_desktop_chrome()
        options.add_argument(f'user-agent={user_agent}')
        
        # Experimental options to hide automation
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Disable logging
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        try:
            self.driver = webdriver.Chrome(options=options)
            
            # Execute CDP commands to hide webdriver
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent
            })
            
            # Apply COMPLETE fingerprint randomization
            full_stealth_script = FingerprintRandomizer.get_full_stealth_script()
            self.driver.execute_script(full_stealth_script)
            
            logger.info("✅ Selenium driver ready with advanced stealth")
            
        except Exception as e:
            logger.error(f"❌ Failed to start Selenium: {str(e)}")
            raise
    
    def close(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔴 Selenium driver closed")
    
    def search_patents(self, query: str, max_results: int = 20) -> List[str]:
        """
        Search Google Patents for WO numbers
        """
        logger.info(f"  🔍 Selenium: Searching '{query}'")
        
        retry = RetryStrategy(max_retries=3)
        wo_numbers = []
        
        while retry.should_retry() and len(wo_numbers) == 0:
            try:
                url = f"https://patents.google.com/?q={query}"
                logger.info(f"    Navigating to: {url}")
                
                self.driver.get(url)
                
                # Human-like wait
                time.sleep(self.delays.page_load())
                
                # Wait for results
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "search-result-item"))
                    )
                except TimeoutException:
                    logger.warning("    No search results found (timeout)")
                    
                    if retry.should_retry():
                        delay = retry.get_delay()
                        logger.info(f"    Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    continue
                
                # Get page source
                html = self.driver.page_source
                
                # Extract WO numbers
                wo_pattern = r'/patent/(WO\d{4}\d{6,7})'
                matches = re.findall(wo_pattern, html)
                
                for match in matches:
                    wo = match[:13]  # WO + year + 6 digits
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
                
                # Also search in plain text
                text_pattern = r'WO[\s-]?(\d{4})[\s/\-]?(\d{6,7})'
                text_matches = re.findall(text_pattern, html)
                
                for year, num in text_matches:
                    wo = f"WO{year}{num[:6]}"
                    if wo not in wo_numbers:
                        wo_numbers.append(wo)
                
                # Scroll for more results
                if len(wo_numbers) < max_results:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(self.delays.scroll())
                    
                    # Extract again
                    html = self.driver.page_source
                    matches = re.findall(wo_pattern, html)
                    for match in matches:
                        wo = match[:13]
                        if wo not in wo_numbers and len(wo_numbers) < max_results:
                            wo_numbers.append(wo)
                
                if wo_numbers:
                    logger.info(f"    ✅ Found {len(wo_numbers)} WO numbers")
                    retry.reset()
                else:
                    logger.warning(f"    ⚠️ No WO numbers found (attempt {retry.attempt + 1})")
                    
                    if retry.should_retry():
                        delay = retry.get_delay()
                        logger.info(f"    Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                
            except Exception as e:
                logger.error(f"    ❌ Error: {str(e)}")
                
                if retry.should_retry():
                    delay = retry.get_delay()
                    logger.info(f"    Retrying in {delay:.1f}s...")
                    time.sleep(delay)
        
        return wo_numbers[:max_results]
    
    def get_br_patents_from_wo(self, wo_number: str) -> List[Dict]:
        """
        Get BR patents from WO page
        """
        logger.info(f"  🔍 Selenium: Crawling WO {wo_number}")
        
        br_patents = []
        
        try:
            clean_wo = wo_number.replace(' ', '').replace('-', '')
            url = f"https://patents.google.com/patent/{clean_wo}"
            
            self.driver.get(url)
            time.sleep(self.delays.page_load())
            
            html = self.driver.page_source
            
            # Find BR patents
            br_pattern = r'/patent/(BR\d+[A-Z]\d?)'
            matches = re.findall(br_pattern, html)
            
            for br_num in matches:
                if not any(p['publication_number'] == br_num for p in br_patents):
                    br_patents.append({
                        'publication_number': br_num,
                        'title': f'Found in {wo_number} family',
                        'abstract': '',
                        'assignee': '',
                        'filing_date': '',
                        'patent_type': 'FAMILY_MEMBER',
                        'link': f"https://patents.google.com/patent/{br_num}",
                        'source': f'selenium_wo_{wo_number}',
                        'score': 8
                    })
            
            if br_patents:
                logger.info(f"    ✅ Found {len(br_patents)} BR patents")
            
        except Exception as e:
            logger.error(f"    ❌ Error: {str(e)}")
        
        return br_patents
    
    def search_br_direct(self, molecule: str) -> List[Dict]:
        """
        Direct BR search
        """
        logger.info(f"  🔍 Selenium: Direct BR search for '{molecule}'")
        
        br_patents = []
        
        try:
            url = f"https://patents.google.com/?q={molecule}+BR"
            self.driver.get(url)
            time.sleep(self.delays.page_load())
            
            html = self.driver.page_source
            
            br_pattern = r'/patent/(BR\d+[A-Z]\d?)'
            matches = re.findall(br_pattern, html)
            
            for br_num in matches:
                if not any(p['publication_number'] == br_num for p in br_patents):
                    br_patents.append({
                        'publication_number': br_num,
                        'title': 'BR Patent',
                        'abstract': '',
                        'assignee': '',
                        'filing_date': '',
                        'patent_type': 'DIRECT_SEARCH',
                        'link': f"https://patents.google.com/patent/{br_num}",
                        'source': 'selenium_direct',
                        'score': 9
                    })
            
            logger.info(f"    ✅ Direct: {len(br_patents)} BR patents")
            
        except Exception as e:
            logger.error(f"    ❌ Error: {str(e)}")
        
        return br_patents
