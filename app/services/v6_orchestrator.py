"""
V6 STEALTH Orchestrator - Production Ready
Integrates advanced anti-detection for Google Patents and WIPO
"""
import logging
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from app.services.pubchem import PubChemService
from app.services.google_patents import GooglePatentsCrawler
from app.services.wipo_search import WIPOCrawler
from app.services.inpi import INPIService
from app.models.patent import MoleculeInfo
from app.utils.delays import HumanDelaySimulator

logger = logging.getLogger(__name__)


class V6StealthOrchestrator:
    """
    Production-ready orchestrator with advanced anti-detection
    
    Search Strategy:
    1. PubChem: Get molecule intelligence (dev codes, CAS, synonyms)
    2. Google Patents: Find WO numbers with stealth techniques
    3. WIPO: Validate WO numbers and get BR applications
    4. INPI: Direct BR patent search
    5. Google Patents: Extract BR patents from WO families
    
    Anti-Detection Features:
    - Fingerprint randomization (canvas, WebGL, fonts, battery, etc.)
    - Correct Chrome header order with Client Hints
    - Session management with cookie persistence
    - Gaussian delays (15-30s for Google, lighter for others)
    - Circuit breaker pattern
    - User-Agent rotation
    - Multi-layer fallback
    """
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        
        # Services
        self.pubchem = PubChemService()
        self.google_patents = None  # Lazy init
        self.wipo = None  # Lazy init
        self.inpi = INPIService()
        self.delays = HumanDelaySimulator()
        
        # Statistics
        self.stats = {
            'total_searches': 0,
            'google_patents_success': 0,
            'google_patents_failures': 0,
            'wipo_success': 0,
            'wipo_failures': 0,
            'total_wo_found': 0,
            'total_br_found': 0
        }
    
    async def search(
        self,
        molecule_name: str,
        brand_name: Optional[str] = None,
        target_countries: Optional[List[str]] = None
    ) -> Dict:
        """
        Execute comprehensive patent search with stealth
        
        Args:
            molecule_name: Chemical name of molecule
            brand_name: Brand/commercial name
            target_countries: List of country codes (e.g., ['BR', 'US'])
        
        Returns:
            Complete search results with BR patents
        """
        self.stats['total_searches'] += 1
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info(f"🚀 V6 STEALTH SEARCH: {molecule_name}")
        logger.info("=" * 80)
        
        # PHASE 1: PubChem Intelligence
        logger.info("\n📊 PHASE 1: PubChem Molecular Intelligence")
        pubchem_data = await self._get_pubchem_data(molecule_name)
        
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
        
        logger.info(f"  ✅ CID: {molecule_info.cid}")
        logger.info(f"  ✅ CAS: {molecule_info.cas}")
        logger.info(f"  ✅ Dev Codes: {len(molecule_info.dev_codes)}")
        logger.info(f"  ✅ Synonyms: {len(molecule_info.synonyms)}")
        
        # PHASE 2: WO Discovery via Google Patents
        logger.info("\n🔍 PHASE 2: WO Discovery (Google Patents Stealth)")
        wo_numbers = await self._discover_wo_numbers(molecule_info)
        
        logger.info(f"  ✅ Total unique WO numbers: {len(wo_numbers)}")
        self.stats['total_wo_found'] += len(wo_numbers)
        
        # PHASE 3: WIPO Validation (Optional - can skip if Google worked well)
        logger.info("\n🌍 PHASE 3: WIPO Validation")
        wipo_br_apps = await self._get_wipo_br_applications(wo_numbers[:5])  # Validate first 5
        
        logger.info(f"  ✅ WIPO BR applications: {len(wipo_br_apps)}")
        
        # PHASE 4: BR Patent Collection
        logger.info("\n🇧🇷 PHASE 4: BR Patent Collection")
        
        all_br_patents = {}
        
        # Strategy 1: INPI Direct
        logger.info("  📍 Strategy 1: INPI Direct Search")
        inpi_patents = await self._search_inpi_direct(molecule_info)
        
        for p in inpi_patents:
            pub_num = p['publication_number']
            if pub_num not in all_br_patents:
                all_br_patents[pub_num] = p
        
        logger.info(f"    ✅ INPI Direct: {len(inpi_patents)} BR patents")
        
        # Strategy 2: BR from WO families (Google Patents)
        logger.info("  📍 Strategy 2: BR from WO Families")
        wo_br_patents = await self._extract_br_from_wo_families(wo_numbers)
        
        for p in wo_br_patents:
            pub_num = p['publication_number']
            if pub_num not in all_br_patents:
                all_br_patents[pub_num] = p
        
        logger.info(f"    ✅ WO Families: {len(wo_br_patents)} BR patents")
        
        # Strategy 3: WIPO BR applications
        for app in wipo_br_apps:
            if app not in all_br_patents:
                all_br_patents[app] = {
                    'publication_number': app,
                    'source': 'wipo',
                    'title': 'From WIPO national phase',
                    'score': 5
                }
        
        logger.info(f"    ✅ WIPO Apps: {len(wipo_br_apps)} BR applications")
        
        # PHASE 5: Results Compilation
        enriched_patents = list(all_br_patents.values())
        enriched_patents.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        self.stats['total_br_found'] += len(enriched_patents)
        
        # Statistics by source
        by_source = {}
        for p in enriched_patents:
            src = p.get('source', 'unknown')
            by_source[src] = by_source.get(src, 0) + 1
        
        execution_time = time.time() - start_time
        
        # Final Report
        logger.info("\n" + "=" * 80)
        logger.info("✅ V6 STEALTH SEARCH COMPLETED")
        logger.info(f"  Molecule: {molecule_name}")
        logger.info(f"  WO Numbers Found: {len(wo_numbers)}")
        logger.info(f"  BR Patents Found: {len(enriched_patents)}")
        logger.info(f"  By Source: {by_source}")
        logger.info(f"  Execution Time: {execution_time:.1f}s")
        logger.info(f"  Google Patents Success Rate: {self._calc_success_rate('google')}")
        logger.info(f"  WIPO Success Rate: {self._calc_success_rate('wipo')}")
        logger.info("=" * 80)
        
        return {
            'molecule_info': molecule_info.dict(),
            'search_strategy': {
                'mode': 'v6_stealth_production',
                'techniques': [
                    'Fingerprint randomization (canvas, WebGL, fonts, battery, screen, hardware)',
                    'Chrome header order with Client Hints',
                    'Session management with cookies',
                    'Gaussian delays (15-30s Google, lighter others)',
                    'Circuit breaker pattern',
                    'User-Agent rotation (30+ agents)',
                    'Multi-source WO discovery'
                ],
                'sources': ['PubChem', 'Google Patents (stealth)', 'WIPO', 'INPI'],
                'features': ['Advanced anti-detection', 'Multi-layer fallback', 'Rate limiting']
            },
            'wo_processing': {
                'total_wo_found': len(wo_numbers),
                'wo_numbers': wo_numbers,
                'wipo_validated': len(wipo_br_apps)
            },
            'summary': {
                'total_br_patents': len(enriched_patents),
                'by_source': by_source,
                'from_inpi': len(inpi_patents),
                'from_wo_families': len(wo_br_patents),
                'from_wipo': len(wipo_br_apps)
            },
            'br_patents': enriched_patents,
            'comparison': {
                'expected': 8,
                'found': len(enriched_patents),
                'match_rate': f"{min(100, int((len(enriched_patents) / 8) * 100))}%",
                'status': self._get_status(len(enriched_patents))
            },
            'statistics': self.stats,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _get_pubchem_data(self, molecule_name: str) -> Dict:
        """Get PubChem data"""
        try:
            return self.pubchem.get_molecule_data(molecule_name)
        except Exception as e:
            logger.error(f"❌ PubChem failed: {e}")
            return {}
    
    async def _discover_wo_numbers(self, molecule_info: MoleculeInfo) -> List[str]:
        """Discover WO numbers using Google Patents stealth"""
        try:
            # Initialize Google Patents crawler
            self.google_patents = GooglePatentsCrawler(proxy=self.proxy)
            
            # Search with molecule name and dev codes
            wo_numbers = await self.google_patents.search_wo_numbers(
                molecule_name=molecule_info.name,
                dev_codes=molecule_info.dev_codes,
                cas=molecule_info.cas
            )
            
            if wo_numbers:
                self.stats['google_patents_success'] += 1
            else:
                self.stats['google_patents_failures'] += 1
            
            return wo_numbers
            
        except Exception as e:
            logger.error(f"❌ Google Patents WO discovery failed: {e}")
            self.stats['google_patents_failures'] += 1
            return []
    
    async def _get_wipo_br_applications(self, wo_numbers: List[str]) -> List[str]:
        """Get BR applications from WIPO"""
        if not wo_numbers:
            return []
        
        try:
            # Initialize WIPO crawler
            self.wipo = WIPOCrawler(proxy=self.proxy)
            
            all_br_apps = []
            
            for wo in wo_numbers:
                br_apps = await self.wipo.get_br_applications(wo)
                all_br_apps.extend(br_apps)
                
                # Delay between WO queries
                await asyncio.sleep(2)
            
            if all_br_apps:
                self.stats['wipo_success'] += 1
            else:
                self.stats['wipo_failures'] += 1
            
            return list(set(all_br_apps))  # Deduplicate
            
        except Exception as e:
            logger.error(f"❌ WIPO BR applications failed: {e}")
            self.stats['wipo_failures'] += 1
            return []
    
    async def _search_inpi_direct(self, molecule_info: MoleculeInfo) -> List[Dict]:
        """Direct INPI search"""
        try:
            patents = self.inpi.search_patents(
                molecule=molecule_info.name,
                dev_codes=molecule_info.dev_codes[:2],
                brand=molecule_info.brand
            )
            return patents
        except Exception as e:
            logger.error(f"❌ INPI direct search failed: {e}")
            return []
    
    async def _extract_br_from_wo_families(self, wo_numbers: List[str]) -> List[Dict]:
        """Extract BR patents from WO families using Google Patents"""
        if not wo_numbers or not self.google_patents:
            return []
        
        all_br_patents = []
        
        try:
            # Process first 10 WO numbers (to avoid too many requests)
            for wo in wo_numbers[:10]:
                logger.info(f"    Processing {wo}...")
                
                success, br_patents = await self.google_patents.get_wo_worldwide_applications(wo)
                
                if success and br_patents:
                    for br_id in br_patents:
                        all_br_patents.append({
                            'publication_number': br_id,
                            'source': 'google_patents_wo_family',
                            'wo_number': wo,
                            'title': f'BR from {wo}',
                            'score': 7
                        })
                
                # Delay between WO processing (important!)
                await asyncio.sleep(2)
            
            return all_br_patents
            
        except Exception as e:
            logger.error(f"❌ BR extraction from WO families failed: {e}")
            return []
    
    def _calc_success_rate(self, service: str) -> str:
        """Calculate success rate for a service"""
        if service == 'google':
            total = self.stats['google_patents_success'] + self.stats['google_patents_failures']
            if total == 0:
                return 'N/A'
            rate = (self.stats['google_patents_success'] / total) * 100
            return f"{rate:.1f}%"
        
        elif service == 'wipo':
            total = self.stats['wipo_success'] + self.stats['wipo_failures']
            if total == 0:
                return 'N/A'
            rate = (self.stats['wipo_success'] / total) * 100
            return f"{rate:.1f}%"
        
        return 'N/A'
    
    def _get_status(self, count: int) -> str:
        """Get status based on BR patent count"""
        if count >= 8:
            return '✅ Excellent'
        elif count >= 4:
            return '⚠️ Good'
        else:
            return '❌ Low'
    
    async def cleanup(self):
        """Cleanup all resources"""
        if self.google_patents:
            await self.google_patents.cleanup()
        if self.wipo:
            await self.wipo.cleanup()
        
        logger.info("🧹 V6 Stealth Orchestrator cleaned up")


# Convenience function for FastAPI
async def execute_v6_search(
    molecule_name: str,
    brand_name: Optional[str] = None,
    proxy: Optional[str] = None
) -> Dict:
    """
    Execute V6 Stealth search
    
    Usage:
        result = await execute_v6_search("Darolutamide", "Nubeqa")
    """
    orchestrator = V6StealthOrchestrator(proxy=proxy)
    
    try:
        result = await orchestrator.search(molecule_name, brand_name)
        return result
    finally:
        await orchestrator.cleanup()
