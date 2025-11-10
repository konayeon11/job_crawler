"""
Pattern detector - 사이트 크롤링 패턴 자동 감지
"""
from playwright.sync_api import Page
from typing import Optional, Dict, Any
from src.schema import PatternType


class PatternDetector:
    """사이트 패턴 자동 감지 엔진"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def detect(self) -> PatternType:
        """패턴 감지 실행
        
        감지 순서:
        1. API Direct (네트워크에서 API 호출 확인)
        2. Hash Routing (URL에 # 포함 및 SPA 감지)
        3. Function (onclick, 모달 등)
        4. A Link (일반 링크)
        5. Static Toggle (버튼/필터)
        """
        
        # 1. API Direct 체크 (네트워크 캡처 필요)
        # Note: PlaywrightLauncher에서 캡처된 데이터 사용
        
        # 2. Hash Routing 체크
        if self._is_hash_routing():
            return PatternType.HASH_ROUTING
        
        # 3. Function 체크 (onclick, 모달)
        if self._has_function_pattern():
            return PatternType.FUNCTION
        
        # 4. A Link 체크
        if self._has_a_links():
            return PatternType.A_LINK
        
        # 5. Static Toggle (기본)
        if self._has_toggle_buttons():
            return PatternType.STATIC_TOGGLE
        
        return PatternType.UNKNOWN
    
    def _is_hash_routing(self) -> bool:
        """해시 라우팅 패턴 감지"""
        current_url = self.page.url
        
        # URL에 # 포함
        if "#" in current_url:
            # React/Vue 등 SPA 프레임워크 감지
            has_spa = self.page.evaluate("""
                () => {
                    return !!(
                        window.React || 
                        window.Vue || 
                        window.Angular ||
                        document.querySelector('[data-reactroot]') ||
                        document.querySelector('[data-v-]')
                    );
                }
            """)
            return has_spa
        
        return False
    
    def _has_function_pattern(self) -> bool:
        """함수형 패턴 감지 (onclick, 모달)"""
        # onclick 속성 가진 요소 확인
        onclick_elements = self.page.query_selector_all("[onclick]")
        
        # 모달/다이얼로그 감지
        modal_elements = self.page.query_selector_all(
            "div[role='dialog'], .modal, .popup"
        )
        
        return len(onclick_elements) > 0 or len(modal_elements) > 0
    
    def _has_a_links(self) -> bool:
        """A 태그 링크 패턴 감지"""
        # 채용공고 링크로 보이는 a 태그 확인
        job_links = self.page.query_selector_all(
            "a[href*='job'], a[href*='career'], a[href*='recruit'], a[href*='position']"
        )
        return len(job_links) > 3  # 최소 3개 이상
    
    def _has_toggle_buttons(self) -> bool:
        """토글 버튼 패턴 감지"""
        # 필터/카테고리 버튼 감지
        filter_buttons = self.page.query_selector_all(
            "button, .filter, .category, .tab, [role='tab']"
        )
        return len(filter_buttons) > 0
    
    def get_pattern_metadata(self, pattern: PatternType) -> Dict[str, Any]:
        """패턴별 메타데이터 수집"""
        metadata = {
            "pattern": pattern.value,
            "url": self.page.url,
            "title": self.page.title()
        }
        
        if pattern == PatternType.HASH_ROUTING:
            metadata["hash"] = self.page.url.split("#")[-1] if "#" in self.page.url else None
        
        elif pattern == PatternType.FUNCTION:
            metadata["onclick_count"] = len(self.page.query_selector_all("[onclick]"))
            metadata["modal_count"] = len(self.page.query_selector_all("div[role='dialog'], .modal"))
        
        elif pattern == PatternType.A_LINK:
            job_links = self.page.query_selector_all("a[href*='job'], a[href*='career']")
            metadata["job_link_count"] = len(job_links)
        
        return metadata
