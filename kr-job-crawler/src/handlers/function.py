"""
Function Handler - onclick/모달 패턴
"""
from typing import List, Optional
from src.handlers.base import BaseHandler
from src.schema import JobPostingCreate, PatternType, SiteProfile


class FunctionHandler(BaseHandler):
    """함수형 패턴 핸들러 (onclick, 모달)"""
    
    def __init__(self, page, profile: SiteProfile):
        super().__init__(page, profile)
        self.pattern_type = PatternType.FUNCTION
    
    def crawl(
        self, 
        target_category: str = "IT",
        limit: Optional[int] = None
    ) -> List[JobPostingCreate]:
        """크롤링 실행"""
        
        self.apply_it_filter(target_category)
        
        # onclick 요소 탐지
        clickable_elements = self.page.query_selector_all(
            "[onclick], button.job-item, div.job-card[data-action]"
        )
        
        results = []
        for idx, elem in enumerate(clickable_elements):
            if limit and idx >= limit:
                break
            
            try:
                # 클릭하여 모달/상세 열기
                elem.click()
                self.page.wait_for_timeout(500)
                
                # 모달 내용 추출
                modal = self.page.query_selector("div[role='dialog'], .modal-content")
                if modal:
                    title = self._safe_extract(modal, "h1, h2, .title")
                    company = self._safe_extract(modal, ".company-name")
                    
                    posting = JobPostingCreate(
                        domain=self.domain,
                        source_url=self.page.url,
                        canonical_job_id=f"{self.domain}_modal_{idx}",
                        job_title_raw=title,
                        company_name_raw=company,
                        pattern_detected=self.pattern_type,
                        selectors_used={"modal": "div[role='dialog']"}
                    )
                    results.append(posting)
                    
                    # 모달 닫기
                    close_btn = modal.query_selector("button.close, [aria-label='Close']")
                    if close_btn:
                        close_btn.click()
                        self.page.wait_for_timeout(300)
            
            except Exception as e:
                print(f"⚠️  모달 처리 실패: {e}")
                continue
        
        return results
    
    def apply_it_filter(self, category: str) -> bool:
        """IT 필터 적용"""
        # onclick 필터 버튼 시도
        try:
            filter_btn = self.page.query_selector(
                f"button[onclick]:has-text('{category}'), [data-filter='{category}']"
            )
            if filter_btn:
                filter_btn.click()
                self.page.wait_for_timeout(1000)
                return True
        except Exception:
            pass
        
        return False
