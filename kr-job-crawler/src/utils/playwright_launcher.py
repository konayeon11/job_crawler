"""
Playwright launcher with network capture capabilities
"""
from playwright.sync_api import sync_playwright, Browser, Page, Route
from typing import Optional, List, Dict, Any, Callable
import time
import random
from dataclasses import dataclass, field

from src.config import settings


@dataclass
class NetworkRequest:
    """캡처된 네트워크 요청"""
    url: str
    method: str
    headers: Dict[str, str]
    post_data: Optional[str] = None
    resource_type: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class NetworkResponse:
    """캡처된 네트워크 응답"""
    url: str
    status: int
    headers: Dict[str, str]
    body: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class PlaywrightLauncher:
    """Playwright 브라우저 런처 및 네트워크 캡처"""
    
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else settings.playwright_headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.requests: List[NetworkRequest] = []
        self.responses: List[NetworkResponse] = []
        
    def __enter__(self):
        self.playwright = sync_playwright().start()
        
        browser_type = getattr(self.playwright, settings.playwright_browser)
        self.browser = browser_type.launch(headless=self.headless)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def new_page(self, capture_network: bool = True) -> Page:
        """새 페이지 생성 (네트워크 캡처 옵션)"""
        if not self.browser:
            raise RuntimeError("Browser not launched. Use context manager.")
        
        page = self.browser.new_page(
            user_agent=settings.user_agent,
            viewport={"width": 1920, "height": 1080}
        )
        
        if capture_network:
            self._setup_network_listeners(page)
        
        return page
    
    def _setup_network_listeners(self, page: Page):
        """네트워크 리스너 설정"""
        
        def on_request(request):
            """요청 캡처"""
            # API 호출만 필터링 (XHR, Fetch)
            if request.resource_type in ["xhr", "fetch"]:
                self.requests.append(NetworkRequest(
                    url=request.url,
                    method=request.method,
                    headers=request.headers,
                    post_data=request.post_data,
                    resource_type=request.resource_type
                ))
        
        def on_response(response):
            """응답 캡처"""
            if response.request.resource_type in ["xhr", "fetch"]:
                try:
                    body = response.text() if response.ok else None
                except:
                    body = None
                
                self.responses.append(NetworkResponse(
                    url=response.url,
                    status=response.status,
                    headers=response.headers,
                    body=body
                ))
        
        page.on("request", on_request)
        page.on("response", on_response)
    
    def clear_captures(self):
        """캡처된 네트워크 데이터 초기화"""
        self.requests.clear()
        self.responses.clear()
    
    def get_api_calls(self, url_pattern: Optional[str] = None) -> List[NetworkRequest]:
        """API 호출 필터링"""
        if url_pattern:
            return [req for req in self.requests if url_pattern in req.url]
        return self.requests
    
    def get_graphql_calls(self) -> List[NetworkRequest]:
        """GraphQL 호출 필터링"""
        return [req for req in self.requests if "graphql" in req.url.lower()]
    
    @staticmethod
    def random_delay(min_sec: float = None, max_sec: float = None):
        """랜덤 지연 (요청 제한 준수)"""
        min_delay = min_sec or settings.request_delay_min
        max_delay = max_sec or settings.request_delay_max
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    @staticmethod
    def scroll_to_bottom(page: Page, max_scrolls: int = 10, delay: float = 1.0):
        """무한 스크롤 표준 루프"""
        previous_height = page.evaluate("document.body.scrollHeight")
        
        for i in range(max_scrolls):
            # 스크롤 다운
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(delay)
            
            # 새 높이 확인
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break
            previous_height = new_height
