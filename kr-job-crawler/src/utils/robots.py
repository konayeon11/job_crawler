"""
robots.txt compliance checker
"""
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import httpx
from typing import Optional


class RobotsChecker:
    """robots.txt 준수 체커"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.parser = RobotFileParser()
        self.robots_url = urljoin(base_url, "/robots.txt")
        self._loaded = False
    
    def load(self) -> bool:
        """robots.txt 로드"""
        try:
            response = httpx.get(self.robots_url, timeout=10)
            if response.status_code == 200:
                self.parser.parse(response.text.splitlines())
                self._loaded = True
                return True
        except Exception:
            pass
        
        self._loaded = False
        return False
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """URL 크롤링 가능 여부 확인"""
        if not self._loaded:
            # robots.txt 없으면 허용
            return True
        
        return self.parser.can_fetch(user_agent, url)
    
    def get_crawl_delay(self, user_agent: str = "*") -> Optional[float]:
        """크롤 딜레이 확인"""
        if not self._loaded:
            return None
        
        return self.parser.crawl_delay(user_agent)
