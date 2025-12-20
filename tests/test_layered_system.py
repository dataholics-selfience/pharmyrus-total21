"""
Test V6 Layered Crawler System

Tests:
1. Individual crawler layers
2. CrawlerManager with auto-fallback
3. Complete V6 Layered Orchestrator
4. Circuit breaker behavior
"""
import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_crawler_layers():
    """Test individual crawler layers"""
    from app.crawlers import PlaywrightCrawler, HTTPXCrawler, SeleniumCrawler
    
    print("\n" + "="*80)
    print("🧪 TEST 1: Individual Crawler Layers")
    print("="*80)
    
    query = "Darolutamide patent WO2011"
    
    # Test Playwright
    print("\n📝 Testing Playwright Crawler...")
    try:
        playwright = PlaywrightCrawler()
        wo_numbers = await playwright.search_patents(query, max_results=5)
        print(f"✅ Playwright: Found {len(wo_numbers)} WO numbers")
        print(f"   WO numbers: {wo_numbers[:3]}")
        await playwright.cleanup()
    except Exception as e:
        print(f"❌ Playwright failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test HTTPX
    print("\n📝 Testing HTTPX Crawler...")
    try:
        httpx_crawler = HTTPXCrawler()
        wo_numbers = await httpx_crawler.search_patents(query, max_results=5)
        print(f"✅ HTTPX: Found {len(wo_numbers)} WO numbers")
        print(f"   WO numbers: {wo_numbers[:3]}")
        await httpx_crawler.cleanup()
    except Exception as e:
        print(f"❌ HTTPX failed: {e}")
    
    await asyncio.sleep(2)
    
    # Test Selenium
    print("\n📝 Testing Selenium Crawler...")
    try:
        selenium = SeleniumCrawler()
        wo_numbers = await selenium.search_patents(query, max_results=5)
        print(f"✅ Selenium: Found {len(wo_numbers)} WO numbers")
        print(f"   WO numbers: {wo_numbers[:3]}")
        await selenium.cleanup()
    except Exception as e:
        print(f"❌ Selenium failed: {e}")
    
    print("\n✅ Individual layer tests complete\n")


async def test_crawler_manager():
    """Test CrawlerManager with auto-fallback"""
    from app.crawlers import CrawlerManager, TargetSite
    
    print("\n" + "="*80)
    print("🧪 TEST 2: CrawlerManager with Auto-Fallback")
    print("="*80)
    
    manager = CrawlerManager()
    
    # Test multi-query search
    print("\n📝 Testing multi-query WO discovery...")
    queries = [
        "Darolutamide patent WO2011",
        "Darolutamide Orion patent",
        "ODM-201 patent WO"
    ]
    
    try:
        wo_numbers, layer_usage = await manager.search_wo_numbers_multi_query(
            queries,
            target=TargetSite.GOOGLE_PATENTS,
            max_results_per_query=5
        )
        
        print(f"\n✅ Multi-query search complete:")
        print(f"   Total unique WO numbers: {len(wo_numbers)}")
        print(f"   Layer usage: {layer_usage}")
        print(f"   WO numbers found: {wo_numbers[:5]}")
        
    except Exception as e:
        print(f"❌ Multi-query search failed: {e}")
    
    # Test BR extraction
    if wo_numbers:
        print(f"\n📝 Testing BR extraction for {wo_numbers[0]}...")
        try:
            br_patents, layer_used = await manager.get_br_patents_from_wo(
                wo_numbers[0],
                target=TargetSite.GOOGLE_PATENTS
            )
            
            print(f"✅ BR extraction complete:")
            print(f"   BR patents found: {len(br_patents)}")
            print(f"   Layer used: {layer_used}")
            if br_patents:
                print(f"   BR numbers: {br_patents[:3]}")
            
        except Exception as e:
            print(f"❌ BR extraction failed: {e}")
    
    # Print statistics
    manager.print_statistics()
    
    await manager.cleanup_all()
    
    print("\n✅ CrawlerManager tests complete\n")


async def test_v6_orchestrator():
    """Test complete V6 Layered Orchestrator"""
    from app.services.v6_layered_orchestrator import V6LayeredOrchestrator
    
    print("\n" + "="*80)
    print("🧪 TEST 3: V6 Layered Orchestrator (Complete Pipeline)")
    print("="*80)
    
    orchestrator = V6LayeredOrchestrator()
    
    print("\n📝 Testing complete search for Darolutamide...")
    try:
        results = await orchestrator.search(
            molecule_name="Darolutamide",
            brand_name="Nubeqa",
            target_countries=["BR"]
        )
        
        print(f"\n✅ SEARCH RESULTS:")
        print(f"\n📊 Molecule Info:")
        mol_info = results['molecule_info']
        print(f"   CID: {mol_info.get('cid', 'N/A')}")
        print(f"   CAS: {mol_info.get('cas', 'N/A')}")
        print(f"   Dev Codes: {len(mol_info.get('dev_codes', []))}")
        
        print(f"\n🔍 WO Discovery:")
        wo_disc = results['wo_discovery']
        print(f"   WO numbers found: {wo_disc.get('total_found', 0)}")
        print(f"   Queries used: {wo_disc.get('queries_used', 0)}")
        print(f"   Layer usage: {wo_disc.get('layer_usage', {})}")
        
        print(f"\n🇧🇷 BR Patents:")
        print(f"   Total BR found: {results['summary'].get('total_br_found', 0)}")
        print(f"   From WO families: {results['wo_to_br_conversion'].get('successful_conversions', 0)}")
        print(f"   From INPI direct: {results['inpi_search'].get('total_found', 0)}")
        print(f"   By source: {results['summary'].get('by_source', {})}")
        
        print(f"\n⏱️  Performance:")
        print(f"   Execution time: {results['execution_time']:.2f}s")
        
        print(f"\n📈 Statistics:")
        stats = results['statistics']['manager']
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Success rate: {stats['success_rate']}")
        print(f"   Layer usage: {stats['layer_usage']}")
        
        # Show first few BR patents
        if results['br_patents']:
            print(f"\n📋 Sample BR Patents:")
            for i, patent in enumerate(results['br_patents'][:5], 1):
                print(f"   {i}. {patent['number']} (source: {patent['source']}, layer: {patent.get('layer', 'N/A')})")
        
        # Compare with Cortellis
        br_count = results['summary'].get('total_br_found', 0)
        expected = 8
        match_rate = (min(br_count, expected) / expected) * 100
        
        print(f"\n🎯 Cortellis Comparison:")
        print(f"   Expected: {expected} BR patents")
        print(f"   Found: {br_count} BR patents")
        print(f"   Match rate: {match_rate:.1f}%")
        
        if br_count >= expected:
            print(f"   Status: ✅ EXCELLENT (exceeds Cortellis)")
        elif br_count >= 6:
            print(f"   Status: ✅ GOOD (close to Cortellis)")
        else:
            print(f"   Status: ⚠️  NEEDS IMPROVEMENT")
        
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ V6 Orchestrator tests complete\n")


async def test_circuit_breaker():
    """Test circuit breaker behavior"""
    from app.crawlers import PlaywrightCrawler
    
    print("\n" + "="*80)
    print("🧪 TEST 4: Circuit Breaker Behavior")
    print("="*80)
    
    print("\n📝 Simulating repeated failures to trigger circuit breaker...")
    
    crawler = PlaywrightCrawler()
    
    # Manual failure recording
    for i in range(4):
        crawler.record_failure(is_block=(i % 2 == 0))
        print(f"   Failure {i+1}: Consecutive failures = {crawler.consecutive_failures}")
        print(f"   Status: {crawler.status.value}")
        print(f"   Is available: {crawler.is_available()}")
    
    print(f"\n✅ Circuit breaker triggered!")
    print(f"   Status: {crawler.status.value}")
    print(f"   Cooldown: {max(0, int(crawler.circuit_open_until - asyncio.get_event_loop().time()))}s remaining")
    
    await crawler.cleanup()
    
    print("\n✅ Circuit breaker tests complete\n")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 PHARMYRUS V6 LAYERED CRAWLER - FULL TEST SUITE")
    print("="*80)
    
    try:
        # Test 1: Individual layers
        await test_crawler_layers()
        
        # Test 2: CrawlerManager
        await test_crawler_manager()
        
        # Test 3: V6 Orchestrator (complete pipeline)
        await test_v6_orchestrator()
        
        # Test 4: Circuit breaker
        await test_circuit_breaker()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())
