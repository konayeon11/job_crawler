"""
Auto-Profiler - 자동 프로파일링 엔진
JSON-LD → API/GraphQL → DOM 패턴 → BFS 순차 시도
"""
from playwright.sync_api import Page
from typing import Optional, Dict, Any, List
import json

from src.schema import PatternType, SiteProfile
from src.utils.playwright_launcher import PlaywrightLauncher


class AutoProfiler:
    """자동 프로파일링 엔진"""
    
    def __init__(self, page: Page, domain: str, launcher: Optional[PlaywrightLauncher] = None):
        self.page = page
        self.domain = domain
        self.launcher = launcher
    
    def profile(self) -> SiteProfile:
        """순차적 프로파일링 실행
        
        실패-복구 시퀀스:
        1. JSON-LD(JobPosting) 탐지
        2. API/GraphQL 캡처
        3. DOM 패턴 (4가지)
        4. BFS 탐색
        
        Returns:
            생성된 SiteProfile
        """
        
        print(f"🔍 Auto-Profiling 시작: {self.domain}")
        
        # 1. JSON-LD 시도
        json_ld_result = self._try_json_ld()
        if json_ld_result["found"]:
            print("✅ JSON-LD 스키마 발견")
            return self._build_profile_from_json_ld(json_ld_result)
        
        # 2. API/GraphQL 시도
        api_result = self._try_api_capture()
        if api_result["found"]:
            print("✅ API/GraphQL 엔드포인트 발견")
            return self._build_profile_from_api(api_result)
        
        # 3. DOM 패턴 탐지
        dom_result = self._try_dom_patterns()
        if dom_result["pattern"] != PatternType.UNKNOWN:
            print(f"✅ DOM 패턴 발견: {dom_result['pattern'].value}")
            return self._build_profile_from_dom(dom_result)
        
        # 4. BFS 폴백
        print("⚠️  표준 패턴 미발견, BFS 탐색 시작")
        bfs_result = self._bfs_search()
        return self._build_profile_from_bfs(bfs_result)
    
    def _try_json_ld(self) -> Dict[str, Any]:
        """JSON-LD 스키마 탐지"""
        try:
            json_ld_scripts = self.page.query_selector_all('script[type="application/ld+json"]')
            
            for script in json_ld_scripts:
                content = script.inner_text()
                data = json.loads(content)
                
                # JobPosting 타입 확인
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return {
                        "found": True,
                        "type": "json-ld",
                        "data": data
                    }
                
                # 배열인 경우
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            return {
                                "found": True,
                                "type": "json-ld",
                                "data": item
                            }
        
        except Exception as e:
            print(f"⚠️  JSON-LD 파싱 실패: {e}")
        
        return {"found": False}
    
    def _try_api_capture(self) -> Dict[str, Any]:
        """네트워크에서 API/GraphQL 캡처"""
        if not self.launcher:
            return {"found": False}
        
        # API 호출 수집
        api_calls = self.launcher.get_api_calls()
        graphql_calls = self.launcher.get_graphql_calls()
        
        if graphql_calls:
            return {
                "found": True,
                "type": "graphql",
                "endpoint": graphql_calls[0].url,
                "calls": graphql_calls
            }
        
        if api_calls:
            # jobs/careers 관련 API 필터링
            job_apis = [
                call for call in api_calls 
                if any(kw in call.url.lower() for kw in ["job", "career", "recruit", "position"])
            ]
            
            if job_apis:
                return {
                    "found": True,
                    "type": "rest",
                    "endpoint": job_apis[0].url,
                    "calls": job_apis
                }
        
        return {"found": False}
    
    def _try_dom_patterns(self) -> Dict[str, Any]:
        """DOM 패턴 4가지 시도"""
        from src.detector.pattern_detector import PatternDetector
        
        detector = PatternDetector(self.page)
        pattern = detector.detect()
        metadata = detector.get_pattern_metadata(pattern)
        
        return {
            "pattern": pattern,
            "metadata": metadata
        }
    
    def _bfs_search(self) -> Dict[str, Any]:
        """BFS 탐색 - 공고 리스트 컨테이너 찾기"""
        # 간단한 BFS로 가장 많은 반복 요소를 가진 컨테이너 찾기
        container_candidates = []
        
        common_containers = [
            "main",
            "#content",
            ".job-list",
            ".postings",
            "[role='main']"
        ]
        
        for selector in common_containers:
            try:
                elem = self.page.query_selector(selector)
                if elem:
                    # 하위 반복 요소 개수 확인
                    children = elem.query_selector_all("article, .item, .card, li")
                    if len(children) > 3:
                        container_candidates.append({
                            "selector": selector,
                            "count": len(children)
                        })
            except Exception:
                continue
        
        # 가장 많은 요소를 가진 컨테이너 선택
        if container_candidates:
            best = max(container_candidates, key=lambda x: x["count"])
            return {
                "found": True,
                "container": best["selector"],
                "item_count": best["count"]
            }
        
        return {"found": False}
    
    def _build_profile_from_json_ld(self, result: Dict[str, Any]) -> SiteProfile:
        """JSON-LD 기반 프로파일 생성"""
        return SiteProfile(
            domain=self.domain,
            name=self.domain,
            version="1.0.0-auto",
            pattern=PatternType.API_DIRECT,
            extraction_rules={
                "source": "json-ld",
                "schema_type": "JobPosting"
            }
        )
    
    def _build_profile_from_api(self, result: Dict[str, Any]) -> SiteProfile:
        """API 기반 프로파일 생성"""
        return SiteProfile(
            domain=self.domain,
            name=self.domain,
            version="1.0.0-auto",
            pattern=PatternType.API_DIRECT,
            api_config={
                "type": result["type"],
                "endpoint": result["endpoint"]
            }
        )
    
    def _build_profile_from_dom(self, result: Dict[str, Any]) -> SiteProfile:
        """DOM 패턴 기반 프로파일 생성"""
        return SiteProfile(
            domain=self.domain,
            name=self.domain,
            version="1.0.0-auto",
            pattern=result["pattern"],
            selectors=result.get("metadata", {})
        )
    
    def _build_profile_from_bfs(self, result: Dict[str, Any]) -> SiteProfile:
        """BFS 결과 기반 프로파일 생성"""
        return SiteProfile(
            domain=self.domain,
            name=self.domain,
            version="1.0.0-auto",
            pattern=PatternType.STATIC_TOGGLE,
            selectors={
                "container": result.get("container", "main"),
                "discovered_by": "bfs"
            }
        )
