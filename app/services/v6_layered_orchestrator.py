"""
V6 LAYERED Orchestrator - Multi-Layer Crawler System

Complete pipeline with intelligent layer selection:
1. PubChem: Get molecule data (CID, CAS, dev codes, synonyms)
2. Multi-Layer WO Discovery: Search WO numbers with auto-fallback
3. WO to BR Conversion: Extract BR patents from WO families
4. INPI Direct Search: Additional BR patents via Railway API
5. Deduplication & Enrichment: Final BR patent list

Architecture:
- CrawlerManager: Intelligent 3-layer system (Playwright → HTTPX → Selenium)
- Automatic fallback on failure or blocking
- Circuit breaker per layer
- Smart layer selection based on target site
"""
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

from app.services.pubchem import get_molecule_data
from app.crawlers import CrawlerManager, TargetSite

logger = logging.getLogger(__name__)


class V6LayeredOrchestrator:
    """
    Production orchestrator with multi-layer crawler system
    
    Features:
    - 3-layer crawler architecture with auto-fallback
    - Smart layer selection (stealth vs speed)
    - Circuit breaker protection
    - Comprehensive metrics
    """
    
    def __init__(self):
        self.crawler_manager = CrawlerManager()
        self.inpi_api_url = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
    
    async def search(
        self,
        molecule_name: str,
        brand_name: Optional[str] = None,
        target_countries: List[str] = None
    ) -> Dict:
        """
        Complete patent search pipeline
        
        Args:
            molecule_name: Chemical name (e.g., "Darolutamide")
            brand_name: Commercial name (e.g., "Nubeqa")
            target_countries: List of target countries (default: ["BR"])
        
        Returns:
            Complete search results with BR patents
        """
        start_time = time.time()
        
        if not target_countries:
            target_countries = ["BR"]
        
        logger.info("="*80)
        logger.info(f"🚀 V6 LAYERED SEARCH START")
        logger.info(f"   Molecule: {molecule_name}")
        logger.info(f"   Brand: {brand_name or 'N/A'}")
        logger.info(f"   Targets: {', '.join(target_countries)}")
        logger.info("="*80)
        
        results = {
            'molecule_info': {},
            'wo_discovery': {},
            'wo_to_br_conversion': {},
            'inpi_search': {},
            'br_patents': [],
            'summary': {},
            'statistics': {},
            'execution_time': 0
        }
        
        try:
            # Phase 1: PubChem
            logger.info("\n📊 PHASE 1: PubChem Intelligence")
            pubchem_data = await self._get_pubchem_data(molecule_name)
            results['molecule_info'] = pubchem_data
            
            # Phase 2: Multi-Layer WO Discovery
            logger.info("\n🔍 PHASE 2: Multi-Layer WO Discovery")
            wo_data = await self._discover_wo_numbers(
                molecule_name,
                pubchem_data.get('dev_codes', []),
                pubchem_data.get('cas')
            )
            results['wo_discovery'] = wo_data
            
            # Phase 3: WO to BR Conversion
            logger.info("\n🇧🇷 PHASE 3: WO to BR Conversion")
            wo_to_br_data = await self._convert_wo_to_br(wo_data['wo_numbers'])
            results['wo_to_br_conversion'] = wo_to_br_data
            
            # Phase 4: INPI Direct Search
            logger.info("\n🏛️  PHASE 4: INPI Direct Search")
            inpi_data = await self._search_inpi_direct(molecule_name, brand_name)
            results['inpi_search'] = inpi_data
            
            # Phase 5: Deduplicate and Build Final List
            logger.info("\n📋 PHASE 5: Deduplication & Final List")
            all_br_patents = self._deduplicate_br_patents(
                wo_to_br_data.get('br_patents', []),
                inpi_data.get('br_patents', [])
            )
            results['br_patents'] = all_br_patents
            
            # Statistics
            results['statistics'] = self.crawler_manager.get_all_metrics()
            results['execution_time'] = time.time() - start_time
            
            # Summary
            results['summary'] = {
                'total_wo_found': len(wo_data['wo_numbers']),
                'total_br_found': len(all_br_patents),
                'wo_with_br': wo_to_br_data.get('successful_conversions', 0),
                'inpi_found': len(inpi_data.get('br_patents', [])),
                'by_source': self._count_by_source(all_br_patents)
            }
            
            # Print statistics
            self.crawler_manager.print_statistics()
            
            logger.info("="*80)
            logger.info(f"✅ SEARCH COMPLETE")
            logger.info(f"   WO Numbers: {results['summary']['total_wo_found']}")
            logger.info(f"   BR Patents: {results['summary']['total_br_found']}")
            logger.info(f"   Time: {results['execution_time']:.2f}s")
            logger.info("="*80)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}", exc_info=True)
            results['error'] = str(e)
            results['execution_time'] = time.time() - start_time
            return results
        
        finally:
            # Cleanup
            await self.crawler_manager.cleanup_all()
    
    async def _get_pubchem_data(self, molecule_name: str) -> Dict:
        """Phase 1: Get molecule intelligence from PubChem"""
        try:
            data = await asyncio.to_thread(get_molecule_data, molecule_name)
            
            logger.info(f"   ✅ PubChem Data:")
            logger.info(f"      CID: {data.get('cid', 'N/A')}")
            logger.info(f"      CAS: {data.get('cas', 'N/A')}")
            logger.info(f"      Dev Codes: {len(data.get('dev_codes', []))}")
            logger.info(f"      Synonyms: {len(data.get('synonyms', []))}")
            
            return data
            
        except Exception as e:
            logger.warning(f"   ⚠️  PubChem failed: {e}")
            return {
                'cid': None,
                'cas': None,
                'dev_codes': [],
                'synonyms': []
            }
    
    async def _discover_wo_numbers(
        self,
        molecule_name: str,
        dev_codes: List[str],
        cas: Optional[str]
    ) -> Dict:
        """Phase 2: Discover WO numbers using multi-layer search"""
        
        # Build search queries
        queries = self._build_wo_queries(molecule_name, dev_codes, cas)
        
        logger.info(f"   Built {len(queries)} search queries")
        
        # Multi-query search with auto-fallback
        wo_numbers, layer_usage = await self.crawler_manager.search_wo_numbers_multi_query(
            queries,
            target=TargetSite.GOOGLE_PATENTS,
            max_results_per_query=10
        )
        
        return {
            'wo_numbers': wo_numbers,
            'queries_used': len(queries),
            'layer_usage': layer_usage,
            'total_found': len(wo_numbers)
        }
    
    def _build_wo_queries(
        self,
        molecule_name: str,
        dev_codes: List[str],
        cas: Optional[str]
    ) -> List[str]:
        """Build comprehensive WO search queries"""
        queries = []
        
        # Base molecule queries with year ranges
        years = ['2016', '2018', '2019', '2020', '2021', '2022', '2023']
        for year in years:
            queries.append(f"{molecule_name} patent WO{year}")
        
        # Company-specific queries (common pharma companies)
        companies = ['Orion', 'Bayer', 'Pfizer', 'Roche', 'Novartis', 'Merck']
        for company in companies[:3]:  # Limit to 3
            queries.append(f"{molecule_name} {company} patent")
        
        # Dev code queries
        for dev_code in dev_codes[:5]:  # Limit to 5
            queries.append(f"{dev_code} patent WO")
        
        # CAS number query
        if cas:
            queries.append(f"{cas} patent WO")
        
        return queries
    
    async def _convert_wo_to_br(self, wo_numbers: List[str]) -> Dict:
        """Phase 3: Convert WO numbers to BR patents"""
        
        if not wo_numbers:
            logger.warning("   No WO numbers to convert")
            return {
                'br_patents': [],
                'successful_conversions': 0,
                'failed_conversions': 0
            }
        
        logger.info(f"   Converting {len(wo_numbers)} WO numbers...")
        
        all_br_patents = []
        successful = 0
        failed = 0
        
        for i, wo_number in enumerate(wo_numbers, 1):
            logger.info(f"   [{i}/{len(wo_numbers)}] Processing {wo_number}...")
            
            br_patents, layer_used = await self.crawler_manager.get_br_patents_from_wo(
                wo_number,
                target=TargetSite.GOOGLE_PATENTS
            )
            
            if br_patents:
                successful += 1
                for br_patent in br_patents:
                    all_br_patents.append({
                        'number': br_patent,
                        'source_wo': wo_number,
                        'source': 'wo_family',
                        'layer': layer_used
                    })
                logger.info(f"      ✅ Found {len(br_patents)} BR patents via {layer_used}")
            else:
                failed += 1
                logger.info(f"      ⚠️  No BR patents found")
            
            # Small delay between WO conversions
            await asyncio.sleep(0.3)
        
        logger.info(f"   Conversion complete: {successful} successful, {failed} failed")
        
        return {
            'br_patents': all_br_patents,
            'successful_conversions': successful,
            'failed_conversions': failed
        }
    
    async def _search_inpi_direct(
        self,
        molecule_name: str,
        brand_name: Optional[str]
    ) -> Dict:
        """Phase 4: Search INPI directly via Railway API"""
        
        br_patents = []
        
        # Search by molecule name
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=40.0) as client:
                # Molecule search
                logger.info(f"   Searching INPI for molecule: {molecule_name}")
                url = f"{self.inpi_api_url}?medicine={molecule_name}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        for patent in data['data']:
                            if patent.get('title', '').startswith('BR'):
                                br_patents.append({
                                    'number': patent['title'].replace(' ', '-'),
                                    'source': 'inpi_molecule',
                                    'layer': 'inpi_api'
                                })
                
                logger.info(f"      Found {len(br_patents)} patents")
                
                # Brand search if provided
                if brand_name:
                    await asyncio.sleep(1)
                    logger.info(f"   Searching INPI for brand: {brand_name}")
                    url = f"{self.inpi_api_url}?medicine={brand_name}"
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        initial_count = len(br_patents)
                        
                        if 'data' in data:
                            for patent in data['data']:
                                if patent.get('title', '').startswith('BR'):
                                    patent_num = patent['title'].replace(' ', '-')
                                    # Avoid duplicates
                                    if not any(p['number'] == patent_num for p in br_patents):
                                        br_patents.append({
                                            'number': patent_num,
                                            'source': 'inpi_brand',
                                            'layer': 'inpi_api'
                                        })
                        
                        logger.info(f"      Found {len(br_patents) - initial_count} additional patents")
        
        except Exception as e:
            logger.error(f"   ❌ INPI search failed: {e}")
        
        return {
            'br_patents': br_patents,
            'total_found': len(br_patents)
        }
    
    def _deduplicate_br_patents(
        self,
        wo_br_patents: List[Dict],
        inpi_br_patents: List[Dict]
    ) -> List[Dict]:
        """Deduplicate BR patents from all sources"""
        
        seen = set()
        unique_patents = []
        
        all_patents = wo_br_patents + inpi_br_patents
        
        for patent in all_patents:
            # Normalize patent number
            patent_num = patent['number'].upper().replace(' ', '').replace('-', '')
            
            if patent_num not in seen:
                seen.add(patent_num)
                unique_patents.append(patent)
        
        logger.info(f"   Total patents: {len(all_patents)}")
        logger.info(f"   Unique patents: {len(unique_patents)}")
        logger.info(f"   Duplicates removed: {len(all_patents) - len(unique_patents)}")
        
        return unique_patents
    
    def _count_by_source(self, br_patents: List[Dict]) -> Dict:
        """Count patents by source"""
        counts = {}
        
        for patent in br_patents:
            source = patent.get('source', 'unknown')
            counts[source] = counts.get(source, 0) + 1
        
        return counts


# Convenience function for backwards compatibility
async def execute_v6_search(
    molecule_name: str,
    brand_name: Optional[str] = None,
    target_countries: List[str] = None
) -> Dict:
    """Execute V6 layered search"""
    orchestrator = V6LayeredOrchestrator()
    return await orchestrator.search(molecule_name, brand_name, target_countries)
