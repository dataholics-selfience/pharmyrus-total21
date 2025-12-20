"""
Human-like delay system
Randomizes timing to avoid bot detection
"""
import random
import time
import asyncio
from typing import Optional


class HumanDelaySimulator:
    """
    Simulates human-like delays
    Uses exponential backoff for retries
    """
    
    # Base delays (in seconds)
    MIN_PAGE_LOAD = 1.5
    MAX_PAGE_LOAD = 4.0
    
    MIN_CLICK_DELAY = 0.3
    MAX_CLICK_DELAY = 1.2
    
    MIN_TYPE_DELAY = 0.05
    MAX_TYPE_DELAY = 0.15
    
    MIN_SCROLL_DELAY = 0.5
    MAX_SCROLL_DELAY = 1.5
    
    @staticmethod
    def random_delay(min_sec: float, max_sec: float) -> float:
        """
        Generate a random delay with slight variance
        Uses normal distribution for more human-like timing
        """
        mid = (min_sec + max_sec) / 2
        std_dev = (max_sec - min_sec) / 6  # 99.7% within range
        
        delay = random.gauss(mid, std_dev)
        
        # Clamp to range
        return max(min_sec, min(max_sec, delay))
    
    @classmethod
    def page_load(cls) -> float:
        """Delay for page loading"""
        return cls.random_delay(cls.MIN_PAGE_LOAD, cls.MAX_PAGE_LOAD)
    
    @classmethod
    def click(cls) -> float:
        """Delay between clicks"""
        return cls.random_delay(cls.MIN_CLICK_DELAY, cls.MAX_CLICK_DELAY)
    
    @classmethod
    def typing(cls) -> float:
        """Delay between keystrokes"""
        return cls.random_delay(cls.MIN_TYPE_DELAY, cls.MAX_TYPE_DELAY)
    
    @classmethod
    def scroll(cls) -> float:
        """Delay for scrolling"""
        return cls.random_delay(cls.MIN_SCROLL_DELAY, cls.MAX_SCROLL_DELAY)
    
    @classmethod
    def between_searches(cls) -> float:
        """Delay between different searches"""
        return cls.random_delay(2.0, 5.0)
    
    @classmethod
    async def async_wait(cls, delay: float):
        """Async wait with human-like delay"""
        await asyncio.sleep(delay)
    
    @classmethod
    def sync_wait(cls, delay: float):
        """Sync wait with human-like delay"""
        time.sleep(delay)
    
    @classmethod
    def exponential_backoff(cls, attempt: int, base_delay: float = 2.0, max_delay: float = 60.0) -> float:
        """
        Exponential backoff for retries
        attempt: 0-based retry attempt number
        """
        delay = min(base_delay * (2 ** attempt), max_delay)
        # Add jitter (±25%)
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        return delay + jitter
    
    @classmethod
    def jittered_delay(cls, base_delay: float, jitter_percent: float = 0.25) -> float:
        """
        Add random jitter to a base delay
        jitter_percent: 0.25 = ±25% variance
        """
        jitter = base_delay * jitter_percent * (random.random() * 2 - 1)
        return base_delay + jitter


class RetryStrategy:
    """
    Retry strategy with exponential backoff
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.attempt = 0
    
    def should_retry(self) -> bool:
        """Check if we should retry"""
        return self.attempt < self.max_retries
    
    def get_delay(self) -> float:
        """Get delay for current attempt"""
        delay = HumanDelaySimulator.exponential_backoff(self.attempt, self.base_delay)
        self.attempt += 1
        return delay
    
    def reset(self):
        """Reset retry counter"""
        self.attempt = 0


class DelayManager:
    """
    Manages delays for different target sites with Gaussian distribution
    """
    
    # Site-specific delays (min, max) in seconds
    SITE_DELAYS = {
        'google_patents': (15.0, 30.0),  # High stealth requirement
        'wipo': (2.0, 4.0),               # Medium
        'inpi': (0.5, 1.0),               # Light
        'pubchem': (1.0, 2.0),            # Light
        'default': (2.0, 5.0),            # Default for unknown sites
    }
    
    @classmethod
    def get_delay(cls, site: str = 'default') -> float:
        """
        Get delay for specific site using Gaussian distribution
        Args:
            site: Site identifier (google_patents, wipo, inpi, etc)
        Returns:
            Delay in seconds
        """
        min_delay, max_delay = cls.SITE_DELAYS.get(site, cls.SITE_DELAYS['default'])
        return HumanDelaySimulator.random_delay(min_delay, max_delay)
    
    @classmethod
    async def async_delay(cls, site: str = 'default'):
        """Async delay for specific site"""
        delay = cls.get_delay(site)
        await asyncio.sleep(delay)
    
    @classmethod
    def sync_delay(cls, site: str = 'default'):
        """Sync delay for specific site"""
        delay = cls.get_delay(site)
        time.sleep(delay)
