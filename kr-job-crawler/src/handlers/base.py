"""
Base handler - 모든 패턴 핸들러의 추상 클래스
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from playwright.sync_api import Page

from src.schema import JobPostingCreate, PatternType, SiteProfile


class BaseHandler(ABC):
    """크롤링 핸들러 베이스 클래스"""
    
    def __init__(self, page: Page, profile: SiteProfile):
        self.page = page
        self.profile = profile
        self.domain = profile.domain
        self.pattern_type: PatternType = PatternType.UNKNOWN
    
    @abstractmethod
    def crawl(
        self, 
        target_category: str = "IT",
        limit: Optional[int] = None
    ) -> List[JobPostingCreate]:
        """크롤링 실행 (구현 필수)
        
        Args:
            target_category: 대상 직군 (IT, Engineering, Tech 등)
            limit: 수집 제한 개수
            
        Returns:
            JobPostingCreate 리스트
        """
        pass
    
    @abstractmethod
    def apply_it_filter(self, category: str) -> bool:
        """IT 직군 필터 적용 (구현 필수)
        
        Args:
            category: 필터링할 카테고리명
            
        Returns:
            성공 여부
        """
        pass
    
    def extract_job_list(self) -> List[Dict[str, Any]]:
        """현재 페이지에서 공고 리스트 추출 (공통 로직)"""
        # 기본 셀렉터 시도
        selectors = [
            "article.job-posting",
            "div.job-item",
            "li.job-card",
            "[data-job-id]",
            ".posting-item"
        ]
        
        jobs = []
        for selector in selectors:
            elements = self.page.query_selector_all(selector)
            if elements:
                for elem in elements:
                    try:
                        job_data = {
                            "title": self._safe_extract(elem, "h2, h3, .title"),
                            "company": self._safe_extract(elem, ".company-name"),
                            "location": self._safe_extract(elem, ".location"),
                            "url": self._safe_extract_attr(elem, "a", "href")
                        }
                        jobs.append(job_data)
                    except Exception:
                        continue
                
                if jobs:
                    break
        
        return jobs
    
    def _safe_extract(self, element, selector: str) -> Optional[str]:
        """안전한 텍스트 추출"""
        try:
            elem = element.query_selector(selector)
            return elem.inner_text().strip() if elem else None
        except Exception:
            return None
    
    def _safe_extract_attr(self, element, selector: str, attr: str) -> Optional[str]:
        """안전한 속성 추출"""
        try:
            elem = element.query_selector(selector)
            return elem.get_attribute(attr) if elem else None
        except Exception:
            return None
    
    def infinite_scroll(self, max_scrolls: int = 10) -> int:
        """무한 스크롤 처리"""
        from src.utils.playwright_launcher import PlaywrightLauncher
        
        PlaywrightLauncher.scroll_to_bottom(
            self.page, 
            max_scrolls=max_scrolls,
            delay=1.0
        )
        
        return max_scrolls
