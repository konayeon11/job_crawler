"""
Hash Routing Handler - SPA 해시 라우팅 패턴
"""
from typing import List, Optional
from src.handlers.base import BaseHandler
from src.schema import JobPostingCreate, PatternType, SiteProfile


class HashRoutingHandler(BaseHandler):
    """해시 라우팅 패턴 핸들러 (SPA)"""
    
    def __init__(self, page, profile: SiteProfile):
        super().__init__(page, profile)
        self.pattern_type = PatternType.HASH_ROUTING
    
    def crawl(
        self, 
        target_category: str = "IT",
        limit: Optional[int] = None
    ) -> List[JobPostingCreate]:
        """크롤링 실행"""
        
        # IT 해시 라우트 적용
        it_route = self.apply_it_filter(target_category)
        
        # 해시 변경 후 대기
        self.page.wait_for_timeout(2000)
        
        # 공고 추출
        self.infinite_scroll(max_scrolls=5)
        jobs_raw = self.extract_job_list()
        
        results = []
        for idx, job in enumerate(jobs_raw):
            if limit and idx >= limit:
                break
            
            posting = JobPostingCreate(
                domain=self.domain,
                source_url=job.get("url", self.page.url),
                canonical_job_id=f"{self.domain}_hash_{idx}",
                job_title_raw=job.get("title"),
                company_name_raw=job.get("company"),
                pattern_detected=self.pattern_type,
                route=it_route,
                site_filter_route=it_route
            )
            results.append(posting)
        
        return results
    
    def apply_it_filter(self, category: str) -> str:
        """IT 해시 라우트 적용"""
        # 해시 라우트 후보
        routes = [
            f"#/jobs/{category.lower()}",
            f"#/careers/{category.lower()}",
            f"#/positions?category={category}",
            f"#/{category.lower()}"
        ]
        
        current_url = self.page.url.split("#")[0]
        
        for route in routes:
            try:
                target_url = current_url + route
                self.page.goto(target_url)
                self.page.wait_for_load_state("networkidle")
                
                # 공고가 로드되었는지 확인
                jobs = self.extract_job_list()
                if jobs:
                    return route
            except Exception:
                continue
        
        # 실패 시 현재 해시 반환
        return self.page.url.split("#")[-1] if "#" in self.page.url else ""
