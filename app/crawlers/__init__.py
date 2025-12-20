"""
Pharmyrus V6 STEALTH - Multi-Layer Crawler System

Architecture:
┌─────────────────────────────────────────────────────────┐
│                   CrawlerManager                        │
│              (Smart Layer Orchestrator)                 │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Layer 1     │  │  Layer 2     │  │  Layer 3     │
│  Playwright  │  │  HTTPX       │  │  Selenium    │
│              │  │              │  │              │
│ Highest      │  │ Fast         │  │ Robust       │
│ Stealth      │  │ Medium       │  │ Fallback     │
│              │  │ Stealth      │  │              │
│ 500ms-2s     │  │ 100-300ms    │  │ 1-3s         │
└──────────────┘  └──────────────┘  └──────────────┘

Layer Selection Strategy:
- Google Patents: Playwright → Selenium → HTTPX (stealth priority)
- WIPO: HTTPX → Playwright → Selenium (speed priority)  
- INPI: HTTPX → Playwright → Selenium (speed priority)

Features:
✅ Automatic fallback on failure
✅ Circuit breaker per layer (3 failures → 5min cooldown)
✅ Performance metrics and success rates
✅ Smart layer selection based on target
✅ Multi-query deduplication
✅ Comprehensive logging
"""

from app.crawlers.base_crawler import (
    BaseCrawler,
    CrawlerLayer,
    CrawlerStatus
)

from app.crawlers.playwright_crawler import PlaywrightCrawler
from app.crawlers.httpx_crawler import HTTPXCrawler
from app.crawlers.selenium_crawler import SeleniumCrawler

from app.crawlers.crawler_manager import (
    CrawlerManager,
    TargetSite
)

__all__ = [
    # Base
    'BaseCrawler',
    'CrawlerLayer',
    'CrawlerStatus',
    
    # Crawlers
    'PlaywrightCrawler',
    'HTTPXCrawler',
    'SeleniumCrawler',
    
    # Manager
    'CrawlerManager',
    'TargetSite',
]

__version__ = '6.0.0-STEALTH'
__author__ = 'Pharmyrus Team'
__description__ = 'Multi-layer patent crawler with advanced anti-detection'
