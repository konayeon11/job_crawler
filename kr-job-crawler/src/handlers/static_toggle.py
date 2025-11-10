"""
Static Toggle Handler - 정적 토글 버튼 패턴
"""
from typing import List, Optional
from src.handlers.base import BaseHandler
from src.schema import JobPostingCreate, PatternType, SiteProfile


class StaticToggleHandler(BaseHandler):
    """정적 토글 버튼 패턴 핸들러
    
    예: 카테고리 버튼 클릭 시 DOM이 즉시 변경되는 패턴
    """
    
    def __init__(self, page, profile: SiteProfile):
        super().__init__(page, profile)
        self.pattern_type = PatternType.STATIC_TOGGLE
    
    def crawl(
        self, 
        target_category: str = "IT",
        limit: Optional[int] = None
    ) -> List[JobPostingCreate]:
        """크롤링 실행"""
        
        # 1. IT 필터 적용
        if not self.apply_it_filter(target_category):
            print(f"⚠️  IT 필터 적용 실패, 전체 수집 후 사후 분류 예정")
        
        # 2. 공고 리스트 추출
        self.infinite_scroll(max_scrolls=5)
        jobs_raw = self.extract_job_list()
        
        # 3. JobPostingCreate 변환
        results = []
        for idx, job in enumerate(jobs_raw):
            if limit and idx >= limit:
                break
            
            posting = JobPostingCreate(
                domain=self.domain,
                source_url=job.get("url", self.page.url),
                canonical_job_id=f"{self.domain}_{idx}",
                job_title_raw=job.get("title"),
                company_name_raw=job.get("company"),
                location_raw=job.get("location"),
                pattern_detected=self.pattern_type,
                site_filter_selector="[implement-in-facet-mapper]"
            )
            results.append(posting)
        
        return results
    
    def apply_it_filter(self, category: str) -> bool:
        """IT 직군 필터 적용"""
        # 버튼 후보 탐색
        button_candidates = [
            f"button:has-text('{category}')",
            f"[role='tab']:has-text('{category}')",
            f".category:has-text('{category}')",
            f".filter:has-text('{category}')"
        ]
        
        for selector in button_candidates:
            try:
                button = self.page.query_selector(selector)
                if button:
                    button.click()
                    self.page.wait_for_timeout(1000)  # DOM 업데이트 대기
                    return True
            except Exception:
                continue
        
        return False
