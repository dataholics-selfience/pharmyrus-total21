"""
Crawler Manager - Multi-Layer Orchestrator with Auto-Fallback

Layer Strategy:
1. Playwright (Highest stealth, slowest) - Try first for Google Patents
2. HTTPX (Fast, medium stealth) - Fallback or primary for WIPO
3. Selenium (Robust fallback) - Last resort

Features:
- Automatic fallback on failure
- Circuit breaker per layer
- Smart layer selection based on target
- Comprehensive metrics
"""
import asyncio
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

from app.crawlers.base_crawler import BaseCrawler, CrawlerLayer
from app.crawlers.playwright_crawler import PlaywrightCrawler
from app.crawlers.httpx_crawler import HTTPXCrawler
from app.crawlers.selenium_crawler import SeleniumCrawler

logger = logging.getLogger(__name__)


class TargetSite(Enum):
    """Target sites with different requirements"""
    GOOGLE_PATENTS = "google_patents"  # Needs high stealth
    WIPO = "wipo"                      # Lighter protection
    INPI = "inpi"                      # Minimal protection


class CrawlerManager:
    """
    Intelligent multi-layer crawler manager
    
    Strategies:
    - Google Patents: Playwright → Selenium → HTTPX (stealth priority)
    - WIPO: HTTPX → Playwright → Selenium (speed priority)
    - INPI: HTTPX → Playwright → Selenium (speed priority)
    """
    
    def __init__(self):
        # Initialize all crawlers
        self.crawlers: Dict[CrawlerLayer, BaseCrawler] = {
            CrawlerLayer.PLAYWRIGHT: PlaywrightCrawler(),
            CrawlerLayer.HTTPX: HTTPXCrawler(),
            CrawlerLayer.SELENIUM: SeleniumCrawler(),
        }
        
        # Layer strategies per target
        self.strategies = {
            TargetSite.GOOGLE_PATENTS: [
                CrawlerLayer.PLAYWRIGHT,
                CrawlerLayer.SELENIUM,
                CrawlerLayer.HTTPX
            ],
            TargetSite.WIPO: [
                CrawlerLayer.HTTPX,
                CrawlerLayer.PLAYWRIGHT,
                CrawlerLayer.SELENIUM
            ],
            TargetSite.INPI: [
                CrawlerLayer.HTTPX,
                CrawlerLayer.PLAYWRIGHT,
                CrawlerLayer.SELENIUM
            ]
        }
        
        # Global metrics
        self.total_requests = 0
        self.total_successes = 0
        self.total_failures = 0
        self.layer_usage = {layer: 0 for layer in CrawlerLayer}
        self.layer_successes = {layer: 0 for layer in CrawlerLayer}
        
        logger.info("🎯 CrawlerManager initialized with 3 layers")
    
    async def search_wo_numbers(
        self,
        query: str,
        target: TargetSite = TargetSite.GOOGLE_PATENTS,
        max_results: int = 20
    ) -> Tuple[List[str], str]:
        """
        Search for WO numbers with automatic fallback
        
        Args:
            query: Search query
            target: Target site (determines layer strategy)
            max_results: Maximum results to return
        
        Returns:
            Tuple of (wo_numbers, layer_used)
        """
        logger.info(f"🔍 CrawlerManager: Searching WO numbers for '{query}' on {target.value}")
        
        strategy = self.strategies[target]
        
        for layer in strategy:
            crawler = self.crawlers[layer]
            
            if not crawler.is_available():
                logger.warning(f"   ⏭️  Skipping {crawler.name} (not available)")
                continue
            
            logger.info(f"   🎯 Trying {crawler.name}...")
            
            self.total_requests += 1
            self.layer_usage[layer] += 1
            
            try:
                wo_numbers = await crawler.search_patents(query, max_results)
                
                if wo_numbers:
                    self.total_successes += 1
                    self.layer_successes[layer] += 1
                    
                    logger.info(
                        f"   ✅ {crawler.name} SUCCESS: {len(wo_numbers)} WO numbers "
                        f"(success rate: {crawler.get_success_rate():.1f}%)"
                    )
                    
                    return wo_numbers, crawler.name
                else:
                    logger.warning(f"   ⚠️  {crawler.name} returned empty results, trying next layer...")
                    
            except Exception as e:
                logger.error(f"   ❌ {crawler.name} error: {e}, trying next layer...")
        
        # All layers failed
        self.total_failures += 1
        logger.error(f"❌ CrawlerManager: All layers failed for '{query}'")
        
        return [], "none"
    
    async def get_patent_details(
        self,
        wo_number: str,
        target: TargetSite = TargetSite.GOOGLE_PATENTS
    ) -> Tuple[Optional[Dict], str]:
        """
        Get patent details with automatic fallback
        
        Returns:
            Tuple of (details, layer_used)
        """
        logger.info(f"📄 CrawlerManager: Getting details for {wo_number}")
        
        strategy = self.strategies[target]
        
        for layer in strategy:
            crawler = self.crawlers[layer]
            
            if not crawler.is_available():
                continue
            
            logger.info(f"   🎯 Trying {crawler.name}...")
            
            self.layer_usage[layer] += 1
            
            try:
                details = await crawler.get_patent_details(wo_number)
                
                if details:
                    self.layer_successes[layer] += 1
                    logger.info(f"   ✅ {crawler.name} SUCCESS")
                    return details, crawler.name
                    
            except Exception as e:
                logger.error(f"   ❌ {crawler.name} error: {e}")
        
        logger.error(f"❌ CrawlerManager: All layers failed for {wo_number}")
        return None, "none"
    
    async def get_br_patents_from_wo(
        self,
        wo_number: str,
        target: TargetSite = TargetSite.GOOGLE_PATENTS
    ) -> Tuple[List[str], str]:
        """
        Get BR patents from WO family with automatic fallback
        
        Returns:
            Tuple of (br_patents, layer_used)
        """
        logger.info(f"🇧🇷 CrawlerManager: Getting BR patents for {wo_number}")
        
        strategy = self.strategies[target]
        
        for layer in strategy:
            crawler = self.crawlers[layer]
            
            if not crawler.is_available():
                continue
            
            logger.info(f"   🎯 Trying {crawler.name}...")
            
            self.layer_usage[layer] += 1
            
            try:
                br_patents = await crawler.get_br_patents_from_wo(wo_number)
                
                if br_patents:
                    self.layer_successes[layer] += 1
                    logger.info(f"   ✅ {crawler.name} SUCCESS: {len(br_patents)} BR patents")
                    return br_patents, crawler.name
                    
            except Exception as e:
                logger.error(f"   ❌ {crawler.name} error: {e}")
        
        logger.warning(f"⚠️  CrawlerManager: No BR patents found for {wo_number}")
        return [], "none"
    
    async def search_wo_numbers_multi_query(
        self,
        queries: List[str],
        target: TargetSite = TargetSite.GOOGLE_PATENTS,
        max_results_per_query: int = 10
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Search multiple queries and deduplicate results
        
        Args:
            queries: List of search queries
            target: Target site
            max_results_per_query: Max results per query
        
        Returns:
            Tuple of (unique_wo_numbers, layer_usage_count)
        """
        logger.info(f"🔍 CrawlerManager: Multi-query search ({len(queries)} queries)")
        
        all_wo_numbers = set()
        layer_usage_count = {}
        
        for i, query in enumerate(queries, 1):
            logger.info(f"   Query {i}/{len(queries)}: '{query}'")
            
            wo_numbers, layer_used = await self.search_wo_numbers(
                query,
                target,
                max_results_per_query
            )
            
            # Track layer usage
            layer_usage_count[layer_used] = layer_usage_count.get(layer_used, 0) + 1
            
            # Add to set (auto-deduplication)
            all_wo_numbers.update(wo_numbers)
            
            logger.info(f"      Found {len(wo_numbers)} WO numbers (total unique: {len(all_wo_numbers)})")
            
            # Small delay between queries
            await asyncio.sleep(0.5)
        
        unique_list = sorted(list(all_wo_numbers))
        
        logger.info(f"✅ Multi-query complete: {len(unique_list)} unique WO numbers")
        logger.info(f"   Layer usage: {layer_usage_count}")
        
        return unique_list, layer_usage_count
    
    def get_all_metrics(self) -> Dict:
        """Get comprehensive metrics from all layers"""
        return {
            'manager': {
                'total_requests': self.total_requests,
                'total_successes': self.total_successes,
                'total_failures': self.total_failures,
                'success_rate': f"{(self.total_successes / max(1, self.total_requests)) * 100:.1f}%",
                'layer_usage': {
                    layer.name: count for layer, count in self.layer_usage.items()
                },
                'layer_successes': {
                    layer.name: count for layer, count in self.layer_successes.items()
                }
            },
            'layers': {
                layer.name: crawler.get_metrics()
                for layer, crawler in self.crawlers.items()
            }
        }
    
    async def cleanup_all(self):
        """Cleanup all crawlers"""
        logger.info("🧹 CrawlerManager: Cleaning up all layers...")
        
        for crawler in self.crawlers.values():
            try:
                await crawler.cleanup()
            except Exception as e:
                logger.error(f"   Error cleaning up {crawler.name}: {e}")
        
        logger.info("✅ CrawlerManager: All layers cleaned up")
    
    def print_statistics(self):
        """Print beautiful statistics"""
        print("\n" + "="*80)
        print("📊 CRAWLER MANAGER STATISTICS")
        print("="*80)
        
        # Manager stats
        print(f"\n🎯 MANAGER:")
        print(f"   Total Requests: {self.total_requests}")
        print(f"   Successes: {self.total_successes}")
        print(f"   Failures: {self.total_failures}")
        
        if self.total_requests > 0:
            success_rate = (self.total_successes / self.total_requests) * 100
            print(f"   Success Rate: {success_rate:.1f}%")
        
        print(f"\n📈 LAYER USAGE:")
        for layer, count in self.layer_usage.items():
            successes = self.layer_successes[layer]
            rate = (successes / count * 100) if count > 0 else 0
            print(f"   {layer.name:12} - Used: {count:3} times | Successes: {successes:3} ({rate:.1f}%)")
        
        # Individual crawler stats
        print(f"\n🔧 CRAWLER DETAILS:")
        for layer, crawler in self.crawlers.items():
            metrics = crawler.get_metrics()
            print(f"\n   {layer.name} ({metrics['status']}):")
            print(f"      Requests: {metrics['total_requests']}")
            print(f"      Success Rate: {metrics['success_rate']}")
            print(f"      Avg Response Time: {metrics['avg_response_time']:.2f}s")
            
            if metrics['circuit_breaker']['is_open']:
                print(f"      ⛔ Circuit OPEN (cooldown: {metrics['circuit_breaker']['cooldown_remaining']}s)")
        
        print("\n" + "="*80 + "\n")
