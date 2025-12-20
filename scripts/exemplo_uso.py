#!/usr/bin/env python3
"""
Pharmyrus V6 LAYERED - Exemplo de Uso Completo
Demonstra busca real de patentes com o sistema multi-camada
"""
import asyncio
import json
from datetime import datetime
from app.services.v6_layered_orchestrator import V6LayeredOrchestrator


async def exemplo_busca_completa():
    """Exemplo de busca completa com output detalhado"""
    print("\n" + "="*80)
    print("🔬 PHARMYRUS V6 LAYERED - EXEMPLO DE BUSCA COMPLETA")
    print("="*80 + "\n")
    
    # Inicializar orchestrator
    print("📋 Inicializando V6 Layered Orchestrator...")
    orchestrator = V6LayeredOrchestrator()
    
    # Molécula de exemplo: Darolutamide (baseline Cortellis: 8 BR)
    molecule = "Darolutamide"
    brand = "Nubeqa"
    
    print(f"🎯 Molécula: {molecule}")
    print(f"💊 Nome comercial: {brand}")
    print(f"🌍 País alvo: Brasil")
    print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}\n")
    
    try:
        # Executar busca
        print("🚀 Executando pipeline completo...\n")
        results = await orchestrator.search(
            molecule_name=molecule,
            brand_name=brand,
            target_countries=["BR"]
        )
        
        # Exibir resultados
        print("\n" + "="*80)
        print("📊 RESULTADOS DA BUSCA")
        print("="*80 + "\n")
        
        # Fase 1: PubChem
        print("📚 FASE 1: PubChem Intelligence")
        mol_info = results.get('molecule_info', {})
        print(f"   ✅ CID: {mol_info.get('cid', 'N/A')}")
        print(f"   ✅ CAS: {mol_info.get('cas', 'N/A')}")
        print(f"   ✅ Dev codes: {len(mol_info.get('dev_codes', []))} encontrados")
        print(f"   ✅ Synonyms: {len(mol_info.get('synonyms', []))} encontrados")
        
        # Fase 2: WO Discovery
        print(f"\n🔍 FASE 2: WO Number Discovery")
        wo_disc = results.get('wo_discovery', {})
        wo_nums = wo_disc.get('wo_numbers', [])
        print(f"   ✅ WO numbers encontrados: {len(wo_nums)}")
        if wo_nums:
            print(f"   📄 Primeiros 5: {', '.join(wo_nums[:5])}")
        
        # Fase 3: WO → BR Conversion
        print(f"\n🔄 FASE 3: WO → BR Conversion")
        wo_br = results.get('wo_to_br_conversion', {})
        wo_processed = wo_br.get('wo_processed', 0)
        wo_success = wo_br.get('successful_conversions', 0)
        print(f"   ✅ WO processados: {wo_processed}")
        print(f"   ✅ Conversões bem-sucedidas: {wo_success}")
        print(f"   ✅ Taxa de sucesso: {wo_br.get('success_rate', 0):.1f}%")
        
        # Fase 4: INPI
        print(f"\n🇧🇷 FASE 4: INPI Direct Search")
        inpi = results.get('inpi_search', {})
        print(f"   ✅ BR patents via INPI: {inpi.get('total_found', 0)}")
        
        # Fase 5: Final Results
        print(f"\n🎯 FASE 5: Resultados Finais")
        br_patents = results.get('br_patents', [])
        print(f"   ✅ Total BR patents: {len(br_patents)}")
        
        # Estatísticas
        stats = results.get('statistics', {})
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"   ⏱️  Tempo total: {stats.get('total_time', 0):.2f}s")
        print(f"   🎯 Taxa de sucesso: {stats.get('overall_success_rate', 0):.1f}%")
        
        crawler_stats = stats.get('crawler_stats', {})
        if crawler_stats:
            print(f"\n   📊 Por Layer:")
            for layer, data in crawler_stats.items():
                print(f"      • {layer}: {data.get('success_rate', 0):.1f}% "
                      f"({data.get('successful_requests', 0)}/{data.get('total_requests', 0)})")
        
        # Comparação Cortellis
        print(f"\n🏆 COMPARAÇÃO COM CORTELLIS:")
        summary = results.get('summary', {})
        expected = 8  # Baseline Darolutamide
        found = len(br_patents)
        match_rate = (min(found, expected) / expected) * 100
        
        print(f"   • Esperado (Cortellis): {expected} BR")
        print(f"   • Encontrado: {found} BR")
        print(f"   • Match rate: {match_rate:.0f}%")
        
        if found >= 8:
            print(f"   ✅ EXCELENTE - 100% match!")
        elif found >= 6:
            print(f"   ✅ BOM - Match satisfatório")
        elif found >= 4:
            print(f"   ⚠️  ACEITÁVEL - Precisa melhorar")
        else:
            print(f"   ❌ BAIXO - Revisar estratégia")
        
        # Mostrar alguns BR patents
        if br_patents:
            print(f"\n📄 PRIMEIROS 3 BR PATENTS:")
            for i, patent in enumerate(br_patents[:3], 1):
                print(f"\n   {i}. {patent.get('number', 'N/A')}")
                print(f"      Título: {patent.get('title', 'N/A')[:60]}...")
                print(f"      Fonte: {patent.get('source', 'N/A')}")
                print(f"      Link: {patent.get('link', 'N/A')}")
        
        # Salvar resultados
        print(f"\n💾 Salvando resultados...")
        output_file = f"results_{molecule}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Salvo em: {output_file}")
        
        print(f"\n⏰ Conclusão: {datetime.now().strftime('%H:%M:%S')}")
        print("\n" + "="*80)
        print("✅ BUSCA COMPLETA FINALIZADA COM SUCESSO!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n🧹 Limpando recursos...")
        await orchestrator.cleanup()
        print("   ✅ Cleanup concluído")


