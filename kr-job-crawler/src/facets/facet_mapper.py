"""
Facet Mapper - 직군 버튼 자동 탐지 및 매핑
"""
from playwright.sync_api import Page
from typing import Optional, Dict, Any, List
import time

from src.utils.hash_utils import compute_list_hash
from src.utils.playwright_launcher import PlaywrightLauncher


class FacetMapper:
    """직군 버튼 자동 탐지 및 검증 매퍼"""
    
    def __init__(self, page: Page, launcher: Optional[PlaywrightLauncher] = None):
        self.page = page
        self.launcher = launcher
    
    def detect_it_facets(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """IT 직군 버튼 후보 탐지
        
        Args:
            keywords: 탐지할 키워드 (기본: IT, Engineering, Tech, Developer, Software)
            
        Returns:
            버튼 후보 정보 리스트
        """
        if keywords is None:
            keywords = ["IT", "Engineering", "Tech", "Developer", "Software", "개발"]
        
        candidates = []
        
        # 다양한 셀렉터로 버튼 탐색
        selectors = [
            "button",
            "[role='tab']",
            "[role='button']",
            ".category",
            ".filter",
            ".tab",
            "a.category-link"
        ]
        
        for selector in selectors:
            elements = self.page.query_selector_all(selector)
            
            for elem in elements:
                try:
                    text = elem.inner_text().strip()
                    
                    # 키워드 매칭
                    for keyword in keywords:
                        if keyword.lower() in text.lower():
                            candidates.append({
                                "selector": selector,
                                "text": text,
                                "keyword": keyword,
                                "element": elem
                            })
                            break
                
                except Exception:
                    continue
        
        return candidates
    
    def verify_facet(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """버튼 후보 검증 (클릭 전후 리스트 해시 비교)
        
        Args:
            candidate: 버튼 후보 정보
            
        Returns:
            검증 결과 (유효성, 매핑 정보, 네트워크 파라미터)
        """
        element = candidate["element"]
        
        # 클릭 전 상태 캡처
        before_hash = self._capture_list_hash()
        before_network = self._get_network_snapshot()
        
        # 클릭
        try:
            element.click()
            self.page.wait_for_timeout(1500)  # 변경 대기
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
        
        # 클릭 후 상태 캡처
        after_hash = self._capture_list_hash()
        after_network = self._get_network_snapshot()
        
        # 해시 비교
        list_changed = before_hash != after_hash
        
        # 네트워크 파라미터 추출
        network_params = self._diff_network_calls(before_network, after_network)
        
        result = {
            "valid": list_changed,
            "selector": candidate["selector"],
            "text": candidate["text"],
            "keyword": candidate["keyword"],
            "list_hash_before": before_hash,
            "list_hash_after": after_hash,
            "network_params": network_params,
            "route": self._extract_route_change()
        }
        
        return result
    
    def map_and_save(
        self, 
        verified_facets: List[Dict[str, Any]],
        profile_path: str
    ) -> bool:
        """검증된 facet을 프로파일에 저장"""
        # Profile 저장 로직은 ProfileLoader에서 처리
        # 여기서는 매핑 데이터 구조만 반환
        
        mapping = {
            "it_filter": {
                "facets": verified_facets,
                "verified_at": time.time()
            }
        }
        
        # 실제 저장은 ProfileLoader 사용
        return True
    
    def _capture_list_hash(self) -> str:
        """현재 페이지의 공고 리스트 해시 계산"""
        # 공고 리스트로 보이는 요소들의 텍스트 추출
        selectors = [
            "article.job-posting",
            "div.job-item",
            "li.job-card",
            "[data-job-id]"
        ]
        
        items = []
        for selector in selectors:
            elements = self.page.query_selector_all(selector)
            if elements:
                items = [elem.inner_text().strip() for elem in elements]
                break
        
        return compute_list_hash(items)
    
    def _get_network_snapshot(self) -> List[str]:
        """네트워크 호출 스냅샷"""
        if not self.launcher:
            return []
        
        return [req.url for req in self.launcher.requests]
    
    def _diff_network_calls(
        self, 
        before: List[str], 
        after: List[str]
    ) -> Dict[str, Any]:
        """네트워크 호출 차이 분석"""
        new_calls = [url for url in after if url not in before]
        
        # API 호출만 필터링
        api_calls = [url for url in new_calls if "/api/" in url or "graphql" in url]
        
        if not api_calls:
            return {}
        
        # 첫 번째 API 호출 파라미터 추출
        first_api = api_calls[0]
        
        return {
            "endpoint": first_api.split("?")[0],
            "query_string": first_api.split("?")[1] if "?" in first_api else "",
            "all_calls": api_calls
        }
    
    def _extract_route_change(self) -> Optional[str]:
        """라우트 변경 추출 (해시 라우팅용)"""
        current_url = self.page.url
        
        if "#" in current_url:
            return current_url.split("#")[-1]
        
        return None
