#!/usr/bin/env python3
"""
Pharmyrus V6 LAYERED - Quick Validation Script
Verifica se todos os componentes estão presentes e funcionais
"""
import os
import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description} - NOT FOUND")
        return False


def validate_system():
    """Validate complete system"""
    print("\n" + "="*80)
    print("🔍 PHARMYRUS V6 LAYERED - SYSTEM VALIDATION")
    print("="*80 + "\n")
    
    all_ok = True
    
    # Crawlers
    print("📂 CRAWLERS (Multi-Layer System):")
    files = [
        ("app/crawlers/__init__.py", "Crawler __init__"),
        ("app/crawlers/base_crawler.py", "Base Crawler (interface)"),
        ("app/crawlers/playwright_crawler.py", "Layer 1: Playwright"),
        ("app/crawlers/httpx_crawler.py", "Layer 2: HTTPX"),
        ("app/crawlers/selenium_crawler.py", "Layer 3: Selenium"),
        ("app/crawlers/crawler_manager.py", "Crawler Manager"),
    ]
    for filepath, desc in files:
        if not check_file_exists(filepath, f"   {desc}"):
            all_ok = False
    
    # Orchestrator
    print("\n📂 ORCHESTRATOR:")
    if not check_file_exists("app/services/v6_layered_orchestrator.py", "   V6 Layered Orchestrator"):
        all_ok = False
    
    # Tests
    print("\n📂 TESTS:")
    if not check_file_exists("test_layered_system.py", "   Complete Test Suite"):
        all_ok = False
    
    # Documentation
    print("\n📂 DOCUMENTATION:")
    docs = [
        ("README_LAYERED_SYSTEM.md", "Technical Documentation"),
        ("RESUMO_EXECUTIVO.md", "Executive Summary"),
        ("STATUS_FINAL.md", "Final Status Report"),
        ("show_system.py", "Visual Presentation"),
    ]
    for filepath, desc in docs:
        if not check_file_exists(filepath, f"   {desc}"):
            all_ok = False
    
    # Utils
    print("\n📂 UTILITIES:")
    if not check_file_exists("install.sh", "   Installation Script"):
        all_ok = False
    
    # Syntax check
    print("\n🔧 SYNTAX VALIDATION:")
    try:
        import py_compile
        
        crawler_files = [
            "app/crawlers/base_crawler.py",
            "app/crawlers/playwright_crawler.py",
            "app/crawlers/httpx_crawler.py",
            "app/crawlers/selenium_crawler.py",
            "app/crawlers/crawler_manager.py",
        ]
        
        syntax_ok = True
        for file in crawler_files:
            try:
                py_compile.compile(file, doraise=True)
            except Exception as e:
                print(f"   ❌ Syntax error in {file}: {e}")
                syntax_ok = False
                all_ok = False
        
        if syntax_ok:
            print("   ✅ All crawler files: No syntax errors")
        
        # Check orchestrator
        try:
            py_compile.compile("app/services/v6_layered_orchestrator.py", doraise=True)
            print("   ✅ Orchestrator: No syntax errors")
        except Exception as e:
            print(f"   ❌ Syntax error in orchestrator: {e}")
            all_ok = False
            
    except Exception as e:
        print(f"   ⚠️  Could not validate syntax: {e}")
    
    # Summary
    print("\n" + "="*80)
    if all_ok:
        print("✅ SYSTEM VALIDATION: ALL CHECKS PASSED")
        print("="*80)
        print("\n🚀 System is ready for testing!")
        print("\nNext steps:")
        print("   1. Install dependencies: ./install.sh")
        print("   2. Run tests: python test_layered_system.py")
        print("   3. View system: python show_system.py")
        print()
        return 0
    else:
        print("❌ SYSTEM VALIDATION: SOME CHECKS FAILED")
        print("="*80)
        print("\n⚠️  Please review the errors above")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(validate_system())