async def exemplo_uso_direto_manager():
    """Exemplo de uso direto do CrawlerManager"""
    print("\n" + "="*80)
    print("🔧 EXEMPLO: USO DIRETO DO CRAWLER MANAGER")
    print("="*80 + "\n")
    
    from app.crawlers import CrawlerManager, TargetSite
    
    manager = CrawlerManager()
    
    try:
        # Buscar WO numbers
        print("🔍 Buscando WO numbers...")
        wo_numbers, layer_used = await manager.search_wo_numbers(
            query="Darolutamide patent WO",
            target=TargetSite.GOOGLE_PATENTS
        )
        
        print(f"   ✅ Layer usado: {layer_used}")
        print(f"   ✅ WO encontrados: {len(wo_numbers)}")
        if wo_numbers:
            print(f"   📄 Primeiros 3: {', '.join(wo_numbers[:3])}")
        
        # Se encontrou WO, buscar BR patents
        if wo_numbers:
            print(f"\n🇧🇷 Buscando BR patents do primeiro WO...")
            br_patents, layer_used = await manager.get_br_patents_from_wo(
                wo_number=wo_numbers[0],
                target=TargetSite.GOOGLE_PATENTS
            )
            
            print(f"   ✅ Layer usado: {layer_used}")
            print(f"   ✅ BR patents: {len(br_patents)}")
        
        # Mostrar métricas
        print(f"\n📊 MÉTRICAS DO CRAWLER MANAGER:")
        metrics = manager.get_all_metrics()
        print(f"   • Total requests: {metrics['total_requests']}")
        print(f"   • Total successes: {metrics['total_successes']}")
        print(f"   • Success rate: {metrics['overall_success_rate']:.1f}%")
        
        print(f"\n   Layer usage:")
        for layer, count in metrics['layer_usage'].items():
            print(f"      • {layer}: {count} requests")
        
    finally:
        await manager.cleanup_all()
        print("\n   ✅ Cleanup concluído")


async def exemplo_teste_individual_layer():
    """Exemplo de teste de layer individual"""
    print("\n" + "="*80)
    print("🎯 EXEMPLO: TESTE DE LAYER INDIVIDUAL (HTTPX)")
    print("="*80 + "\n")
    
    from app.crawlers import HTTPXCrawler
    
    crawler = HTTPXCrawler()
    
    try:
        print("🔍 Testando HTTPX crawler...")
        
        # Teste simples
        html = await crawler.fetch_page("https://httpbin.org/get")
        
        if html:
            print(f"   ✅ Fetch bem-sucedido")
            print(f"   ✅ Content length: {len(html)} chars")
        
        # Mostrar métricas
        metrics = crawler.get_metrics()
        print(f"\n📊 MÉTRICAS:")
        print(f"   • Total requests: {metrics['total_requests']}")
        print(f"   • Success rate: {metrics['success_rate']:.1f}%")
        print(f"   • Circuit breaker: {metrics['circuit_breaker_status']}")
        
    finally:
        await crawler.cleanup()
        print("\n   ✅ Cleanup concluído")


async def main():
    """Menu principal"""
    print("\n" + "="*80)
    print("🚀 PHARMYRUS V6 LAYERED - EXEMPLOS DE USO")
    print("="*80)
    print("\nEscolha um exemplo:")
    print("1. Busca completa (V6 Orchestrator)")
    print("2. Uso direto do CrawlerManager")
    print("3. Teste de layer individual")
    print("4. Executar todos os exemplos")
    print("0. Sair")
    
    choice = input("\nOpção: ").strip()
    
    if choice == "1":
        await exemplo_busca_completa()
    elif choice == "2":
        await exemplo_uso_direto_manager()
    elif choice == "3":
        await exemplo_teste_individual_layer()
    elif choice == "4":
        await exemplo_busca_completa()
        await exemplo_uso_direto_manager()
        await exemplo_teste_individual_layer()
    elif choice == "0":
        print("\n👋 Até logo!")
    else:
        print("\n❌ Opção inválida")


if __name__ == "__main__":
    # Executar exemplo completo direto se não for interativo
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        asyncio.run(exemplo_busca_completa())
    else:
        asyncio.run(main())
