"""
Base Crawler - Interface comum para todos os crawlers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class CrawlerLayer(Enum):
    """Crawler layers in order of preference"""
    PLAYWRIGHT = 1  # Highest stealth, slowest
    HTTPX = 2       # Fast, medium stealth
    SELENIUM = 3    # Fallback, high compatibility


class CrawlerStatus(Enum):
    """Crawler status"""
    READY = "ready"
    RUNNING = "running"
    CIRCUIT_OPEN = "circuit_open"
    FAILED = "failed"


class BaseCrawler(ABC):
    """
    Abstract base class for all crawlers
    
    Features:
    - Circuit breaker pattern
    - Retry logic with exponential backoff
    - Performance metrics
    - Standardized interface
    """
    
    def __init__(self, name: str, layer: CrawlerLayer):
        self.name = name
        self.layer = layer
        self.status = CrawlerStatus.READY
        
        # Circuit breaker
        self.consecutive_failures = 0
        self.max_failures = 3
        self.circuit_open_until = 0
        self.circuit_cooldown = 300  # 5 minutes
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'blocked_requests': 0,
            'total_time': 0.0,
            'avg_response_time': 0.0
        }
        
        # Performance
        self.request_times = []
        self.max_request_time_samples = 100
    
    def is_available(self) -> bool:
        """Check if crawler is available (circuit not open)"""
        if time.time() < self.circuit_open_until:
            return False
        
        if self.status == CrawlerStatus.CIRCUIT_OPEN:
            # Try to recover
            logger.info(f"🔄 {self.name}: Circuit breaker cooling down, attempting recovery...")
            self.status = CrawlerStatus.READY
            self.consecutive_failures = 0
        
        return self.status != CrawlerStatus.FAILED
    
    def record_success(self, response_time: float):
        """Record successful request"""
        self.metrics['total_requests'] += 1
        self.metrics['successful_requests'] += 1
        self.metrics['total_time'] += response_time
        
        self.request_times.append(response_time)
        if len(self.request_times) > self.max_request_time_samples:
            self.request_times.pop(0)
        
        self.metrics['avg_response_time'] = sum(self.request_times) / len(self.request_times)
        
        # Reset circuit breaker on success
        self.consecutive_failures = 0
        self.status = CrawlerStatus.READY
    
    def record_failure(self, is_block: bool = False):
        """Record failed request"""
        self.metrics['total_requests'] += 1
        self.metrics['failed_requests'] += 1
        
        if is_block:
            self.metrics['blocked_requests'] += 1
        
        self.consecutive_failures += 1
        
        # Check circuit breaker
        if self.consecutive_failures >= self.max_failures:
            self.open_circuit()
    
    def open_circuit(self):
        """Open circuit breaker"""
        self.circuit_open_until = time.time() + self.circuit_cooldown
        self.status = CrawlerStatus.CIRCUIT_OPEN
        
        logger.error(
            f"⛔ {self.name}: Circuit breaker OPENED "
            f"(failures: {self.consecutive_failures}, "
            f"cooldown: {self.circuit_cooldown}s)"
        )
    
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.metrics['total_requests'] == 0:
            return 0.0
        return (self.metrics['successful_requests'] / self.metrics['total_requests']) * 100
    
    def get_metrics(self) -> Dict:
        """Get performance metrics"""
        return {
            'name': self.name,
            'layer': self.layer.name,
            'status': self.status.value,
            'success_rate': f"{self.get_success_rate():.1f}%",
            **self.metrics,
            'circuit_breaker': {
                'consecutive_failures': self.consecutive_failures,
                'is_open': self.status == CrawlerStatus.CIRCUIT_OPEN,
                'cooldown_remaining': max(0, int(self.circuit_open_until - time.time()))
            }
        }
    
    @abstractmethod
    async def initialize(self):
        """Initialize crawler resources"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup crawler resources"""
        pass
    
    @abstractmethod
    async def search_patents(self, query: str, max_results: int = 20) -> List[str]:
        """
        Search for patents and return WO numbers
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of WO numbers
        """
        pass
    
    @abstractmethod
    async def get_patent_details(self, wo_number: str) -> Optional[Dict]:
        """
        Get details for a specific patent
        
        Args:
            wo_number: WO patent number
            
        Returns:
            Patent details or None if failed
        """
        pass
    
    @abstractmethod
    async def get_br_patents_from_wo(self, wo_number: str) -> List[str]:
        """
        Get BR patent numbers from WO family
        
        Args:
            wo_number: WO patent number
            
        Returns:
            List of BR patent numbers
        """
        pass
