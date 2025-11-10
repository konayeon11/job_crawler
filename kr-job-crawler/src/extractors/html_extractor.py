"""
HTML Extractor - HTML에서 스키마 필드 추출 및 정규화
"""
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from datetime import datetime
import re

from src.schema import JobPostingCreate


class HTMLExtractor:
    """HTML → JobPostingCreate 매핑"""
    
    def __init__(self, html: str, source_url: str, domain: str):
        self.soup = BeautifulSoup(html, 'lxml')
        self.source_url = source_url
        self.domain = domain
    
    def extract(self) -> JobPostingCreate:
        """HTML에서 공고 정보 추출"""
        
        return JobPostingCreate(
            domain=self.domain,
            source_url=self.source_url,
            canonical_job_id=self._extract_job_id(),
            
            # 원문 추출
            company_name_raw=self._extract_company(),
            job_title_raw=self._extract_title(),
            department_raw=self._extract_department(),
            employment_type_raw=self._extract_employment_type(),
            location_raw=self._extract_location(),
            post_date_raw=self._extract_post_date(),
            close_date_raw=self._extract_close_date(),
            detail_html=str(self.soup),
            
            # 표준화 (정규화)
            title=self._normalize_title(),
            employment_type=self._normalize_employment_type(),
            location_country=self._extract_country(),
            location_city=self._extract_city(),
            post_date=self._parse_date(self._extract_post_date()),
            close_date=self._parse_date(self._extract_close_date()),
            
            # 스킬 추출
            skills=self._extract_skills()
        )
    
    def _extract_job_id(self) -> str:
        """공고 ID 추출"""
        # URL에서 ID 추출 시도
        match = re.search(r'/(\d+)/?$', self.source_url)
        if match:
            return match.group(1)
        
        # data-job-id 속성 확인
        elem = self.soup.find(attrs={"data-job-id": True})
        if elem:
            return elem['data-job-id']
        
        # 폴백: URL 해시
        from src.utils.hash_utils import compute_content_hash
        return compute_content_hash(self.source_url)[:16]
    
    def _extract_company(self) -> Optional[str]:
        """회사명 추출"""
        selectors = [
            ".company-name",
            "[itempr op='hiringOrganization']",
            "h1.company",
            ".employer-name"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_title(self) -> Optional[str]:
        """공고 제목 추출"""
        selectors = [
            "h1.job-title",
            "[itemprop='title']",
            "h1",
            ".position-title"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_department(self) -> Optional[str]:
        """부서명 추출"""
        selectors = [
            ".department",
            "[itemprop='department']",
            ".team-name"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_employment_type(self) -> Optional[str]:
        """고용형태 추출"""
        selectors = [
            ".employment-type",
            "[itemprop='employmentType']",
            ".job-type"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_location(self) -> Optional[str]:
        """위치 추출"""
        selectors = [
            ".location",
            "[itemprop='jobLocation']",
            ".address"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_post_date(self) -> Optional[str]:
        """게시일 추출"""
        selectors = [
            ".post-date",
            "[itemprop='datePosted']",
            "time.posted"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_close_date(self) -> Optional[str]:
        """마감일 추출"""
        selectors = [
            ".close-date",
            "[itemprop='validThrough']",
            ".deadline"
        ]
        return self._safe_select_text(selectors)
    
    def _extract_skills(self) -> Optional[List[str]]:
        """스킬 추출"""
        skills = []
        
        # 스킬 태그/뱃지 추출
        skill_selectors = [
            ".skill-tag",
            ".tech-stack",
            "[itemprop='skills']"
        ]
        
        for selector in skill_selectors:
            elements = self.soup.select(selector)
            for elem in elements:
                skill = elem.get_text(strip=True)
                if skill:
                    skills.append(skill)
        
        return skills if skills else None
    
    def _normalize_title(self) -> Optional[str]:
        """제목 정규화"""
        title = self._extract_title()
        if not title:
            return None
        
        # 불필요한 문자 제거
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    
    def _normalize_employment_type(self) -> Optional[str]:
        """고용형태 정규화"""
        raw = self._extract_employment_type()
        if not raw:
            return None
        
        # 매핑 테이블
        mapping = {
            "정규직": "FULL_TIME",
            "계약직": "CONTRACT",
            "인턴": "INTERN",
            "full-time": "FULL_TIME",
            "part-time": "PART_TIME",
            "contract": "CONTRACT"
        }
        
        raw_lower = raw.lower()
        for key, value in mapping.items():
            if key in raw_lower:
                return value
        
        return raw
    
    def _extract_country(self) -> Optional[str]:
        """국가 추출"""
        location = self._extract_location()
        if not location:
            return None
        
        # 한국 키워드 확인
        if any(kw in location for kw in ["한국", "Korea", "서울", "Seoul"]):
            return "KR"
        
        return None
    
    def _extract_city(self) -> Optional[str]:
        """도시 추출"""
        location = self._extract_location()
        if not location:
            return None
        
        # 주요 도시 매칭
        cities = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]
        for city in cities:
            if city in location:
                return city
        
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional:
        """날짜 파싱"""
        if not date_str:
            return None
        
        # 다양한 날짜 형식 시도
        formats = [
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%Y/%m/%d",
            "%Y년 %m월 %d일"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _safe_select_text(self, selectors: List[str]) -> Optional[str]:
        """안전한 셀렉터 텍스트 추출"""
        for selector in selectors:
            elem = self.soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    return text
        return None
