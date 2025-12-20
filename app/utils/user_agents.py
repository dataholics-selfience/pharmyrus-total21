"""
User-Agent Rotation System
Mimics real browsers across multiple devices
"""
import random
from typing import Dict, List


class UserAgentRotator:
    """
    Rotates between realistic User-Agents
    Based on real browser statistics
    """
    
    # Desktop Chrome (Latest versions)
    DESKTOP_CHROME = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    # Desktop Firefox
    DESKTOP_FIREFOX = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    # Desktop Safari
    DESKTOP_SAFARI = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    ]
    
    # Desktop Edge
    DESKTOP_EDGE = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    ]
    
    # Mobile iOS Safari
    MOBILE_IOS = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    ]
    
    # Mobile Android Chrome
    MOBILE_ANDROID = [
        'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',
    ]
    
    ALL_AGENTS = (
        DESKTOP_CHROME + 
        DESKTOP_FIREFOX + 
        DESKTOP_SAFARI + 
        DESKTOP_EDGE + 
        MOBILE_IOS + 
        MOBILE_ANDROID
    )
    
    @classmethod
    def get_random(cls) -> str:
        """Get a random user agent"""
        return random.choice(cls.ALL_AGENTS)
    
    @classmethod
    def get_desktop_chrome(cls) -> str:
        """Get random desktop Chrome UA"""
        return random.choice(cls.DESKTOP_CHROME)
    
    @classmethod
    def get_mobile(cls) -> str:
        """Get random mobile UA"""
        return random.choice(cls.MOBILE_IOS + cls.MOBILE_ANDROID)
    
    @classmethod
    def get_headers(cls, user_agent: str = None) -> Dict[str, str]:
        """
        Get realistic headers for the given user agent
        Includes all critical headers for Google
        """
        if user_agent is None:
            user_agent = cls.get_random()
        
        # Detect if mobile
        is_mobile = 'Mobile' in user_agent or 'iPhone' in user_agent or 'iPad' in user_agent
        
        # Base headers (critical for Google)
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        # Add Chrome-specific headers if Chrome UA
        if 'Chrome' in user_agent and 'Edg' not in user_agent:
            headers['sec-ch-ua'] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
            headers['sec-ch-ua-mobile'] = '?1' if is_mobile else '?0'
            headers['sec-ch-ua-platform'] = '"Android"' if is_mobile else '"Windows"'
        
        return headers
    
    @classmethod
    def get_playwright_context_args(cls, user_agent: str = None) -> Dict:
        """
        Get Playwright browser context arguments
        For stealth mode
        """
        if user_agent is None:
            user_agent = cls.get_desktop_chrome()
        
        is_mobile = 'Mobile' in user_agent or 'iPhone' in user_agent
        
        context_args = {
            'user_agent': user_agent,
            'viewport': {
                'width': 375 if is_mobile else 1920,
                'height': 667 if is_mobile else 1080
            },
            'device_scale_factor': 3 if 'iPhone' in user_agent else 1,
            'is_mobile': is_mobile,
            'has_touch': is_mobile,
            'locale': 'en-US',
            'timezone_id': 'America/Sao_Paulo',
            'permissions': ['geolocation'],
            'geolocation': {'latitude': -23.5505, 'longitude': -46.6333},  # São Paulo
            'color_scheme': 'light',
            'extra_http_headers': cls.get_headers(user_agent)
        }
        
        return context_args
