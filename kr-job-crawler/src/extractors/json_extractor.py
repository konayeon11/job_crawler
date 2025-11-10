"""
JSON Extractor - JSON/API 응답에서 스키마 필드 추출
"""
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.schema import JobPostingCreate


class JSONExtractor:
    """JSON → JobPostingCreate 매핑"""
    
    def __init__(self, data: Dict[str, Any], source_url: str, domain: str):
        self.data = data
        self.source_url = source_url
        self.domain = domain
    
    def extract(self) -> JobPostingCreate:
        """JSON에서 공고 정보 추출"""
        
        return JobPostingCreate(
            domain=self.domain,
            source_url=self.source_url,
            canonical_job_id=self._get_field(["id", "jobId", "postingId", "uuid"]),
            
            # 원문
            company_name_raw=self._get_field(["company", "companyName", "employer"]),
            job_title_raw=self._get_field(["title", "jobTitle", "position", "positionTitle"]),
            department_raw=self._get_field(["department", "team", "division"]),
            employment_type_raw=self._get_field(["employmentType", "jobType", "type"]),
            location_raw=self._get_field(["location", "address", "place"]),
            post_date_raw=self._get_field(["postedDate", "publishedAt", "createdAt"]),
            close_date_raw=self._get_field(["closeDate", "deadline", "expiresAt"]),
            detail_json=self.data,
            
            # 표준화
            title=self._normalize_title(),
            employment_type=self._normalize_employment_type(),
            post_date=self._parse_date(self._get_field(["postedDate", "publishedAt"])),
            
            # 스킬
            skills=self._extract_skills()
        )
    
    def _get_field(self, keys: List[str]) -> Optional[str]:
        """여러 키 시도하여 필드 추출"""
        for key in keys:
            value = self.data.get(key)
            if value:
                return str(value)
        return None
    
    def _extract_skills(self) -> Optional[List[str]]:
        """스킬 추출"""
        skill_keys = ["skills", "technologies", "techStack", "requirements"]
        
        for key in skill_keys:
            skills = self.data.get(key)
            if skills:
                if isinstance(skills, list):
                    return [str(s) for s in skills]
                elif isinstance(skills, str):
                    # 쉼표로 구분된 문자열
                    return [s.strip() for s in skills.split(",")]
        
        return None
    
    def _normalize_title(self) -> Optional[str]:
        """제목 정규화"""
        title = self._get_field(["title", "jobTitle", "position"])
        if title:
            return title.strip()
        return None
    
    def _normalize_employment_type(self) -> Optional[str]:
        """고용형태 정규화"""
        raw = self._get_field(["employmentType", "jobType"])
        if not raw:
            return None
        
        # 대소문자 무시 매핑
        mapping = {
            "full_time": "FULL_TIME",
            "fulltime": "FULL_TIME",
            "part_time": "PART_TIME",
            "contract": "CONTRACT",
            "intern": "INTERN"
        }
        
        raw_lower = raw.lower()
        return mapping.get(raw_lower, raw)
    
    def _parse_date(self, date_str: Optional[str]):
        """ISO 8601 날짜 파싱"""
        if not date_str:
            return None
        
        try:
            # ISO 형식 시도
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.date()
        except Exception:
            pass
        
        return None
