"""
Multi-Layer Orchestrator with Fallback Chain
Playwright → Selenium → HTTP (last resort)
"""
import logging
import time
from typing import Dict, List
from datetime import datetime

from app.services.pubchem import PubChemService
from app.services.playwright_crawler import PlaywrightStealthCrawler
from app.services.selenium_crawler import SeleniumStealthCrawler
from app.services.inpi import INPIService
from app.models.patent import MoleculeInfo
from app.utils.delays import HumanDelaySimulator

logger = logging.getLogger(__name__)


class MultiLayerOrchestrator:
    """
    Orchestrator with intelligent fallback
    Layer 1: Playwright (most stealth)
    Layer 2: Selenium (fallback)
    Layer 3: HTTP requests (last resort - already tried, doesn't work well)
    """
    
    def __init__(self):
        self.pubchem = PubChemService()
        self.inpi = INPIService()
        self.delays = HumanDelaySimulator()
    
    async def search(self, molecule_name: str, brand_name: str = None, target_countries: List[str] = None) -> Dict:
        """
        MULTI-LAYER STEALTH SEARCH
        """
        
        start_time = time.time()
        logger.info("=" * 70)
        logger.info(f"🚀 MULTI-LAYER STEALTH SEARCH: {molecule_name}")
        logger.info("=" * 70)
        
        # PHASE 1: PubChem
        logger.info("\n📊 PHASE 1: PubChem Intelligence")
        pubchem_data = self.pubchem.get_molecule_data(molecule_name)
        
        molecule_info = MoleculeInfo(
            name=molecule_name,
            brand=brand_name,
            cid=pubchem_data.get('cid'),
            cas=pubchem_data.get('cas'),
            molecular_formula=pubchem_data.get('molecular_formula'),
            molecular_weight=pubchem_data.get('molecular_weight'),
            dev_codes=pubchem_data.get('dev_codes', []),
            synonyms=pubchem_data.get('synonyms', [])[:20]
        )
        
        logger.info(f"  ✅ CID={molecule_info.cid}, {len(molecule_info.dev_codes)} dev codes, CAS={molecule_info.cas}")
        
        # PHASE 2: WO Discovery with Fallback Chain
        logger.info("\n🔍 PHASE 2: WO Discovery (Multi-Layer Fallback)")
        
        wo_numbers = []
        crawler_used = None
        
        # Try Layer 1: Playwright
        logger.info("  🎭 Layer 1: Trying Playwright Stealth...")
        try:
            async with PlaywrightStealthCrawler() as playwright:
                # Build search queries
                queries = self._build_search_queries(molecule_name, brand_name, molecule_info.dev_codes)
                
                for query in queries[:5]:  # Max 5 queries
                    wos = await playwright.search_patents(query, max_results=20)
                    wo_numbers.extend(wos)
                    
                    # Deduplicate
                    wo_numbers = list(dict.fromkeys(wo_numbers))
                    
                    if len(wo_numbers) >= 10:
                        break
                    
                    # Delay between queries
                    await self.delays.async_wait(self.delays.between_searches())
                
                if wo_numbers:
                    crawler_used = 'playwright'
                    logger.info(f"  ✅ Playwright SUCCESS: {len(wo_numbers)} WO numbers")
                else:
                    logger.warning("  ⚠️ Playwright found 0 WO numbers, trying Selenium...")
                    
        except Exception as e:
            logger.error(f"  ❌ Playwright failed: {str(e)}")
            logger.info("  🔄 Falling back to Selenium...")
        
        # Try Layer 2: Selenium (if Playwright failed)
        if not wo_numbers:
            logger.info("  🎭 Layer 2: Trying Selenium Stealth...")
            try:
                with SeleniumStealthCrawler() as selenium:
                    queries = self._build_search_queries(molecule_name, brand_name, molecule_info.dev_codes)
                    
                    for query in queries[:5]:
                        wos = selenium.search_patents(query, max_results=20)
                        wo_numbers.extend(wos)
                        
                        wo_numbers = list(dict.fromkeys(wo_numbers))
                        
                        if len(wo_numbers) >= 10:
                            break
                        
                        time.sleep(self.delays.between_searches())
                    
                    if wo_numbers:
                        crawler_used = 'selenium'
                        logger.info(f"  ✅ Selenium SUCCESS: {len(wo_numbers)} WO numbers")
                    else:
                        logger.warning("  ⚠️ Selenium also found 0 WO numbers")
                        
            except Exception as e:
                logger.error(f"  ❌ Selenium failed: {str(e)}")
        
        if not wo_numbers:
            logger.warning("  ⚠️ ALL CRAWLERS FAILED - No WO numbers found")
            logger.warning("  💡 Google may be blocking. Consider using SerpAPI as last resort.")
        
        # PHASE 3: BR Patent Collection
        logger.info("\n🇧🇷 PHASE 3: BR Patent Collection")
        
        all_br_patents = {}
        
        # Strategy 1: INPI Direct
        logger.info("  Strategy 1: INPI Direct Search")
        inpi_patents = self.inpi.search_patents(
            molecule=molecule_name,
            dev_codes=molecule_info.dev_codes[:2],
            brand=brand_name
        )
        
        for p in inpi_patents:
            pub_num = p['publication_number']
            if pub_num not in all_br_patents:
                all_br_patents[pub_num] = p
        
        logger.info(f"    ✅ INPI: {len(inpi_patents)} BR patents")
        
        # Strategy 2: BR from WO families (using successful crawler)
        google_wo_count = 0
        google_direct_count = 0
        
        if wo_numbers and crawler_used:
            logger.info(f"  Strategy 2: BR from WO Families (using {crawler_used})")
            
            if crawler_used == 'playwright':
                try:
                    async with PlaywrightStealthCrawler() as playwright:
                        for wo in wo_numbers[:10]:
                            br_patents = await playwright.get_br_patents_from_wo(wo)
                            
                            for p in br_patents:
                                pub_num = p['publication_number']
                                if pub_num not in all_br_patents:
                                    all_br_patents[pub_num] = p
                                    google_wo_count += 1
                            
                            await self.delays.async_wait(1.0)
                        
                        # Direct BR search
                        logger.info("  Strategy 3: Direct BR Search (Playwright)")
                        direct_br = await playwright.search_br_direct(molecule_name)
                        
                        for p in direct_br:
                            pub_num = p['publication_number']
                            if pub_num not in all_br_patents:
                                all_br_patents[pub_num] = p
                                google_direct_count += 1
                        
                except Exception as e:
                    logger.error(f"  ❌ Playwright BR extraction failed: {str(e)}")
            
            elif crawler_used == 'selenium':
                try:
                    with SeleniumStealthCrawler() as selenium:
                        for wo in wo_numbers[:10]:
                            br_patents = selenium.get_br_patents_from_wo(wo)
                            
                            for p in br_patents:
                                pub_num = p['publication_number']
                                if pub_num not in all_br_patents:
                                    all_br_patents[pub_num] = p
                                    google_wo_count += 1
                            
                            time.sleep(1.0)
                        
                        # Direct BR search
                        logger.info("  Strategy 3: Direct BR Search (Selenium)")
                        direct_br = selenium.search_br_direct(molecule_name)
                        
                        for p in direct_br:
                            pub_num = p['publication_number']
                            if pub_num not in all_br_patents:
                                all_br_patents[pub_num] = p
                                google_direct_count += 1
                        
                except Exception as e:
                    logger.error(f"  ❌ Selenium BR extraction failed: {str(e)}")
            
            logger.info(f"    ✅ Google WO Families: {google_wo_count} BR patents")
            logger.info(f"    ✅ Google Direct: {google_direct_count} BR patents")
        
        # PHASE 4: Results
        enriched_patents = list(all_br_patents.values())
        enriched_patents.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        by_source = {}
        for p in enriched_patents:
            src = p.get('source', 'unknown')
            by_source[src] = by_source.get(src, 0) + 1
        
        execution_time = time.time() - start_time
        
        logger.info("\n" + "=" * 70)
        logger.info(f"✅ MULTI-LAYER SEARCH COMPLETED")
        logger.info(f"  Crawler used: {crawler_used or 'NONE'}")
        logger.info(f"  WO numbers found: {len(wo_numbers)}")
        logger.info(f"  Total BR patents: {len(enriched_patents)}")
        logger.info(f"  By source: {by_source}")
        logger.info(f"  Execution time: {execution_time:.2f}s")
        logger.info("=" * 70)
        
        return {
            'molecule_info': molecule_info.dict(),
            'search_strategy': {
                'mode': 'multi_layer_stealth',
                'crawler_used': crawler_used or 'none',
                'layers': ['Playwright (stealth)', 'Selenium (fallback)', 'HTTP (last resort)'],
                'sources': ['PubChem', f'{crawler_used or "none"} Crawler', 'INPI Crawler'],
                'note': 'Anti-detection with user-agent rotation and human-like delays'
            },
            'wo_processing': {
                'total_wo_found': len(wo_numbers),
                'wo_numbers': wo_numbers[:20],
                'wo_processed': min(len(wo_numbers), 10)
            },
            'summary': {
                'total_br_patents': len(enriched_patents),
                'from_inpi': len(inpi_patents),
                'from_google_wo': google_wo_count,
                'from_google_direct': google_direct_count,
                'by_source': by_source
            },
            'br_patents': enriched_patents,
            'all_patents': enriched_patents,
            'comparison': {
                'expected': 8,
                'found': len(enriched_patents),
                'match_rate': f"{min(100, int((len(enriched_patents) / 8) * 100))}%",
                'status': '✅ Excellent' if len(enriched_patents) >= 8 else ('⚠️ Good' if len(enriched_patents) >= 4 else '❌ Low')
            },
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }
    
    def _build_search_queries(self, molecule: str, brand: str, dev_codes: List[str]) -> List[str]:
        """Build optimized search queries"""
        queries = [
            molecule,
            f"{molecule} patent",
            f"{molecule} pharmaceutical composition"
        ]
        
        if brand:
            queries.append(f"{brand} patent")
        
        if dev_codes:
            queries.extend([f"{code} patent" for code in dev_codes[:3]])
        
        return queries
