"""
Pydantic schemas for data validation and serialization
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class PatternType(str, Enum):
    """크롤링 패턴 타입"""
    STATIC_TOGGLE = "static_toggle"
    A_LINK = "a_link"
    FUNCTION = "function"
    HASH_ROUTING = "hash_routing"
    API_DIRECT = "api_direct"
    UNKNOWN = "unknown"


class LabelSource(str, Enum):
    """IT 분류 출처"""
    SITE = "site"
    RULE = "rule"
    MODEL = "model"
    MIXED = "mixed"


class JobPostingBase(BaseModel):
    """Job posting base schema"""
    
    # A. 식별/출처
    domain: str
    source_url: str
    canonical_job_id: str
    source_platform: Optional[str] = None
    
    # B. 원문
    company_name_raw: Optional[str] = None
    job_title_raw: Optional[str] = None
    department_raw: Optional[str] = None
    team_raw: Optional[str] = None
    category_raw: Optional[str] = None
    employment_type_raw: Optional[str] = None
    location_raw: Optional[str] = None
    post_date_raw: Optional[str] = None
    close_date_raw: Optional[str] = None
    detail_html: Optional[str] = None
    detail_json: Optional[Dict[str, Any]] = None
    
    # C. 표준화
    title: Optional[str] = None
    employment_type: Optional[str] = None
    location_country: Optional[str] = None
    location_city: Optional[str] = None
    post_date: Optional[date] = None
    close_date: Optional[date] = None
    is_active: bool = True
    
    # D. IT 분류/스킬
    site_category_path: Optional[str] = None
    skills: Optional[List[str]] = None
    it_label: Optional[bool] = None
    label_source: Optional[LabelSource] = None
    label_confidence: Optional[float] = None
    label_evidence: Optional[Dict[str, Any]] = None
    
    # E. 프로비넌스
    pattern_detected: Optional[PatternType] = None
    route: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_operation: Optional[str] = None
    api_params: Optional[Dict[str, Any]] = None
    selectors_used: Optional[Dict[str, Any]] = None
    site_filter_selector: Optional[str] = None
    site_filter_route: Optional[str] = None
    site_filter_api_params: Optional[Dict[str, Any]] = None
    profile_version: Optional[str] = None
    snapshot_hash: Optional[str] = None
    
    # F. 관리
    country_filter: Optional[str] = None


class JobPostingCreate(JobPostingBase):
    """Job posting creation schema"""
    pass


class JobPostingResponse(JobPostingBase):
    """Job posting response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SiteProfile(BaseModel):
    """사이트 프로파일 스키마"""
    domain: str
    name: str
    version: str = "1.0.0"
    pattern: PatternType
    
    # 직군 필터 설정
    it_filter: Optional[Dict[str, Any]] = None
    
    # 패턴별 설정
    selectors: Optional[Dict[str, str]] = None
    api_config: Optional[Dict[str, Any]] = None
    
    # 추출 규칙
    extraction_rules: Optional[Dict[str, Any]] = None
    
    # 메타데이터
    last_verified: Optional[datetime] = None
    notes: Optional[str] = None


class CrawlResult(BaseModel):
    """크롤링 결과 요약"""
    domain: str
    total_found: int
    it_filtered: int
    saved: int
    errors: List[str] = []
    pattern_used: PatternType
    execution_time: float
