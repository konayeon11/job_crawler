"""
A Link Handler - A 태그 링크 패턴
"""
from typing import List, Optional
from src.handlers.base import BaseHandler
from src.schema import JobPostingCreate, PatternType, SiteProfile


class ALinkHandler(BaseHandler):
    """A 태그 링크 패턴 핸들러"""
    
    def __init__(self, page, profile: SiteProfile):
        super().__init__(page, profile)
        self.pattern_type = PatternType.A_LINK
    
    def crawl(
        self, 
        target_category: str = "IT",
        limit: Optional[int] = None
    ) -> List[JobPostingCreate]:
        """크롤링 실행"""
        
        # IT 필터 시도
        self.apply_it_filter(target_category)
        
        # 링크 수집
        self.infinite_scroll(max_scrolls=5)
        job_links = self._extract_job_links()
        
        results = []
        for idx, link in enumerate(job_links):
            if limit and idx >= limit:
                break
            
            posting = JobPostingCreate(
                domain=self.domain,
                source_url=link["url"],
                canonical_job_id=f"{self.domain}_{link['url'].split('/')[-1]}",
                job_title_raw=link.get("title"),
                pattern_detected=self.pattern_type,
                route=link["url"]
            )
            results.append(posting)
        
        return results
    
    def apply_it_filter(self, category: str) -> bool:
        """IT 필터 적용 (A Link는 주로 URL 기반 필터링)"""
        # 카테고리 링크 클릭 시도
        try:
            category_link = self.page.query_selector(
                f"a:has-text('{category}'), a[href*='it'], a[href*='tech']"
            )
            if category_link:
                category_link.click()
                self.page.wait_for_load_state("networkidle")
                return True
        except Exception:
            pass
        
        return False
    
    def _extract_job_links(self) -> List[dict]:
        """공고 링크 추출"""
        links = []
        
        # 공고 링크로 보이는 a 태그 수집
        selectors = [
            "a[href*='job']",
            "a[href*='career']",
            "a[href*='recruit']",
            "a[href*='position']"
        ]
        
        for selector in selectors:
            elements = self.page.query_selector_all(selector)
            for elem in elements:
                try:
                    url = elem.get_attribute("href")
                    if url and url.startswith("http"):
                        links.append({
                            "url": url,
                            "title": elem.inner_text().strip()
                        })
                except Exception:
                    continue
        
        # 중복 제거
        seen = set()
        unique_links = []
        for link in links:
            if link["url"] not in seen:
                seen.add(link["url"])
                unique_links.append(link)
        
        return unique_links
