"""
API Direct Handler - API/GraphQL 직접 호출
"""
from typing import List, Optional, Dict, Any
import httpx
import json

from src.handlers.base import BaseHandler
from src.schema import JobPostingCreate, PatternType, SiteProfile


class APIDirectHandler(BaseHandler):
    """API 직접 호출 핸들러"""
    
    def __init__(self, page, profile: SiteProfile):
        super().__init__(page, profile)
        self.pattern_type = PatternType.API_DIRECT
        self.api_config = profile.api_config if profile and profile.api_config else {}
        self.client = httpx.Client(timeout=30.0)
    
    def crawl(
        self, 
        target_category: str = "IT",
        limit: Optional[int] = None
    ) -> List[JobPostingCreate]:
        """크롤링 실행"""
        
        # API 엔드포인트 확인
        endpoint = self.api_config.get("endpoint")
        if not endpoint:
            print("⚠️  API 엔드포인트가 설정되지 않음")
            return []
        
        # IT 필터 파라미터 적용
        params = self._build_params(target_category, limit)
        
        # API 호출
        if self.api_config.get("type") == "graphql":
            data = self._call_graphql(endpoint, params)
        else:
            data = self._call_rest_api(endpoint, params)
        
        # 응답 파싱
        jobs = self._parse_response(data)
        
        # JobPostingCreate 변환
        results = []
        for idx, job in enumerate(jobs):
            if limit and idx >= limit:
                break
            
            posting = JobPostingCreate(
                domain=self.domain,
                source_url=job.get("url", endpoint),
                canonical_job_id=job.get("id", f"api_{idx}"),
                job_title_raw=job.get("title"),
                company_name_raw=job.get("company"),
                location_raw=job.get("location"),
                detail_json=job,
                pattern_detected=self.pattern_type,
                api_endpoint=endpoint,
                api_params=params
            )
            results.append(posting)
        
        return results
    
    def apply_it_filter(self, category: str) -> bool:
        """API는 파라미터로 필터 적용"""
        return True
    
    def _build_params(self, category: str, limit: Optional[int]) -> Dict[str, Any]:
        """API 파라미터 구성"""
        params = self.api_config.get("params", {}).copy()
        
        # 카테고리 필터 추가
        category_key = self.api_config.get("category_param", "category")
        params[category_key] = category
        
        # 리미트 추가
        if limit:
            limit_key = self.api_config.get("limit_param", "limit")
            params[limit_key] = limit
        
        return params
    
    def _call_rest_api(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """REST API 호출"""
        try:
            method = self.api_config.get("method", "GET").upper()
            
            if method == "GET":
                response = self.client.get(endpoint, params=params)
            else:
                response = self.client.post(endpoint, json=params)
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            print(f"❌ API 호출 실패: {e}")
            return {}
    
    def _call_graphql(self, endpoint: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """GraphQL 호출"""
        query = self.api_config.get("query", "")
        
        try:
            response = self.client.post(
                endpoint,
                json={
                    "query": query,
                    "variables": variables
                }
            )
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            print(f"❌ GraphQL 호출 실패: {e}")
            return {}
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 파싱"""
        # 응답 경로 확인
        jobs_path = self.api_config.get("jobs_path", "data.jobs")
        
        # 중첩 딕셔너리 탐색
        result = data
        for key in jobs_path.split("."):
            if isinstance(result, dict):
                result = result.get(key, [])
            else:
                break
        
        return result if isinstance(result, list) else []
    
    def __del__(self):
        """클라이언트 정리"""
        if hasattr(self, 'client'):
            self.client.close()
