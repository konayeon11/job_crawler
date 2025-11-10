"""
SQLAlchemy ORM models for job_postings table
"""
from sqlalchemy import (
    Column, String, Text, Boolean, Date, TIMESTAMP, 
    Numeric, ARRAY, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class JobPosting(Base):
    """Job posting model - 통합 채용공고 데이터"""
    
    __tablename__ = "job_postings"
    
    # A. 식별/출처
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    canonical_job_id = Column(String(500), nullable=False)
    source_platform = Column(String(100))
    
    # B. 원문
    company_name_raw = Column(String(500))
    job_title_raw = Column(String(1000))
    department_raw = Column(String(500))
    team_raw = Column(String(500))
    category_raw = Column(String(500))
    employment_type_raw = Column(String(200))
    location_raw = Column(String(1000))
    post_date_raw = Column(String(200))
    close_date_raw = Column(String(200))
    detail_html = Column(Text)
    detail_json = Column(JSONB)
    
    # C. 표준화
    title = Column(String(1000))
    employment_type = Column(String(100))
    location_country = Column(String(100))
    location_city = Column(String(200))
    post_date = Column(Date, index=True)
    close_date = Column(Date)
    is_active = Column(Boolean, default=True, index=True)
    
    # D. IT 분류/스킬
    site_category_path = Column(String(1000))
    skills = Column(ARRAY(Text))
    it_label = Column(Boolean, index=True)
    label_source = Column(String(50))  # site|rule|model|mixed
    label_confidence = Column(Numeric(5, 4))
    label_evidence = Column(JSONB)
    
    # E. 프로비넌스
    pattern_detected = Column(String(100))
    route = Column(String(500))
    api_endpoint = Column(Text, index=True)
    api_operation = Column(String(200))
    api_params = Column(JSONB)
    selectors_used = Column(JSONB)
    site_filter_selector = Column(String(500))
    site_filter_route = Column(String(500))
    site_filter_api_params = Column(JSONB)
    profile_version = Column(String(50))
    snapshot_hash = Column(String(64))
    
    # F. 관리
    country_filter = Column(String(10))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 제약조건
    __table_args__ = (
        UniqueConstraint('domain', 'canonical_job_id', name='unique_domain_job'),
        Index('idx_job_postings_source_url_hash', 'source_url', postgresql_using='hash'),
        Index('idx_job_postings_skills_gin', 'skills', postgresql_using='gin'),
        Index('idx_job_postings_label_evidence_gin', 'label_evidence', postgresql_using='gin'),
        Index('idx_job_postings_detail_json_gin', 'detail_json', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<JobPosting(id={self.id}, domain={self.domain}, title={self.title})>"
